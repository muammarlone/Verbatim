"""STS-114: Cross-environment evidence structure tests.

Verifies that the scaffold is present, all required environment directories
exist, run-metadata.json stubs are valid placeholders or correctly filled,
and no filled slot falsely claims enabled connector flags.

These tests PASS when slots are unfilled (OPEN stubs). They are designed to
remain green in CI so the structure can be committed. --strict mode (manual
only) would fail on unfilled slots — that's for pre-pilot gate verification.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT / "evidence" / "environments"
SCHEMA_PATH = ENV_DIR / "manifest-schema.json"

REQUIRED_ENVS = [
    "windows-runner",
    "docker-qualification",
    "codespaces",
    "offline-regression",
]

REQUIRED_CONNECTOR_FLAGS_FALSE = [
    "STS_ZOOM_CONNECTOR_ENABLED",
    "STS_MANIFEST_INTAKE_ENABLED",
    "STS_PROTECTED_ARCHIVE_ENABLED",
]


def _is_placeholder(data: dict) -> bool:
    return "_status" in data and "OPEN" in data.get("_status", "")


def _read_meta(env: str) -> dict:
    path = ENV_DIR / env / "run-metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ── Directory structure ───────────────────────────────────────────────────────

def test_environments_directory_exists():
    assert ENV_DIR.is_dir(), "evidence/environments/ directory is missing"


def test_manifest_schema_exists():
    assert SCHEMA_PATH.is_file(), "evidence/environments/manifest-schema.json is missing"


def test_manifest_schema_is_valid_json():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert "$schema" in schema
    assert "required" in schema


def test_manifest_schema_requires_connector_flags():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    required = schema.get("required", [])
    assert "connector_flags" in required


def test_manifest_schema_has_all_required_environments():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    enum_values = (
        schema.get("properties", {})
        .get("environment", {})
        .get("enum", [])
    )
    for env in REQUIRED_ENVS:
        assert env in enum_values, f"Schema missing environment: {env}"


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_environment_directory_exists(env):
    assert (ENV_DIR / env).is_dir(), f"evidence/environments/{env}/ directory missing"


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_run_metadata_json_exists(env):
    assert (ENV_DIR / env / "run-metadata.json").is_file(), (
        f"evidence/environments/{env}/run-metadata.json missing"
    )


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_run_metadata_json_is_valid_json(env):
    data = _read_meta(env)
    assert isinstance(data, dict)


# ── Placeholder / filled slot checks ─────────────────────────────────────────

@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_run_metadata_is_placeholder_or_filled(env):
    data = _read_meta(env)
    is_placeholder = _is_placeholder(data)
    is_filled = "schema_version" in data
    assert is_placeholder or is_filled, (
        f"{env}/run-metadata.json is neither a valid placeholder nor a filled slot"
    )


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_placeholder_metadata_has_status_key(env):
    data = _read_meta(env)
    if _is_placeholder(data):
        assert "_status" in data
        assert "OPEN" in data["_status"]
        assert "_gate" in data
        assert "_schema" in data


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_filled_metadata_connector_flags_all_false(env):
    data = _read_meta(env)
    if _is_placeholder(data):
        pytest.skip("Slot not yet filled")
    flags = data.get("connector_flags", {})
    for flag in REQUIRED_CONNECTOR_FLAGS_FALSE:
        assert flags.get(flag) is False, (
            f"{env}: connector_flags.{flag} must be false in filled evidence"
        )


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_filled_metadata_no_pytest_failures(env):
    data = _read_meta(env)
    if _is_placeholder(data):
        pytest.skip("Slot not yet filled")
    assert data.get("pytest_failed", 1) == 0


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_filled_metadata_has_claim_boundary(env):
    data = _read_meta(env)
    if _is_placeholder(data):
        pytest.skip("Slot not yet filled")
    assert data.get("claim_boundary"), f"{env}: claim_boundary must not be empty"


@pytest.mark.parametrize("env", REQUIRED_ENVS)
def test_filled_metadata_minimum_three_negative_controls(env):
    data = _read_meta(env)
    if _is_placeholder(data):
        pytest.skip("Slot not yet filled")
    assert data.get("negative_controls_total", 0) >= 3


# ── Readme disclosure ─────────────────────────────────────────────────────────

def test_environments_readme_exists():
    assert (ENV_DIR / "README.md").is_file()


def test_environments_readme_has_claim_boundary():
    text = (ENV_DIR / "README.md").read_text(encoding="utf-8").lower()
    assert "claim boundary" in text or "does not prove" in text


def test_environments_readme_mentions_all_envs():
    text = (ENV_DIR / "README.md").read_text(encoding="utf-8")
    for env in REQUIRED_ENVS:
        assert env in text, f"README.md missing reference to environment: {env}"
