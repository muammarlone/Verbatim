"""STS-112: Codespaces devcontainer policy, fake-secret fixtures, and private-port checks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVCONTAINER_JSON = ROOT / ".devcontainer" / "devcontainer.json"
STOP_GATE = ROOT / ".devcontainer" / "STOP_GATE.md"
POST_CREATE = ROOT / ".devcontainer" / "postCreate.sh"


def _config() -> dict:
    return json.loads(DEVCONTAINER_JSON.read_text(encoding="utf-8"))


def test_devcontainer_json_exists():
    assert DEVCONTAINER_JSON.is_file(), "devcontainer.json must exist"


def test_stop_gate_document_exists():
    assert STOP_GATE.is_file(), "STOP_GATE.md must exist"


def test_post_create_exists():
    assert POST_CREATE.is_file(), "postCreate.sh must exist"


def test_devcontainer_port_is_private():
    config = _config()
    attrs = config.get("portsAttributes", {})
    assert "8000" in attrs, "port 8000 must be configured"
    assert attrs["8000"].get("visibility") == "private", "port 8000 must be private (not public)"


def test_devcontainer_manifest_intake_disabled():
    config = _config()
    env = config.get("remoteEnv", {})
    assert env.get("STS_MANIFEST_INTAKE_ENABLED") == "false"


def test_devcontainer_protected_archive_disabled():
    config = _config()
    env = config.get("remoteEnv", {})
    assert env.get("STS_PROTECTED_ARCHIVE_ENABLED") == "false"


def test_devcontainer_zoom_connector_disabled():
    config = _config()
    env = config.get("remoteEnv", {})
    assert env.get("STS_ZOOM_CONNECTOR_ENABLED") == "false"


def test_devcontainer_data_dir_is_local():
    config = _config()
    env = config.get("remoteEnv", {})
    data_dir = env.get("STS_DATA_DIR", "")
    assert "/workspaces/" in data_dir, "STS_DATA_DIR must be local to the codespace"
    assert "onedrive" not in data_dir.lower(), "STS_DATA_DIR must not reference OneDrive"
    assert "corporate" not in data_dir.lower()


def test_devcontainer_codespaces_env_flag():
    config = _config()
    env = config.get("remoteEnv", {})
    assert env.get("VERBATIM_CODESPACES_ENV") == "true", "VERBATIM_CODESPACES_ENV must be set"


def test_devcontainer_no_production_mounts():
    config = _config()
    mounts = config.get("mounts", [])
    for mount in mounts:
        path = str(mount).lower()
        assert "onedrive" not in path
        assert "corporate" not in path
        assert "production" not in path
        assert "credential" not in path


def test_stop_gate_prohibits_connector_flags():
    text = STOP_GATE.read_text(encoding="utf-8").lower()
    assert "sts_manifest_intake_enabled" in text
    assert "sts_protected_archive_enabled" in text
    assert "sts_zoom_connector_enabled" in text


def test_stop_gate_prohibits_production_data():
    text = STOP_GATE.read_text(encoding="utf-8").lower()
    assert "corporate recordings" in text or "production data" in text
    assert "codespaces" in text or "devcontainer" in text


def test_post_create_has_stop_gate_check():
    text = POST_CREATE.read_text(encoding="utf-8")
    assert "VERBATIM_CODESPACES_ENV" in text, "postCreate must verify the environment flag"


def test_post_create_has_corporate_recording_guard():
    text = POST_CREATE.read_text(encoding="utf-8")
    assert "onedrive" in text.lower() or "STOP_GATE" in text


def test_fake_secret_fixtures_no_real_credentials():
    """Non-Python fixture files must not contain real credentials or tokens."""
    tests_dir = ROOT / "tests"
    fixture_extensions = {".csv", ".xlsx", ".json", ".env", ".txt", ".yaml", ".yml"}
    for path in tests_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in fixture_extensions:
            continue
        text_lower = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "zoom_client_secret" not in text_lower, (
            f"{path.relative_to(ROOT)}: Zoom client secret must not appear in fixtures"
        )
        assert "graph_access_token" not in text_lower, (
            f"{path.relative_to(ROOT)}: Graph access token must not appear in fixtures"
        )
