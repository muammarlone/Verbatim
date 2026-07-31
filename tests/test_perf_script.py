"""Tests for QG-06 synthetic profiling script and evidence schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
PERF_SCRIPT = REPO_ROOT / "scripts" / "perf" / "run_synthetic_profiling.py"
PROTOCOL_FILE = REPO_ROOT / "evidence" / "capacity" / "profiling-protocol.json"
PROFILING_RESULTS_DIR = REPO_ROOT / "evidence" / "capacity"


def _load_protocol() -> dict:
    return json.loads(PROTOCOL_FILE.read_text(encoding="utf-8"))


def _find_results() -> list[Path]:
    return sorted(PROFILING_RESULTS_DIR.glob("docker-profiling-*.json"))


# ---------------------------------------------------------------------------
# Script existence and safety guards
# ---------------------------------------------------------------------------


def test_profiling_script_exists() -> None:
    assert PERF_SCRIPT.is_file(), f"Missing: {PERF_SCRIPT}"


def test_profiling_script_has_mock_mode() -> None:
    text = PERF_SCRIPT.read_text(encoding="utf-8")
    assert "--mock" in text


def test_profiling_script_has_live_guard() -> None:
    text = PERF_SCRIPT.read_text(encoding="utf-8")
    assert "VERBATIM_PERF_LIVE" in text


def test_profiling_script_no_not_qualified_endpoint_missing() -> None:
    text = PERF_SCRIPT.read_text(encoding="utf-8")
    assert "not_qualified_endpoint" in text


# ---------------------------------------------------------------------------
# Protocol schema
# ---------------------------------------------------------------------------


def test_protocol_file_exists() -> None:
    assert PROTOCOL_FILE.is_file(), f"Missing: {PROTOCOL_FILE}"


def test_protocol_has_scenarios() -> None:
    protocol = _load_protocol()
    assert len(protocol.get("scenarios", [])) >= 5


def test_protocol_has_sc04_full_disk_pending_human() -> None:
    protocol = _load_protocol()
    sc04 = next((s for s in protocol["scenarios"] if s["id"] == "SC-04"), None)
    assert sc04 is not None, "SC-04 full-disk scenario missing"
    assert sc04.get("requires_human") is True, "SC-04 must require human"


def test_protocol_has_size_brackets() -> None:
    protocol = _load_protocol()
    brackets = protocol.get("size_brackets", {})
    assert "small" in brackets
    assert "medium" in brackets
    assert "large" in brackets


# ---------------------------------------------------------------------------
# Profiling results schema
# ---------------------------------------------------------------------------


def test_profiling_results_exist() -> None:
    results = _find_results()
    assert results, "No docker-profiling-*.json files in evidence/capacity/"


def test_profiling_result_not_qualified_endpoint() -> None:
    for path in _find_results():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("not_qualified_endpoint") is True, \
            f"{path.name}: missing not_qualified_endpoint=true"


def test_profiling_result_has_required_fields() -> None:
    for path in _find_results():
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in ("schema_version", "run_id", "run_date", "gate", "environment", "scenarios"):
            assert field in data, f"{path.name}: missing field '{field}'"


def test_profiling_result_scenario_ok_has_p50_p95() -> None:
    for path in _find_results():
        data = json.loads(path.read_text(encoding="utf-8"))
        for sc in data.get("scenarios", []):
            if sc.get("status") == "OK":
                assert sc.get("p50_seconds") is not None, \
                    f"{path.name} {sc['scenario_id']}: OK status but missing p50_seconds"
                assert sc.get("p95_seconds") is not None, \
                    f"{path.name} {sc['scenario_id']}: OK status but missing p95_seconds"


def test_profiling_result_has_pending_human_sc04() -> None:
    for path in _find_results():
        data = json.loads(path.read_text(encoding="utf-8"))
        sc04 = next(
            (s for s in data.get("scenarios", []) if s.get("scenario_id") == "SC-04"),
            None,
        )
        if sc04 is not None:
            assert sc04.get("status") == "PENDING_HUMAN", \
                f"{path.name} SC-04 must be PENDING_HUMAN (requires human IT action)"


# ---------------------------------------------------------------------------
# Script runs in mock mode (integration — runs the actual script)
# ---------------------------------------------------------------------------


def test_profiling_script_runs_mock_mode(tmp_path: Path) -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(PERF_SCRIPT),
            "--protocol",
            str(PROTOCOL_FILE),
            "--output-dir",
            str(tmp_path),
            "--mock",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Profiling script exited {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    out_files = list(tmp_path.glob("docker-profiling-*.json"))
    assert out_files, "Script ran but produced no output JSON"
    data = json.loads(out_files[0].read_text(encoding="utf-8"))
    assert data["not_qualified_endpoint"] is True
    assert data["mock_mode"] is True
    assert len(data["scenarios"]) >= 5
