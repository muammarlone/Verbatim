"""STS-110: Installer prep completeness tests.

Verifies that all four installer scripts (Install, Repair, Update, Uninstall):
  - Exist and are well-formed PowerShell stubs
  - Have the production guard sentinel
  - Do not self-assign the bypass value
  - Require administrator privilege (Install/Repair)
  - Have Set-StrictMode and $ErrorActionPreference = 'Stop'
  - Reference sbom/hash-manifest.json for verification
  - Have TODO markers (not falsely claiming completeness)
  - Do not hardcode credentials, tokens, or passwords
  - Do not make external network calls (no Invoke-WebRequest, curl, wget)

IT execution on a clean managed endpoint is required before QG-02 can close.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALL_DIR = ROOT / "scripts" / "install"

SCRIPTS = {
    "Install": "Install-Verbatim.ps1",
    "Repair": "Repair-Verbatim.ps1",
    "Update": "Update-Verbatim.ps1",
    "Uninstall": "Uninstall-Verbatim.ps1",
}

SENTINEL = "VERBATIM_INSTALLER_PRODUCTION_READY"
BYPASS_VALUE = "signed-and-qualified"

FORBIDDEN_NETWORK_CMDLETS = [
    "Invoke-WebRequest",
    "Invoke-RestMethod",
    "curl",
    "wget",
    "Start-BitsTransfer",
]

FORBIDDEN_CREDENTIAL_PATTERNS = [
    "password",
    "secret",
    "token",
    "api_key",
    "client_secret",
]


def _text(script_name: str) -> str:
    return (INSTALL_DIR / script_name).read_text(encoding="utf-8")


# ── File existence ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_exists(script_name):
    assert (INSTALL_DIR / script_name).is_file(), (
        f"scripts/install/{script_name} is missing"
    )


# ── Production guard sentinel ──────────────────────────────────────────────────

@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_has_sentinel_check(script_name):
    text = _text(script_name)
    assert SENTINEL in text, f"{script_name}: missing {SENTINEL} guard"


@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_checks_sentinel_before_using_it(script_name):
    text = _text(script_name)
    sentinel_pos = text.find(SENTINEL)
    bypass_pos = text.find(BYPASS_VALUE)
    assert bypass_pos > sentinel_pos, (
        f"{script_name}: {BYPASS_VALUE!r} appears before the guard check — potential bypass"
    )


@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_does_not_self_assign_bypass_before_guard(script_name):
    text = _text(script_name)
    before_guard = text.split(SENTINEL, 1)[0]
    assert BYPASS_VALUE not in before_guard, (
        f"{script_name}: self-assigns bypass value before guard — would bypass its own check"
    )


# ── PowerShell safety settings ────────────────────────────────────────────────

@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_has_strict_mode(script_name):
    text = _text(script_name)
    assert "Set-StrictMode" in text, f"{script_name}: must use Set-StrictMode"


@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_has_stop_error_preference(script_name):
    text = _text(script_name)
    assert "ErrorActionPreference" in text and "Stop" in text, (
        f"{script_name}: must set $ErrorActionPreference = 'Stop'"
    )


@pytest.mark.parametrize("script_name", ["Install-Verbatim.ps1", "Repair-Verbatim.ps1"])
def test_script_requires_administrator(script_name):
    text = _text(script_name)
    assert "#Requires -RunAsAdministrator" in text, (
        f"{script_name}: must require administrator privilege"
    )


# ── Hash manifest reference ───────────────────────────────────────────────────

def test_install_references_hash_manifest():
    text = _text("Install-Verbatim.ps1")
    assert "hash-manifest.json" in text, (
        "Install script must reference sbom/hash-manifest.json for hash verification"
    )


# ── TODO markers (not falsely complete) ───────────────────────────────────────

@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_has_todo_markers(script_name):
    text = _text(script_name)
    assert "TODO" in text, (
        f"{script_name}: must have TODO markers — it is a preparatory stub, not a completed installer"
    )


@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_self_describes_as_stub(script_name):
    text = _text(script_name).lower()
    assert "stub" in text or "preparatory" in text, (
        f"{script_name}: must self-describe as a preparatory stub"
    )


# ── No external network calls ─────────────────────────────────────────────────

@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_has_no_network_cmdlets(script_name):
    text = _text(script_name)
    for cmdlet in FORBIDDEN_NETWORK_CMDLETS:
        assert cmdlet not in text, (
            f"{script_name}: must not contain network cmdlet {cmdlet!r} — installer must work offline"
        )


# ── No hardcoded credentials ──────────────────────────────────────────────────

@pytest.mark.parametrize("script_name", SCRIPTS.values())
def test_script_has_no_hardcoded_credentials(script_name):
    text = _text(script_name).lower()
    # ADR-005 and sentinel guard check naturally reference 'password' in comment context.
    # Flag only suspicious assignment patterns (= "..." or = '...' near credential keywords).
    import re
    assignment_pattern = re.compile(
        r"""(?:password|secret|token|api_key)\s*=\s*['"][^'"]{4,}['"]""",
        re.IGNORECASE,
    )
    matches = assignment_pattern.findall(text)
    assert not matches, (
        f"{script_name}: hardcoded credential pattern found: {matches}"
    )


# ── ADR and gate linkage in Install ──────────────────────────────────────────

def test_install_references_adr_005():
    text = _text("Install-Verbatim.ps1")
    assert "ADR-005" in text or "adr-005" in text.lower(), (
        "Install script must reference ADR-005 (Windows installer packaging decision)"
    )


def test_install_references_qg_02():
    text = _text("Install-Verbatim.ps1")
    assert "QG-02" in text, "Install script must reference QG-02 (endpoint qualification gate)"
