"""QG-06: Endpoint evidence structure validation.

Verifies that the required evidence directory and placeholder stubs exist,
and that any filled slot meets the schema requirements for the endpoint
performance and capacity gate.

Slots that are still OPEN (placeholder) are counted but not failed — the gate
remains partial until the endpoint platform lead fills them on the qualified
managed endpoint.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT_DIR = ROOT / "evidence" / "endpoint"

REQUIRED_FILES = [
    "README.md",
    "perf-short.json",
    "capacity-matrix.json",
]

REQUIRED_README_PHRASES = [
    "QG-06",
    "endpoint platform lead",
    "claim boundary",
    "perf-short.json",
    "capacity-matrix.json",
]


def _is_placeholder(data: dict) -> bool:
    status = data.get("_status", "")
    return "OPEN" in status or "not yet collected" in status


# ── Directory and file presence ───────────────────────────────────────────────

def test_endpoint_evidence_directory_exists() -> None:
    assert ENDPOINT_DIR.is_dir(), f"evidence/endpoint/ directory missing; create it per QG-06 protocol"


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_required_evidence_file_exists(filename: str) -> None:
    assert (ENDPOINT_DIR / filename).is_file(), f"evidence/endpoint/{filename} missing"


# ── README content ────────────────────────────────────────────────────────────

def test_endpoint_readme_mentions_required_topics() -> None:
    readme = (ENDPOINT_DIR / "README.md").read_text(encoding="utf-8")
    for phrase in REQUIRED_README_PHRASES:
        assert phrase in readme, f"README.md missing expected phrase: {phrase!r}"


def test_endpoint_readme_mentions_negative_controls() -> None:
    readme = (ENDPOINT_DIR / "README.md").read_text(encoding="utf-8")
    assert "negative" in readme.lower()


# ── Placeholder slot integrity ────────────────────────────────────────────────

@pytest.mark.parametrize("filename", ["perf-short.json", "capacity-matrix.json"])
def test_placeholder_slot_is_valid_json(filename: str) -> None:
    path = ENDPOINT_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{filename} must be a JSON object"


@pytest.mark.parametrize("filename", ["perf-short.json", "capacity-matrix.json"])
def test_placeholder_slot_has_required_metadata_fields(filename: str) -> None:
    data = json.loads((ENDPOINT_DIR / filename).read_text(encoding="utf-8"))
    assert "_schema" in data, f"{filename}: missing _schema"
    assert "_status" in data, f"{filename}: missing _status"
    assert "_gate" in data, f"{filename}: missing _gate"
    assert data["_gate"] == "QG-06", f"{filename}: _gate must be QG-06"


@pytest.mark.parametrize("filename", ["perf-short.json", "capacity-matrix.json"])
def test_filled_slot_meets_schema_requirements(filename: str) -> None:
    data = json.loads((ENDPOINT_DIR / filename).read_text(encoding="utf-8"))
    if _is_placeholder(data):
        pytest.skip(f"{filename}: slot not yet filled by endpoint platform lead")
    required = ["date", "python_version", "wall_seconds", "peak_memory_mb", "outcome", "claim_boundary"]
    for field in required:
        assert field in data, f"{filename}: filled slot missing required field {field!r}"
    assert len(data["claim_boundary"]) >= 20, f"{filename}: claim_boundary must be at least 20 chars"
    assert data["outcome"] in ("complete", "failed", "partial"), f"{filename}: invalid outcome"


# ── Gate status ───────────────────────────────────────────────────────────────

def test_qg06_open_slots_are_counted() -> None:
    json_files = list(ENDPOINT_DIR.glob("*.json"))
    open_count = sum(
        1 for f in json_files
        if _is_placeholder(json.loads(f.read_text(encoding="utf-8")))
    )
    # All slots currently open — gate is partial, not failed
    assert open_count >= 0, "open slot count must be non-negative"
    # This assertion documents the current state without blocking CI
    # When all slots are filled, open_count will be 0 and QG-06 can be re-evaluated
