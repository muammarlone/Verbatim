"""Tests for STS-110 installer build scripts — QG-02.

Verifies script presence, guard enforcement, manifest structure,
and absence of hardcoded credentials. No PowerShell execution required.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
BUILD_DIR = REPO_ROOT / "scripts" / "build"
TEMPLATE_DIR = BUILD_DIR / "templates"

WHEELHOUSE_SCRIPT = BUILD_DIR / "build_offline_wheelhouse.ps1"
MSIX_SCRIPT = BUILD_DIR / "build_msix.ps1"
VERIFY_SCRIPT = BUILD_DIR / "verify_wheelhouse_hashes.ps1"
MANIFEST_TEMPLATE = TEMPLATE_DIR / "AppxManifest.xml"


# ---------------------------------------------------------------------------
# Script existence
# ---------------------------------------------------------------------------


def test_wheelhouse_script_exists() -> None:
    assert WHEELHOUSE_SCRIPT.is_file(), f"Missing: {WHEELHOUSE_SCRIPT}"


def test_msix_script_exists() -> None:
    assert MSIX_SCRIPT.is_file(), f"Missing: {MSIX_SCRIPT}"


def test_verify_script_exists() -> None:
    assert VERIFY_SCRIPT.is_file(), f"Missing: {VERIFY_SCRIPT}"


def test_manifest_template_exists() -> None:
    assert MANIFEST_TEMPLATE.is_file(), f"Missing: {MANIFEST_TEMPLATE}"


# ---------------------------------------------------------------------------
# Guard presence in wheelhouse script
# ---------------------------------------------------------------------------


def test_wheelhouse_script_has_guard() -> None:
    text = WHEELHOUSE_SCRIPT.read_text(encoding="utf-8")
    assert "VERBATIM_BUILD_PRODUCTION_WHEELHOUSE" in text


def test_wheelhouse_script_exits_on_missing_guard() -> None:
    text = WHEELHOUSE_SCRIPT.read_text(encoding="utf-8")
    assert "exit 1" in text


# ---------------------------------------------------------------------------
# Guard presence and no-self-assign in MSIX script
# ---------------------------------------------------------------------------


def test_msix_script_has_guard() -> None:
    text = MSIX_SCRIPT.read_text(encoding="utf-8")
    assert "VERBATIM_INSTALLER_PRODUCTION_READY" in text


def test_msix_script_guard_value_is_compared_not_assigned() -> None:
    text = MSIX_SCRIPT.read_text(encoding="utf-8")
    # Must check for equality (-ne or -eq) but must NOT self-assign the bypass value.
    # An assignment would look like: $env:VERBATIM_INSTALLER_PRODUCTION_READY = 'signed-and-qualified'
    # The comparison looks like: -ne 'signed-and-qualified'
    has_comparison = "signed-and-qualified" in text
    assert has_comparison, "Guard value 'signed-and-qualified' not found in comparison"
    # Detect self-assignment pattern: $env:VAR = 'signed-and-qualified' (with optional spaces)
    self_assign = re.search(
        r"\$env:VERBATIM_INSTALLER_PRODUCTION_READY\s*=\s*['\"]signed-and-qualified['\"]",
        text,
    )
    assert self_assign is None, "Script must NOT self-assign the bypass value"


def test_msix_script_exits_on_missing_guard() -> None:
    text = MSIX_SCRIPT.read_text(encoding="utf-8")
    assert "exit 1" in text


def test_msix_script_references_signing_instructions() -> None:
    text = MSIX_SCRIPT.read_text(encoding="utf-8")
    assert "signtool" in text.lower()


# ---------------------------------------------------------------------------
# AppxManifest.xml structure
# ---------------------------------------------------------------------------


def test_manifest_is_valid_xml() -> None:
    tree = ET.parse(MANIFEST_TEMPLATE)
    root = tree.getroot()
    assert root is not None


def test_manifest_has_identity_element() -> None:
    tree = ET.parse(MANIFEST_TEMPLATE)
    ns = {"pkg": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
    identity = tree.find(".//pkg:Identity", ns)
    assert identity is not None


def test_manifest_has_placeholder_publisher() -> None:
    text = MANIFEST_TEMPLATE.read_text(encoding="utf-8")
    assert "PLACEHOLDER_PUBLISHER_DISTINGUISHED_NAME" in text


def test_manifest_has_min_os_version() -> None:
    text = MANIFEST_TEMPLATE.read_text(encoding="utf-8")
    assert "10.0.19041.0" in text


# ---------------------------------------------------------------------------
# No hardcoded credentials
# ---------------------------------------------------------------------------


CREDENTIAL_PATTERNS = [
    r"password\s*=\s*['\"][^'\"]{4,}",
    r"secret\s*=\s*['\"][^'\"]{4,}",
    r"api[_-]?key\s*=\s*['\"][^'\"]{4,}",
    r"token\s*=\s*['\"][^'\"]{4,}",
]


@pytest.mark.parametrize("script", [WHEELHOUSE_SCRIPT, MSIX_SCRIPT, VERIFY_SCRIPT])
def test_no_hardcoded_credentials_in_scripts(script: Path) -> None:
    text = script.read_text(encoding="utf-8").lower()
    for pattern in CREDENTIAL_PATTERNS:
        match = re.search(pattern, text)
        assert match is None, f"Potential credential found in {script.name}: {match.group() if match else ''}"


# ---------------------------------------------------------------------------
# Verify script checks hashes
# ---------------------------------------------------------------------------


def test_verify_script_contains_hash_check() -> None:
    text = VERIFY_SCRIPT.read_text(encoding="utf-8")
    assert "SHA256" in text or "sha256" in text.lower()


def test_verify_script_exits_nonzero_on_failure() -> None:
    text = VERIFY_SCRIPT.read_text(encoding="utf-8")
    assert "exit 2" in text
