from __future__ import annotations

import csv
import io
import json
import re
import time
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from secure_transcribe.errors import StudioError
from secure_transcribe.manifest import (
    MANIFEST_COLUMNS,
    ImportPlanStore,
    parse_manifest,
)

CSV_TYPE = "text/csv"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def valid_rows() -> list[list[str]]:
    return [
        list(MANIFEST_COLUMNS),
        [
            "1.0",
            "archive-1",
            "local_archive",
            "incoming/review.zip",
            "prompt://review-passphrase",
            "Quarterly review",
            "a" * 64,
        ],
        [
            "1.0",
            "zoom-1",
            "zoom_recording",
            "Meeting_123:Recording_456",
            "",
            "Planning call",
            "",
        ],
    ]


def csv_bytes(rows: list[list[str]], *, bom: bool = False) -> bytes:
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    encoded = stream.getvalue().encode("utf-8")
    return (b"\xef\xbb\xbf" + encoded) if bom else encoded


def xlsx_bytes(
    rows: list[list[str]],
    *,
    formula: bool = False,
    hidden_row: bool = False,
    hidden_column: bool = False,
    merged: bool = False,
    external_relationship: bool = False,
    extra_sheet: bool = False,
    numeric_cell: bool = False,
    defined_name: bool = False,
    symlink_entry: bool = False,
    macro_content: bool = False,
    embedded_object: bool = False,
    compression_bomb: bool = False,
    padding_bytes: int = 0,
) -> bytes:
    cells: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        hidden = ' hidden="1"' if hidden_row and row_number == 2 else ""
        row_cells = []
        for column_number, value in enumerate(row, start=1):
            column = chr(ord("A") + column_number - 1)
            reference = f"{column}{row_number}"
            if formula and row_number == 2 and column_number == 6:
                row_cells.append(f'<c r="{reference}"><f>1+1</f><v>2</v></c>')
            elif numeric_cell and row_number == 2 and column_number == 1:
                row_cells.append(f'<c r="{reference}"><v>1</v></c>')
            else:
                row_cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                )
        cells.append(f'<row r="{row_number}"{hidden}>{"".join(row_cells)}</row>')

    merge_xml = '<mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>' if merged else ""
    columns_xml = '<cols><col min="1" max="1" hidden="1"/></cols>' if hidden_column else ""
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'{columns_xml}<sheetData>{"".join(cells)}</sheetData>{merge_xml}</worksheet>'
    )
    second_sheet = (
        '<sheet name="extra" sheetId="2" r:id="rId2"/>' if extra_sheet else ""
    )
    defined_names = (
        "<definedNames><definedName name=\"hidden\">https://example.invalid/</definedName>"
        "</definedNames>"
        if defined_name
        else ""
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="recordings" sheetId="1" r:id="rId1"/>{second_sheet}</sheets>'
        f"{defined_names}"
        '</workbook>'
    )
    second_relationship = (
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet2.xml"/>'
        if extra_sheet
        else ""
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        f'{second_relationship}</Relationships>'
    )
    workbook_content_type = (
        "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
        if macro_content
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        f'ContentType="{workbook_content_type}"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    external_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId9" TargetMode="External" Target="https://example.invalid/" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"/>'
        '</Relationships>'
    )

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
        if extra_sheet:
            archive.writestr("xl/worksheets/sheet2.xml", sheet)
        if external_relationship:
            archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", external_rels)
        if symlink_entry:
            symlink = zipfile.ZipInfo("docProps/link")
            symlink.create_system = 3
            symlink.external_attr = (0o120777 << 16) | 0xA000
            archive.writestr(symlink, "target")
        if embedded_object:
            archive.writestr("xl/embeddings/object.bin", b"not-allowed")
        if compression_bomb:
            archive.writestr("docProps/repeated.bin", b"x" * 1_000_000)
        if padding_bytes:
            archive.writestr(
                "docProps/padding.bin",
                bytes((index % 251 for index in range(padding_bytes))),
                compress_type=zipfile.ZIP_STORED,
            )
    return stream.getvalue()


def parse_csv(rows: list[list[str]], *, bom: bool = False):
    return parse_manifest(
        filename="recordings.csv",
        content_type=CSV_TYPE,
        payload=csv_bytes(rows, bom=bom),
    )


def assert_code(expected: str, callable_) -> None:
    with pytest.raises(StudioError) as captured:
        callable_()
    assert captured.value.code == expected


def test_valid_csv_and_bom_normalize_to_internal_rows() -> None:
    plain = parse_csv(valid_rows())
    bom = parse_csv(valid_rows(), bom=True)
    assert plain == bom
    assert [row.row_id for row in plain] == ["archive-1", "zoom-1"]
    assert plain[0].expected_sha256 == "a" * 64


def test_valid_csv_and_xlsx_normalize_identically() -> None:
    csv_rows = parse_csv(valid_rows())
    xlsx_rows = parse_manifest(
        filename="recordings.xlsx",
        content_type=XLSX_TYPE,
        payload=xlsx_bytes(valid_rows()),
    )
    assert xlsx_rows == csv_rows


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda rows: rows.__setitem__(0, [*rows[0][:-1], "password"]), "MANIFEST_COLUMNS_INVALID"),
        (lambda rows: rows[1].__setitem__(0, "2.0"), "MANIFEST_SCHEMA_VERSION_INVALID"),
        (lambda rows: rows[1].__setitem__(1, "bad id"), "MANIFEST_ROW_ID_INVALID"),
        (lambda rows: rows[2].__setitem__(1, "archive-1"), "MANIFEST_ROW_ID_DUPLICATE"),
        (lambda rows: rows[1].__setitem__(2, "mp4"), "MANIFEST_SOURCE_TYPE_INVALID"),
        (lambda rows: rows[1].__setitem__(3, "../review.zip"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
        (lambda rows: rows[1].__setitem__(3, "./review.zip"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
        (lambda rows: rows[1].__setitem__(3, "incoming//review.zip"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
        (lambda rows: rows[1].__setitem__(3, "incoming/CON.zip"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
        (lambda rows: rows[1].__setitem__(3, "incoming /review.zip"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
        (lambda rows: rows[1].__setitem__(3, "https://example.invalid/a.zip"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
        (lambda rows: rows[1].__setitem__(4, "plaintext-password"), "MANIFEST_SECRET_REF_INVALID"),
        (lambda rows: rows[2].__setitem__(4, "prompt://wrong"), "MANIFEST_SECRET_REF_INVALID"),
        (lambda rows: rows[1].__setitem__(5, "folder/name"), "MANIFEST_DISPLAY_NAME_INVALID"),
        (lambda rows: rows[1].__setitem__(6, "ABC"), "MANIFEST_SHA256_INVALID"),
        (lambda rows: rows[1].__setitem__(5, "=2+2"), "MANIFEST_FORMULA_FORBIDDEN"),
        (lambda rows: rows[2].__setitem__(3, "https://zoom.invalid/file"), "MANIFEST_SOURCE_LOCATOR_INVALID"),
    ],
)
def test_csv_contract_rejects_unsafe_or_ambiguous_values(mutation, reason: str) -> None:
    rows = valid_rows()
    mutation(rows)
    assert_code(reason, lambda: parse_csv(rows))


def test_csv_rejects_row_and_credential_reference_limits() -> None:
    rows = [list(MANIFEST_COLUMNS)]
    for index in range(26):
        rows.append(
            [
                "1.0",
                f"row-{index}",
                "local_archive",
                f"incoming/{index}.zip",
                f"wincred://Verbatim/{index}",
                f"Review {index}",
                "",
            ]
        )
    assert_code("MANIFEST_ROW_LIMIT_EXCEEDED", lambda: parse_csv(rows))
    assert_code("MANIFEST_SECRET_REF_LIMIT_EXCEEDED", lambda: parse_csv(rows[:22]))


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"formula": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"hidden_row": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"hidden_column": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"merged": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"external_relationship": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"extra_sheet": True}, "MANIFEST_XLSX_WORKSHEET_INVALID"),
        ({"numeric_cell": True}, "MANIFEST_XLSX_CELL_TYPE_FORBIDDEN"),
        ({"defined_name": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"symlink_entry": True}, "MANIFEST_XLSX_PACKAGE_UNSAFE"),
        ({"macro_content": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"embedded_object": True}, "MANIFEST_XLSX_FEATURE_FORBIDDEN"),
        ({"compression_bomb": True}, "MANIFEST_XLSX_PACKAGE_UNSAFE"),
    ],
)
def test_xlsx_rejects_prohibited_features(kwargs: dict, reason: str) -> None:
    assert_code(
        reason,
        lambda: parse_manifest(
            filename="recordings.xlsx",
            content_type=XLSX_TYPE,
            payload=xlsx_bytes(valid_rows(), **kwargs),
        ),
    )


def test_filename_content_type_encoding_empty_and_size_fail_closed() -> None:
    payload = csv_bytes(valid_rows())
    assert_code(
        "MANIFEST_TYPE_UNSUPPORTED",
        lambda: parse_manifest(filename="recordings.xlsm", content_type=XLSX_TYPE, payload=payload),
    )
    assert_code(
        "MANIFEST_CONTENT_TYPE_INVALID",
        lambda: parse_manifest(
            filename="recordings.csv", content_type="application/octet-stream", payload=payload
        ),
    )
    assert_code(
        "MANIFEST_ENCODING_INVALID",
        lambda: parse_manifest(filename="recordings.csv", content_type=CSV_TYPE, payload=b"\xff"),
    )
    assert_code(
        "MANIFEST_EMPTY",
        lambda: parse_manifest(filename="recordings.csv", content_type=CSV_TYPE, payload=b""),
    )
    assert_code(
        "MANIFEST_XLSX_INVALID",
        lambda: parse_manifest(
            filename="recordings.xlsx", content_type=XLSX_TYPE, payload=b"not-a-zip"
        ),
    )
    assert_code(
        "MANIFEST_REQUEST_TOO_LARGE",
        lambda: parse_manifest(
            filename="recordings.csv", content_type=CSV_TYPE, payload=b"x" * (5 * 1024**2 + 1)
        ),
    )


def test_plan_store_redacts_secret_targets_and_expires_plans() -> None:
    payload = csv_bytes(valid_rows())
    rows = parse_csv(valid_rows())
    store = ImportPlanStore(ttl_seconds=1_800, max_plans=1)
    plan = store.create(payload, rows)
    preview = store.preview(plan).model_dump(mode="json")
    serialized = str(preview)
    assert "review-passphrase" not in serialized
    assert preview["rows"][0]["secret_provider"] == "prompt"
    assert preview["rows"][1]["secret_provider"] == "zoom_oauth"
    assert store.get(plan.id) == plan
    assert_code("IMPORT_PLAN_CAPACITY_REACHED", lambda: store.create(payload, rows))

    expired = ImportPlanStore(ttl_seconds=0.01, max_plans=1)
    expired_plan = expired.create(payload, rows)
    time.sleep(0.03)
    assert expired.active_count() == 0
    assert_code("IMPORT_PLAN_NOT_FOUND", lambda: expired.get(expired_plan.id))
    store.close()
    assert store.active_count() == 0


def test_near_limit_xlsx_preview_parser_stays_within_performance_budget() -> None:
    payload = xlsx_bytes(valid_rows(), padding_bytes=4_500_000)
    started = time.perf_counter()
    rows = parse_manifest(
        filename="recordings.xlsx",
        content_type=XLSX_TYPE,
        payload=payload,
    )
    elapsed = time.perf_counter() - started
    assert len(rows) == 2
    assert len(payload) < 5 * 1024**2
    assert elapsed < 2.0


def test_manifest_reason_code_catalog_is_versioned_unique_and_complete() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (root / "evals" / "import-manifest-reason-codes.json").read_text(encoding="utf-8")
    )
    entries = catalog["codes"]
    catalog_codes = [entry["code"] for entry in entries]
    assert catalog["schema_version"] == "1.0"
    assert catalog["default_enabled"] is False
    assert len(catalog_codes) == len(set(catalog_codes))
    assert all(entry["http_status"] in {400, 404, 409, 413} for entry in entries)

    source = (root / "src" / "secure_transcribe" / "manifest.py").read_text(encoding="utf-8")
    source += (root / "src" / "secure_transcribe" / "app.py").read_text(encoding="utf-8")
    implemented = set(
        re.findall(r'"((?:MANIFEST|IMPORT_PLAN)_[A-Z0-9_]+|FEATURE_DISABLED)"', source)
    )
    assert implemented == set(catalog_codes)
