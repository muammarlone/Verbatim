"""Supply chain negative tests for QG-02 preparation.

Tests that the sbom artifacts are structurally valid and that the hash-manifest
schema correctly rejects or signals incomplete dispositions. Does NOT test
endpoint-qualified items (wheel hashes, model hash, FFmpeg hash) — those require
the clean-machine qualification step documented in sbom/hash-manifest.json.

Linked story: STS-117
Linked gate:  QG-02
Linked risk:  R-17
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SBOM_TRANSITIVE = ROOT / "sbom" / "transitive-dependency-sbom.cdx.json"
VULNERABILITY_DISPOSITION = ROOT / "sbom" / "vulnerability-disposition.json"
HASH_MANIFEST = ROOT / "sbom" / "hash-manifest.json"
REQUIREMENTS_LOCK = ROOT / "sbom" / "requirements.lock"
REQUIREMENTS_TXT = ROOT / "requirements.txt"
ADR_005 = ROOT / "architecture" / "decisions" / "ADR-005-windows-installer-packaging.md"
INSTALL_SCRIPTS = ROOT / "scripts" / "install"


# ---------------------------------------------------------------------------
# Artifact presence
# ---------------------------------------------------------------------------


def test_transitive_sbom_exists() -> None:
    assert SBOM_TRANSITIVE.is_file(), "sbom/transitive-dependency-sbom.cdx.json is missing"


def test_vulnerability_disposition_exists() -> None:
    assert VULNERABILITY_DISPOSITION.is_file(), "sbom/vulnerability-disposition.json is missing"


def test_hash_manifest_exists() -> None:
    assert HASH_MANIFEST.is_file(), "sbom/hash-manifest.json is missing"


def test_requirements_lock_exists() -> None:
    assert REQUIREMENTS_LOCK.is_file(), "sbom/requirements.lock is missing"


def test_adr_005_exists() -> None:
    assert ADR_005.is_file(), "ADR-005 installer packaging decision record is missing"


def test_install_scripts_exist() -> None:
    for script in ("Install-Verbatim.ps1", "Repair-Verbatim.ps1", "Update-Verbatim.ps1", "Uninstall-Verbatim.ps1"):
        assert (INSTALL_SCRIPTS / script).is_file(), f"scripts/install/{script} is missing"


# ---------------------------------------------------------------------------
# Transitive SBOM structural validity
# ---------------------------------------------------------------------------


def test_transitive_sbom_is_valid_json() -> None:
    sbom = json.loads(SBOM_TRANSITIVE.read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.4"


def test_transitive_sbom_covers_direct_deps() -> None:
    """Every package pinned in requirements.txt must appear in the transitive SBOM."""
    sbom = json.loads(SBOM_TRANSITIVE.read_text(encoding="utf-8"))
    sbom_names = {c["name"].lower() for c in sbom["components"]}
    for raw_line in REQUIREMENTS_TXT.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split("==")[0].lower()
        assert name in sbom_names, f"Direct dep {name} missing from transitive SBOM"


def test_transitive_sbom_has_purl_for_every_component() -> None:
    sbom = json.loads(SBOM_TRANSITIVE.read_text(encoding="utf-8"))
    for component in sbom["components"]:
        assert "purl" in component and component["purl"].startswith("pkg:pypi/"), (
            f"Component {component.get('name')} is missing a valid pypi purl"
        )


def test_transitive_sbom_has_candidate_revision() -> None:
    sbom = json.loads(SBOM_TRANSITIVE.read_text(encoding="utf-8"))
    props = {p["name"]: p["value"] for p in sbom.get("metadata", {}).get("properties", [])}
    revision = props.get("verbatim:candidate_revision", "")
    assert re.fullmatch(r"[0-9a-f]{7,40}", revision), (
        f"transitive SBOM candidate_revision is missing or not a git SHA: {revision!r}"
    )


# ---------------------------------------------------------------------------
# Vulnerability disposition structural validity
# ---------------------------------------------------------------------------


def test_vulnerability_disposition_is_valid_json() -> None:
    disp = json.loads(VULNERABILITY_DISPOSITION.read_text(encoding="utf-8"))
    assert "schema_version" in disp
    assert "dispositions" in disp


def test_vulnerability_disposition_covers_section1_packages() -> None:
    """All section-1 packages must have an explicit disposition."""
    disp = json.loads(VULNERABILITY_DISPOSITION.read_text(encoding="utf-8"))
    section1 = {d["name"].lower(): d["disposition"] for d in disp["dispositions"] if d.get("section") == 1}
    expected = {"annotated-types", "anyio", "fastapi", "h11", "pydantic", "pydantic-core",
                "python-multipart", "starlette", "uvicorn"}
    for name in expected:
        assert name in section1, f"Section-1 package {name} missing from disposition"
        assert section1[name] in ("clean", "accepted", "mitigated"), (
            f"Section-1 package {name} has unexpected disposition: {section1[name]!r}"
        )


def test_vulnerability_disposition_section2_marked_requires_endpoint() -> None:
    """Section-2 packages must be marked requires_qualified_endpoint, not clean."""
    disp = json.loads(VULNERABILITY_DISPOSITION.read_text(encoding="utf-8"))
    section2 = [d for d in disp["dispositions"] if d.get("section") == 2]
    assert section2, "No section-2 packages found in disposition"
    for entry in section2:
        assert entry["disposition"] == "requires_qualified_endpoint", (
            f"Section-2 package {entry['name']} must be marked requires_qualified_endpoint "
            f"until endpoint qualification is complete; got {entry['disposition']!r}"
        )


def test_vulnerability_disposition_no_open_advisories_in_section1() -> None:
    """No section-1 package may have unresolved advisories."""
    disp = json.loads(VULNERABILITY_DISPOSITION.read_text(encoding="utf-8"))
    for entry in disp["dispositions"]:
        if entry.get("section") == 1 and entry.get("advisories") is not None:
            assert entry["advisories"] == [], (
                f"Section-1 package {entry['name']} has unresolved advisories: {entry['advisories']}"
            )


# ---------------------------------------------------------------------------
# Hash manifest structural validity
# ---------------------------------------------------------------------------


def test_hash_manifest_is_valid_json() -> None:
    manifest = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"


def test_hash_manifest_has_candidate_revision() -> None:
    manifest = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    revision = manifest.get("candidate_revision", "")
    assert re.fullmatch(r"[0-9a-f]{7,40}", revision), (
        f"hash-manifest candidate_revision missing or not a git SHA: {revision!r}"
    )


def test_hash_manifest_external_tools_require_endpoint() -> None:
    """FFmpeg and model hashes must be null until endpoint-qualified — not guessed."""
    manifest = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    ffmpeg_hash = manifest.get("external_tools", {}).get("ffmpeg", {}).get("binary_sha256")
    model_hash = manifest.get("model_artifacts", {}).get("whisper_model", {}).get("file_sha256")
    # These MUST remain null until IT completes endpoint qualification.
    # A non-null value here means someone guessed or hardcoded a hash —
    # which is exactly the supply chain risk we are mitigating.
    assert ffmpeg_hash is None, (
        "FFmpeg binary_sha256 must remain null until IT verifies on the qualified endpoint. "
        "Do not populate this field from a development machine."
    )
    assert model_hash is None, (
        "Whisper model file_sha256 must remain null until IT verifies on the qualified endpoint. "
        "Do not populate this field from a development machine."
    )


def test_hash_manifest_python_version_recorded() -> None:
    manifest = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    version = manifest.get("python_runtime", {}).get("verified_version", "")
    assert re.match(r"3\.\d+\.\d+", version), (
        f"python_runtime.verified_version must be a version string, got: {version!r}"
    )


# ---------------------------------------------------------------------------
# Requirements lock file validity
# ---------------------------------------------------------------------------


def _lock_pins(lock_text: str) -> dict[str, str]:
    """Parse non-comment, non-empty lines from the lock file into name→version."""
    pins: dict[str, str] = {}
    for raw_line in lock_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        pins[name.strip().lower()] = version.strip()
    return pins


def test_requirements_lock_covers_direct_deps() -> None:
    """Every direct dep in requirements.txt must appear in the lock file."""
    lock = _lock_pins(REQUIREMENTS_LOCK.read_text(encoding="utf-8"))
    for raw_line in REQUIREMENTS_TXT.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        name = name.lower()
        assert name in lock, f"Direct dep {name} is missing from sbom/requirements.lock"
        assert lock[name] == version.strip(), (
            f"Version mismatch for {name}: requirements.txt={version.strip()}, lock={lock[name]}"
        )


def test_requirements_lock_has_no_unpinned_lines() -> None:
    """Every non-comment non-empty line in the lock file must use exact == pinning."""
    for raw_line in REQUIREMENTS_LOCK.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        assert "==" in line, (
            f"sbom/requirements.lock has an unpinned line: {line!r}. "
            "Every runtime package must use exact == pinning."
        )
        assert ">=" not in line and "<=" not in line and "~=" not in line, (
            f"sbom/requirements.lock must use only == pins, not range specifiers: {line!r}"
        )


# ---------------------------------------------------------------------------
# Install script guard-rail presence (negative control)
# ---------------------------------------------------------------------------


def test_install_scripts_contain_production_guard() -> None:
    """Each install script must contain the production-readiness guard."""
    sentinel = "VERBATIM_INSTALLER_PRODUCTION_READY"
    for script in ("Install-Verbatim.ps1", "Repair-Verbatim.ps1", "Update-Verbatim.ps1", "Uninstall-Verbatim.ps1"):
        text = (INSTALL_SCRIPTS / script).read_text(encoding="utf-8")
        assert sentinel in text, (
            f"scripts/install/{script} is missing the production-readiness guard ({sentinel}). "
            "Install scripts must refuse to run on production endpoints until IT qualification is complete."
        )


def test_install_script_does_not_disable_guard() -> None:
    """The Install script must not set the guard sentinel to the bypass value internally."""
    install_text = (INSTALL_SCRIPTS / "Install-Verbatim.ps1").read_text(encoding="utf-8")
    # If the script itself sets the sentinel to 'signed-and-qualified', it bypasses its own guard.
    assert "signed-and-qualified" not in install_text.split("VERBATIM_INSTALLER_PRODUCTION_READY", 1)[0], (
        "Install-Verbatim.ps1 must not self-assign the bypass value before the guard check."
    )


def test_install_script_requires_administrator() -> None:
    install_text = (INSTALL_SCRIPTS / "Install-Verbatim.ps1").read_text(encoding="utf-8")
    assert "#Requires -RunAsAdministrator" in install_text, (
        "Install-Verbatim.ps1 must require administrator privilege."
    )


# ---------------------------------------------------------------------------
# ADR-005 structural validity
# ---------------------------------------------------------------------------


def test_adr_005_contains_required_sections() -> None:
    text = ADR_005.read_text(encoding="utf-8")
    for section in ("Status", "Context", "Options", "Recommendation", "Consequences"):
        assert section in text, f"ADR-005 is missing required section: {section}"


def test_adr_005_references_hash_manifest() -> None:
    text = ADR_005.read_text(encoding="utf-8")
    assert "hash-manifest.json" in text, "ADR-005 must reference sbom/hash-manifest.json"
