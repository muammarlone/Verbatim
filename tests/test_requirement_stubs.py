"""Tests for blocked-story pre-implementation requirement stubs.

Each blocked story must have a stub in architecture/pre-implementation/
documenting its blocking conditions, threat model requirement, claim boundary,
and acceptance evidence. Tests verify stubs exist, are complete, and do not
contain implementation claims or enabled feature flags.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUB_DIR = ROOT / "architecture" / "pre-implementation"

REQUIRED_STUBS = {
    "STS-101": "STS-101-speaker-diarization.md",
    "STS-103": "STS-103-os-authentication.md",
    "STS-107": "STS-107-credential-locker.md",
    "STS-108": "STS-108-protected-archive.md",
    "STS-109": "STS-109-zoom-oauth.md",
    "STS-119": "STS-119-entity-detection.md",
    "STS-120": "STS-120-redaction.md",
    "STS-121": "STS-121-teams-connector.md",
    "STS-122": "STS-122-zoom-manifest-connector.md",
}

REQUIRED_SECTIONS = [
    "blocking condition",
    "acceptance evidence",
    "claim boundary",
    "assumption",
    "not authorized",
    "not implemented",
]

FORBIDDEN_TERMS = [
    "STS_ZOOM_CONNECTOR_ENABLED=true",
    "STS_MANIFEST_INTAKE_ENABLED=true",
    "STS_PROTECTED_ARCHIVE_ENABLED=true",
    "implementation is complete",
    "fully implemented",
    "production ready",
]


def _stub_path(filename: str) -> Path:
    return STUB_DIR / filename


def _stub_text(filename: str) -> str:
    return _stub_path(filename).read_text(encoding="utf-8")


# ── Directory and file presence ───────────────────────────────────────────────

def test_pre_implementation_directory_exists():
    assert STUB_DIR.is_dir(), "architecture/pre-implementation/ directory missing"


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_requirement_stub_exists(story, filename):
    assert _stub_path(filename).is_file(), (
        f"Pre-implementation stub missing for {story}: {filename}"
    )


# ── Required sections present ─────────────────────────────────────────────────

@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_has_blocking_conditions(story, filename):
    text = _stub_text(filename).lower()
    assert "blocking condition" in text, f"{story}: missing 'blocking condition' section"


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_has_acceptance_evidence(story, filename):
    text = _stub_text(filename).lower()
    assert "acceptance evidence" in text, f"{story}: missing 'acceptance evidence' section"


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_has_claim_boundary(story, filename):
    text = _stub_text(filename).lower()
    assert "claim boundary" in text, f"{story}: missing 'claim boundary' section"


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_claim_boundary_has_assumption(story, filename):
    text = _stub_text(filename).lower()
    assert "assumption" in text, f"{story}: claim_boundary section must include ASSUMPTION label"


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_says_not_authorized(story, filename):
    text = _stub_text(filename).lower()
    assert "not authorized" in text or "blocked" in text, (
        f"{story}: stub must state the feature is not authorized for implementation"
    )


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_says_not_implemented(story, filename):
    text = _stub_text(filename).lower()
    assert "not implemented" in text or "no partial implementation" in text, (
        f"{story}: stub must state the feature is not implemented"
    )


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_mentions_threat_model(story, filename):
    text = _stub_text(filename).lower()
    assert "threat model" in text, f"{story}: stub must reference a required threat model"


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_mentions_owner(story, filename):
    text = _stub_text(filename).lower()
    assert "owner" in text, f"{story}: stub must specify an owner requirement"


# ── Forbidden implementation claims ───────────────────────────────────────────

@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_has_no_enabled_connector_flags(story, filename):
    text = _stub_text(filename)
    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in text, (
            f"{story}: stub contains forbidden term: {forbidden!r}"
        )


@pytest.mark.parametrize("story, filename", REQUIRED_STUBS.items())
def test_stub_status_is_blocked(story, filename):
    text = _stub_text(filename)
    assert "BLOCKED" in text or "not authorized" in text.lower(), (
        f"{story}: stub must have BLOCKED status or state not authorized"
    )
