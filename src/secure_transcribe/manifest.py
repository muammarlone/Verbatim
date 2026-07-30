from __future__ import annotations

import csv
import hashlib
import io
import posixpath
import re
import threading
import zipfile
from datetime import timedelta
from pathlib import PurePosixPath
from uuid import UUID, uuid4
from xml.etree import ElementTree

from .errors import StudioError
from .models import (
    ImportPlan,
    ImportPlanPreview,
    ImportPlanPreviewRow,
    ImportPlanRow,
    ManifestSourceType,
    SecretProvider,
    utc_now,
)

MANIFEST_SCHEMA_VERSION = "1.0"
MANIFEST_COLUMNS = (
    "schema_version",
    "row_id",
    "source_type",
    "source_locator",
    "secret_ref",
    "display_name",
    "expected_sha256",
)
MAX_MANIFEST_BYTES = 5 * 1024 * 1024
MAX_MANIFEST_ROWS = 25
MAX_XLSX_ENTRIES = 128
MAX_XLSX_EXPANDED_BYTES = 20 * 1024 * 1024
MAX_XLSX_COMPRESSION_RATIO = 200
MAX_FIELD_CHARACTERS = 512
MAX_WINCRED_REFERENCES = 20

_ROW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROMPT_REF = re.compile(r"^prompt://[A-Za-z0-9][A-Za-z0-9._ -]{0,63}$")
_WINCRED_REF = re.compile(r"^wincred://[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_ZOOM_LOCATOR = re.compile(
    r"^[A-Za-z0-9_-]{8,128}:[A-Za-z0-9_-]{8,128}$"
)
_ARCHIVE_PATH_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,99}$")
_CELL_REFERENCE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")
_FORMULA_PREFIXES = ("=", "+", "-", "@")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WINDOWS_RESERVED_NAMES = {
    "AUX",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}

_CSV_MEDIA_TYPES = {"text/csv", "application/csv"}
_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_FORBIDDEN_XLSX_PATH_PARTS = (
    "customxml/",
    "xl/activex/",
    "xl/comments",
    "xl/calcchain.xml",
    "xl/connections.xml",
    "xl/drawings/",
    "xl/embeddings/",
    "xl/externallinks/",
    "xl/media/",
    "xl/persons/",
    "xl/pivottables/",
    "xl/pivotcache/",
    "xl/printersettings/",
    "xl/querytables/",
    "xl/slicers/",
    "xl/threadedcomments/",
    "vbaproject",
)
_FORBIDDEN_SHEET_ELEMENTS = {
    "dataValidations",
    "drawing",
    "f",
    "hyperlinks",
    "legacyDrawing",
    "legacyDrawingHF",
    "mergeCell",
    "mergeCells",
    "oleObject",
    "oleObjects",
    "picture",
}
_FORBIDDEN_WORKBOOK_ELEMENTS = {
    "customWorkbookViews",
    "definedName",
    "definedNames",
    "externalReferences",
    "fileSharing",
    "fileVersion",
    "pivotCaches",
    "webPublishing",
    "webPublishObjects",
}


def _fail(code: str, message: str, *, status: int = 400) -> None:
    raise StudioError(code, message, http_status=status)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_root(data: bytes):
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        _fail(
            "MANIFEST_XLSX_PACKAGE_UNSAFE",
            "The XLSX package contains a prohibited XML declaration.",
        )
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise StudioError(
            "MANIFEST_XLSX_INVALID", "The XLSX package contains malformed XML."
        ) from exc


def _is_truthy_xml(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _column_index(letters: str) -> int:
    result = 0
    for character in letters:
        result = result * 26 + (ord(character) - ord("A") + 1)
    return result


def _validate_filename_and_media_type(filename: str | None, content_type: str | None) -> str:
    if (
        not filename
        or len(filename) > 240
        or "/" in filename
        or "\\" in filename
        or _CONTROL_CHARACTERS.search(filename)
    ):
        _fail("MANIFEST_FILENAME_INVALID", "Choose a CSV or XLSX file with a safe name.")
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        if normalized_type not in _CSV_MEDIA_TYPES:
            _fail(
                "MANIFEST_CONTENT_TYPE_INVALID",
                "The CSV file must use an approved CSV content type.",
            )
        return "csv"
    if lowered.endswith(".xlsx"):
        if normalized_type != _XLSX_MEDIA_TYPE:
            _fail(
                "MANIFEST_CONTENT_TYPE_INVALID",
                "The XLSX file must use the standard XLSX content type.",
            )
        return "xlsx"
    _fail("MANIFEST_TYPE_UNSUPPORTED", "Only CSV and non-macro XLSX manifests are supported.")
    raise AssertionError("unreachable")


def _reject_formula_like(value: str) -> None:
    if value.lstrip().startswith(_FORMULA_PREFIXES):
        _fail(
            "MANIFEST_FORMULA_FORBIDDEN",
            "Formula-like manifest values are not allowed.",
        )


def _normalize_table(raw_rows: list[list[str]]) -> list[ImportPlanRow]:
    if not raw_rows:
        _fail("MANIFEST_EMPTY", "The manifest contains no rows.")
    if tuple(raw_rows[0]) != MANIFEST_COLUMNS:
        _fail(
            "MANIFEST_COLUMNS_INVALID",
            "The manifest must contain the seven required columns in the documented order.",
        )

    data_rows: list[list[str]] = []
    for raw in raw_rows[1:]:
        if not any(value.strip() for value in raw):
            continue
        if len(raw) != len(MANIFEST_COLUMNS):
            _fail(
                "MANIFEST_COLUMNS_INVALID",
                "Every manifest row must contain exactly seven columns.",
            )
        normalized = [value.strip() for value in raw]
        for value in normalized:
            if len(value) > MAX_FIELD_CHARACTERS or _CONTROL_CHARACTERS.search(value):
                _fail(
                    "MANIFEST_CELL_INVALID",
                    "A manifest cell exceeds its bound or contains a prohibited character.",
                )
            _reject_formula_like(value)
        data_rows.append(normalized)

    if not data_rows:
        _fail("MANIFEST_EMPTY", "The manifest contains no recording rows.")
    if len(data_rows) > MAX_MANIFEST_ROWS:
        _fail(
            "MANIFEST_ROW_LIMIT_EXCEEDED",
            f"A manifest may contain at most {MAX_MANIFEST_ROWS} recording rows.",
            status=413,
        )

    rows: list[ImportPlanRow] = []
    row_ids: set[str] = set()
    wincred_refs: set[str] = set()
    for values in data_rows:
        row = dict(zip(MANIFEST_COLUMNS, values, strict=True))
        if row["schema_version"] != MANIFEST_SCHEMA_VERSION:
            _fail(
                "MANIFEST_SCHEMA_VERSION_INVALID",
                f"Every row must use schema version {MANIFEST_SCHEMA_VERSION}.",
            )
        row_id = row["row_id"]
        if not _ROW_ID.fullmatch(row_id):
            _fail(
                "MANIFEST_ROW_ID_INVALID",
                "Each row ID must be a bounded ASCII identifier.",
            )
        if row_id in row_ids:
            _fail("MANIFEST_ROW_ID_DUPLICATE", "Manifest row IDs must be unique.")
        row_ids.add(row_id)

        try:
            source_type = ManifestSourceType(row["source_type"])
        except ValueError as exc:
            raise StudioError(
                "MANIFEST_SOURCE_TYPE_INVALID",
                "Source type must be local_archive or zoom_recording.",
            ) from exc

        locator = row["source_locator"]
        secret_ref = row["secret_ref"]
        if source_type == ManifestSourceType.LOCAL_ARCHIVE:
            _validate_archive_locator(locator)
            if not (_PROMPT_REF.fullmatch(secret_ref) or _WINCRED_REF.fullmatch(secret_ref)):
                _fail(
                    "MANIFEST_SECRET_REF_INVALID",
                    "Local archives require a bounded prompt or Windows credential reference.",
                )
            if secret_ref.startswith("wincred://"):
                wincred_refs.add(secret_ref)
        else:
            if not _ZOOM_LOCATOR.fullmatch(locator):
                _fail(
                    "MANIFEST_SOURCE_LOCATOR_INVALID",
                    "Zoom locators must contain bounded recording and file identifiers.",
                )
            if secret_ref:
                _fail(
                    "MANIFEST_SECRET_REF_INVALID",
                    "Zoom rows use user OAuth and must leave secret_ref blank.",
                )

        display_name = row["display_name"]
        if (
            not display_name
            or len(display_name) > 160
            or display_name in {".", ".."}
            or "/" in display_name
            or "\\" in display_name
        ):
            _fail(
                "MANIFEST_DISPLAY_NAME_INVALID",
                "Display names must be bounded metadata and cannot contain a path.",
            )

        expected_sha256 = row["expected_sha256"] or None
        if expected_sha256 is not None and not _SHA256.fullmatch(expected_sha256):
            _fail(
                "MANIFEST_SHA256_INVALID",
                "Expected SHA-256 values must be blank or a lowercase 64-character digest.",
            )
        rows.append(
            ImportPlanRow(
                row_id=row_id,
                source_type=source_type,
                source_locator=locator,
                secret_ref=secret_ref,
                display_name=display_name,
                expected_sha256=expected_sha256,
            )
        )

    if len(wincred_refs) > MAX_WINCRED_REFERENCES:
        _fail(
            "MANIFEST_SECRET_REF_LIMIT_EXCEEDED",
            f"A manifest may reference at most {MAX_WINCRED_REFERENCES} Windows credentials.",
        )
    return rows


def _validate_archive_locator(locator: str) -> None:
    if not locator or len(locator) > 240 or "\\" in locator or ":" in locator:
        _fail(
            "MANIFEST_SOURCE_LOCATOR_INVALID",
            "Archive locators must be bounded relative POSIX paths.",
        )
    path = PurePosixPath(locator)
    if (
        path.is_absolute()
        or path.as_posix() != locator
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail(
            "MANIFEST_SOURCE_LOCATOR_INVALID",
            "Archive locators must remain inside the approved workspace.",
        )
    for part in path.parts:
        base_name = part.split(".", 1)[0].upper()
        if (
            not _ARCHIVE_PATH_SEGMENT.fullmatch(part)
            or part.endswith((" ", "."))
            or base_name in _WINDOWS_RESERVED_NAMES
        ):
            _fail(
                "MANIFEST_SOURCE_LOCATOR_INVALID",
                "Archive locators must use portable, non-reserved path segments.",
            )
    if path.suffix.lower() not in {".zip", ".7z"}:
        _fail(
            "MANIFEST_SOURCE_LOCATOR_INVALID",
            "Archive locators must identify a ZIP or 7z file.",
        )


def _parse_csv(payload: bytes) -> list[list[str]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StudioError(
            "MANIFEST_ENCODING_INVALID", "CSV manifests must use UTF-8 encoding."
        ) from exc
    if "\x00" in text:
        _fail("MANIFEST_ENCODING_INVALID", "CSV manifests cannot contain null characters.")
    try:
        return list(csv.reader(io.StringIO(text, newline=""), dialect="excel", strict=True))
    except csv.Error as exc:
        raise StudioError("MANIFEST_CSV_INVALID", "The CSV structure is invalid.") from exc


def _safe_zip_entries(payload: bytes) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except (zipfile.BadZipFile, OSError) as exc:
        raise StudioError("MANIFEST_XLSX_INVALID", "The XLSX package is invalid.") from exc
    infos = archive.infolist()
    if not infos or len(infos) > MAX_XLSX_ENTRIES:
        archive.close()
        _fail(
            "MANIFEST_XLSX_PACKAGE_UNSAFE",
            "The XLSX package exceeds its entry-count budget.",
        )
    entries: dict[str, zipfile.ZipInfo] = {}
    expanded = 0
    for info in infos:
        name = info.filename.replace("\\", "/")
        normalized = posixpath.normpath(name).lstrip("/")
        lowered = normalized.lower()
        if (
            name.startswith("/")
            or normalized in {"", "."}
            or normalized.startswith("../")
            or ":" in normalized
            or info.flag_bits & 0x1
            or (info.external_attr >> 16) & 0o170000 == 0o120000
            or lowered in entries
        ):
            archive.close()
            _fail(
                "MANIFEST_XLSX_PACKAGE_UNSAFE",
                "The XLSX package contains an unsafe or duplicate entry.",
            )
        expanded += info.file_size
        ratio = info.file_size / max(info.compress_size, 1)
        if expanded > MAX_XLSX_EXPANDED_BYTES or ratio > MAX_XLSX_COMPRESSION_RATIO:
            archive.close()
            _fail(
                "MANIFEST_XLSX_PACKAGE_UNSAFE",
                "The XLSX package exceeds its expansion budget.",
            )
        if any(part in lowered for part in _FORBIDDEN_XLSX_PATH_PARTS):
            archive.close()
            _fail(
                "MANIFEST_XLSX_FEATURE_FORBIDDEN",
                "The XLSX package contains a prohibited workbook feature.",
            )
        entries[lowered] = info
    return archive, entries


def _read_entry(
    archive: zipfile.ZipFile, entries: dict[str, zipfile.ZipInfo], name: str
) -> bytes:
    info = entries.get(name.lower())
    if info is None:
        _fail("MANIFEST_XLSX_INVALID", "The XLSX package is missing a required part.")
    try:
        return archive.read(info)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise StudioError("MANIFEST_XLSX_INVALID", "The XLSX package cannot be read.") from exc


def _validate_xlsx_relationships(
    archive: zipfile.ZipFile, entries: dict[str, zipfile.ZipInfo]
) -> None:
    for name, info in entries.items():
        if not name.endswith(".rels"):
            continue
        root = _xml_root(_read_entry(archive, entries, name))
        for relationship in root:
            if _local_name(relationship.tag) != "Relationship":
                continue
            target = relationship.attrib.get("Target", "")
            if (
                relationship.attrib.get("TargetMode", "").lower() == "external"
                or "\\" in target
                or target.startswith("//")
                or target.lower().startswith(("http:", "https:", "file:"))
            ):
                _fail(
                    "MANIFEST_XLSX_FEATURE_FORBIDDEN",
                    "External XLSX relationships are not allowed.",
                )


def _shared_strings(
    archive: zipfile.ZipFile, entries: dict[str, zipfile.ZipInfo]
) -> list[str]:
    info = entries.get("xl/sharedstrings.xml")
    if info is None:
        return []
    root = _xml_root(_read_entry(archive, entries, "xl/sharedstrings.xml"))
    values: list[str] = []
    for item in root:
        if _local_name(item.tag) == "si":
            values.append(
                "".join(node.text or "" for node in item.iter() if _local_name(node.tag) == "t")
            )
    return values


def _workbook_sheet_path(
    archive: zipfile.ZipFile, entries: dict[str, zipfile.ZipInfo]
) -> str:
    content_types = _read_entry(archive, entries, "[Content_Types].xml")
    lowered_types = content_types.lower()
    if any(
        marker in lowered_types
        for marker in (b"macroenabled", b"vbaproject", b"activex", b"binary")
    ):
        _fail(
            "MANIFEST_XLSX_FEATURE_FORBIDDEN",
            "Macro-enabled or executable workbook content is not allowed.",
        )
    workbook = _xml_root(_read_entry(archive, entries, "xl/workbook.xml"))
    if any(_local_name(node.tag) in _FORBIDDEN_WORKBOOK_ELEMENTS for node in workbook.iter()):
        _fail(
            "MANIFEST_XLSX_FEATURE_FORBIDDEN",
            "The workbook contains a prohibited hidden or executable feature.",
        )
    sheets = [node for node in workbook.iter() if _local_name(node.tag) == "sheet"]
    if (
        len(sheets) != 1
        or sheets[0].attrib.get("name") != "recordings"
        or sheets[0].attrib.get("state", "visible") != "visible"
    ):
        _fail(
            "MANIFEST_XLSX_WORKSHEET_INVALID",
            "XLSX manifests require exactly one visible worksheet named recordings.",
        )
    worksheet_parts = [name for name in entries if name.startswith("xl/worksheets/")]
    if len(worksheet_parts) != 1:
        _fail(
            "MANIFEST_XLSX_WORKSHEET_INVALID",
            "XLSX manifests may contain exactly one worksheet part.",
        )
    relationship_id = next(
        (value for key, value in sheets[0].attrib.items() if _local_name(key) == "id"),
        None,
    )
    relationships = _xml_root(
        _read_entry(archive, entries, "xl/_rels/workbook.xml.rels")
    )
    targets = {
        node.attrib.get("Id"): node.attrib.get("Target", "")
        for node in relationships
        if _local_name(node.tag) == "Relationship"
    }
    target = targets.get(relationship_id or "", "")
    if not target or "\\" in target:
        _fail("MANIFEST_XLSX_INVALID", "The workbook worksheet relationship is invalid.")
    if target.startswith("/"):
        normalized = posixpath.normpath(target).lstrip("/")
    else:
        normalized = posixpath.normpath(posixpath.join("xl", target))
    if normalized.lower() not in entries or not normalized.lower().startswith("xl/worksheets/"):
        _fail("MANIFEST_XLSX_INVALID", "The workbook worksheet target is invalid.")
    return normalized


def _cell_text(cell, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter() if _local_name(node.tag) == "t"
        )
    value_node = next(
        (node for node in cell if _local_name(node.tag) == "v"),
        None,
    )
    value = "" if value_node is None else (value_node.text or "")
    if not value:
        return ""
    if cell_type == "s":
        try:
            return shared[int(value)]
        except (ValueError, IndexError) as exc:
            raise StudioError(
                "MANIFEST_XLSX_INVALID", "The workbook shared-string reference is invalid."
            ) from exc
    if cell_type == "str":
        return value
    _fail(
        "MANIFEST_XLSX_CELL_TYPE_FORBIDDEN",
        "Manifest cells must be stored as text.",
    )
    raise AssertionError("unreachable")


def _parse_xlsx(payload: bytes) -> list[list[str]]:
    archive, entries = _safe_zip_entries(payload)
    try:
        _validate_xlsx_relationships(archive, entries)
        shared = _shared_strings(archive, entries)
        sheet_path = _workbook_sheet_path(archive, entries)
        sheet = _xml_root(_read_entry(archive, entries, sheet_path))
        for node in sheet.iter():
            local = _local_name(node.tag)
            if local in _FORBIDDEN_SHEET_ELEMENTS:
                _fail(
                    "MANIFEST_XLSX_FEATURE_FORBIDDEN",
                    "The worksheet contains a prohibited feature.",
                )
            if local in {"row", "col"} and _is_truthy_xml(node.attrib.get("hidden")):
                _fail(
                    "MANIFEST_XLSX_FEATURE_FORBIDDEN",
                    "Hidden workbook rows or columns are not allowed.",
                )
            if local == "col" and node.attrib.get("width", "").strip() in {"0", "0.0"}:
                _fail(
                    "MANIFEST_XLSX_FEATURE_FORBIDDEN",
                    "Zero-width workbook columns are not allowed.",
                )

        cells: dict[tuple[int, int], str] = {}
        maximum_row = 0
        for cell in (node for node in sheet.iter() if _local_name(node.tag) == "c"):
            reference = cell.attrib.get("r", "")
            match = _CELL_REFERENCE.fullmatch(reference)
            if not match:
                _fail("MANIFEST_XLSX_INVALID", "A worksheet cell reference is invalid.")
            column = _column_index(match.group(1))
            row = int(match.group(2))
            if column > len(MANIFEST_COLUMNS):
                _fail(
                    "MANIFEST_COLUMNS_INVALID",
                    "The worksheet contains data outside the seven manifest columns.",
                )
            if row > MAX_MANIFEST_ROWS + 1:
                _fail(
                    "MANIFEST_ROW_LIMIT_EXCEEDED",
                    f"A manifest may contain at most {MAX_MANIFEST_ROWS} recording rows.",
                    status=413,
                )
            key = (row, column)
            if key in cells:
                _fail("MANIFEST_XLSX_INVALID", "The worksheet contains a duplicate cell.")
            cells[key] = _cell_text(cell, shared)
            maximum_row = max(maximum_row, row)
        return [
            [cells.get((row, column), "") for column in range(1, len(MANIFEST_COLUMNS) + 1)]
            for row in range(1, maximum_row + 1)
        ]
    finally:
        archive.close()


def parse_manifest(
    *, filename: str | None, content_type: str | None, payload: bytes
) -> list[ImportPlanRow]:
    if not payload:
        _fail("MANIFEST_EMPTY", "The selected manifest is empty.")
    if len(payload) > MAX_MANIFEST_BYTES:
        _fail(
            "MANIFEST_REQUEST_TOO_LARGE",
            "The manifest exceeds the 5 MiB limit.",
            status=413,
        )
    manifest_type = _validate_filename_and_media_type(filename, content_type)
    raw_rows = _parse_csv(payload) if manifest_type == "csv" else _parse_xlsx(payload)
    return _normalize_table(raw_rows)


def _preview_row(row: ImportPlanRow) -> ImportPlanPreviewRow:
    if row.source_type == ManifestSourceType.ZOOM_RECORDING:
        provider = SecretProvider.ZOOM_OAUTH
        required = True
    elif row.secret_ref.startswith("prompt://"):
        provider = SecretProvider.PROMPT
        required = True
    else:
        provider = SecretProvider.WINDOWS_CREDENTIAL
        required = True
    return ImportPlanPreviewRow(
        row_id=row.row_id,
        source_type=row.source_type,
        source_locator=row.source_locator,
        secret_provider=provider,
        secret_required=required,
        display_name=row.display_name,
        expected_sha256=row.expected_sha256,
    )


class ImportPlanStore:
    """Bounded process-memory store; plans disappear on expiry or process exit."""

    def __init__(self, *, ttl_seconds: int, max_plans: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_plans = max_plans
        self._plans: dict[str, ImportPlan] = {}
        self._expiry_timers: dict[str, threading.Timer] = {}
        self._lock = threading.RLock()

    def _remove(self, plan_id: str) -> bool:
        with self._lock:
            removed = self._plans.pop(plan_id, None) is not None
            timer = self._expiry_timers.pop(plan_id, None)
            if timer is not None and timer is not threading.current_thread():
                timer.cancel()
            return removed

    def _expire(self, plan_id: str) -> None:
        self._remove(plan_id)

    def sweep_expired(self) -> int:
        now = utc_now()
        with self._lock:
            expired = [plan_id for plan_id, plan in self._plans.items() if plan.expires_at <= now]
            for plan_id in expired:
                self._remove(plan_id)
            return len(expired)

    def create(self, payload: bytes, rows: list[ImportPlanRow]) -> ImportPlan:
        with self._lock:
            self.sweep_expired()
            if len(self._plans) >= self.max_plans:
                _fail(
                    "IMPORT_PLAN_CAPACITY_REACHED",
                    "The preview capacity is full. Wait for an older plan to expire.",
                    status=409,
                )
            created_at = utc_now()
            plan = ImportPlan(
                id=str(uuid4()),
                created_at=created_at,
                expires_at=created_at + timedelta(seconds=self.ttl_seconds),
                manifest_sha256=hashlib.sha256(payload).hexdigest(),
                row_count=len(rows),
                rows=rows,
            )
            self._plans[plan.id] = plan
            timer = threading.Timer(self.ttl_seconds, self._expire, args=(plan.id,))
            timer.daemon = True
            self._expiry_timers[plan.id] = timer
            timer.start()
            return plan

    def get(self, plan_id: str) -> ImportPlan:
        try:
            normalized = str(UUID(plan_id))
        except ValueError as exc:
            raise StudioError(
                "IMPORT_PLAN_NOT_FOUND", "The import plan was not found.", http_status=404
            ) from exc
        with self._lock:
            self.sweep_expired()
            plan = self._plans.get(normalized)
            if plan is None:
                _fail("IMPORT_PLAN_NOT_FOUND", "The import plan was not found.", status=404)
            return plan

    def active_count(self) -> int:
        with self._lock:
            self.sweep_expired()
            return len(self._plans)

    def close(self) -> None:
        with self._lock:
            for timer in self._expiry_timers.values():
                timer.cancel()
            self._expiry_timers.clear()
            self._plans.clear()

    @staticmethod
    def preview(plan: ImportPlan) -> ImportPlanPreview:
        return ImportPlanPreview(
            plan_id=plan.id,
            created_at=plan.created_at,
            expires_at=plan.expires_at,
            manifest_sha256=plan.manifest_sha256,
            row_count=plan.row_count,
            rows=[_preview_row(row) for row in plan.rows],
        )
