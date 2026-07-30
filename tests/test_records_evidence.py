"""QG-05: Records and privacy evidence structure validation.

Verifies that the required evidence directory, sign-off stub, and guidance
documents exist. The sign-off JSON is an OPEN placeholder until the records
and privacy lead completes the deletion drill and approves the export matrix
and training requirements.

Filled sign-off checks run only when the slot is filled — open placeholders
are skipped so CI stays green while the gate is in progress.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = ROOT / "evidence" / "records"

REQUIRED_FILES = [
    "README.md",
    "export-dlp-matrix.md",
    "deletion-drill-guide.md",
    "training-disclosure.md",
    "sign-off.json",
]

REQUIRED_README_PHRASES = [
    "QG-05",
    "records and privacy lead",
    "claim boundary",
    "sign-off.json",
    "deletion drill",
]

REQUIRED_DLP_MATRIX_PHRASES = [
    "QG-05",
    "PROHIBITED",
    "sensitivity",
    "retention",
]

REQUIRED_DRILL_PHRASES = [
    "QG-05",
    "audit log",
    "STS_DATA_DIR",
    "does not",  # "does not delete" the original files
]

REQUIRED_TRAINING_PHRASES = [
    "QG-05",
    "recording authority",
    "incident",
    "deletion",
]


def _is_placeholder(data: dict) -> bool:
    status = data.get("_status", "")
    return "OPEN" in status or "not yet collected" in status


# ── Directory and file presence ───────────────────────────────────────────────

def test_records_evidence_directory_exists() -> None:
    assert RECORDS_DIR.is_dir(), "evidence/records/ directory missing; create it per QG-05 protocol"


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_required_records_file_exists(filename: str) -> None:
    assert (RECORDS_DIR / filename).is_file(), f"evidence/records/{filename} missing"


# ── README ────────────────────────────────────────────────────────────────────

def test_records_readme_mentions_required_topics() -> None:
    readme = (RECORDS_DIR / "README.md").read_text(encoding="utf-8").lower()
    for phrase in REQUIRED_README_PHRASES:
        assert phrase.lower() in readme, f"records README.md missing expected phrase: {phrase!r}"


# ── Export DLP matrix ─────────────────────────────────────────────────────────

def test_export_dlp_matrix_mentions_required_topics() -> None:
    matrix = (RECORDS_DIR / "export-dlp-matrix.md").read_text(encoding="utf-8").lower()
    for phrase in REQUIRED_DLP_MATRIX_PHRASES:
        assert phrase.lower() in matrix, f"export-dlp-matrix.md missing expected phrase: {phrase!r}"


def test_export_dlp_matrix_lists_verbatim_formats() -> None:
    matrix = (RECORDS_DIR / "export-dlp-matrix.md").read_text(encoding="utf-8")
    for fmt in ("TXT", "SRT", "VTT", "MD", "JSON"):
        assert fmt in matrix, f"export-dlp-matrix.md must mention export format {fmt}"


# ── Deletion drill guide ──────────────────────────────────────────────────────

def test_deletion_drill_covers_required_scenarios() -> None:
    drill = (RECORDS_DIR / "deletion-drill-guide.md").read_text(encoding="utf-8")
    for phrase in REQUIRED_DRILL_PHRASES:
        assert phrase in drill, f"deletion-drill-guide.md missing expected phrase: {phrase!r}"


def test_deletion_drill_distinguishes_verbatim_boundary_from_external_copies() -> None:
    drill = (RECORDS_DIR / "deletion-drill-guide.md").read_text(encoding="utf-8")
    assert "browser" in drill.lower() or "download" in drill.lower()
    assert "output folder" in drill.lower() or "batch output" in drill.lower()


# ── Training disclosure ───────────────────────────────────────────────────────

def test_training_disclosure_covers_required_topics() -> None:
    training = (RECORDS_DIR / "training-disclosure.md").read_text(encoding="utf-8").lower()
    for phrase in REQUIRED_TRAINING_PHRASES:
        assert phrase.lower() in training, f"training-disclosure.md missing expected phrase: {phrase!r}"


# ── Sign-off JSON ─────────────────────────────────────────────────────────────

def test_sign_off_json_is_valid() -> None:
    data = json.loads((RECORDS_DIR / "sign-off.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "_schema" in data
    assert "_status" in data
    assert "_gate" in data
    assert data["_gate"] == "QG-05"


def test_filled_sign_off_meets_schema_requirements() -> None:
    data = json.loads((RECORDS_DIR / "sign-off.json").read_text(encoding="utf-8"))
    if _is_placeholder(data):
        pytest.skip("Sign-off slot not yet filled by records and privacy lead")
    required = [
        "date",
        "lead_name",
        "retention_days_approved",
        "approved_export_destinations",
        "backup_exclusion_confirmed",
        "deletion_drill_witnessed",
        "operator_training_approved",
        "claim_boundary",
    ]
    for field in required:
        assert field in data, f"sign-off.json filled slot missing required field {field!r}"
    assert data["deletion_drill_witnessed"] is True
    assert data["operator_training_approved"] is True
    assert len(data["claim_boundary"]) >= 20
    assert data.get("open_findings", []) == [], "QG-05 cannot be passed with open findings"
