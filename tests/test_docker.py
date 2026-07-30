"""STS-111: Docker qualification image — static policy checks.

These tests verify the Dockerfile and compose configuration meet the
non-root, private-port, and no-baked-credentials requirements without
requiring Docker to be installed in the test environment.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "docker" / "Dockerfile.qualification"
COMPOSE = ROOT / "docker" / "docker-compose.qualification.yml"


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _compose_text() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def test_dockerfile_exists():
    assert DOCKERFILE.is_file()


def test_compose_exists():
    assert COMPOSE.is_file()


def test_dockerfile_uses_non_root_user():
    text = _dockerfile_text()
    assert "USER verbatim" in text or "USER 1001" in text, (
        "Dockerfile must switch to non-root user before ENTRYPOINT"
    )
    # Ensure USER comes after useradd
    user_idx = text.rfind("USER verbatim") or text.rfind("USER 1001")
    useradd_idx = text.find("useradd")
    assert useradd_idx < user_idx, "USER directive must come after useradd"


def test_dockerfile_creates_named_non_root_group():
    text = _dockerfile_text()
    assert "groupadd" in text and "verbatim" in text


def test_dockerfile_does_not_run_as_root_by_default():
    text = _dockerfile_text()
    lines_after_user = text[text.rfind("USER"):].strip().splitlines()
    assert not any("USER root" in line for line in lines_after_user[1:])


def test_dockerfile_no_baked_credentials():
    text = _dockerfile_text().lower()
    assert "password" not in text or "verbatim" not in text
    assert "secret" not in text
    assert "token" not in text
    assert "zoom_client_secret" not in text
    assert "graph_access_token" not in text


def test_dockerfile_connector_flags_false():
    text = _dockerfile_text()
    assert 'STS_MANIFEST_INTAKE_ENABLED=false' in text
    assert 'STS_PROTECTED_ARCHIVE_ENABLED=false' in text
    assert 'STS_ZOOM_CONNECTOR_ENABLED=false' in text


def test_dockerfile_model_not_baked_in():
    text = _dockerfile_text()
    # Model path must be externally injected, not COPY-ed
    assert ".pt" not in text or "STS_MODEL_PATH" in text, (
        "Whisper model must not be baked into the image; use STS_MODEL_PATH env var"
    )
    assert "COPY" not in text or "model" not in text.lower() or "STS_MODEL_PATH" in text


def test_dockerfile_data_dir_is_mount():
    text = _dockerfile_text()
    assert "STS_DATA_DIR=/data" in text
    # Data dir must be a volume mount, not built-in content
    assert "COPY data" not in text


def test_dockerfile_entrypoint_loopback_only():
    text = _dockerfile_text()
    assert "127.0.0.1" in text, "ENTRYPOINT must bind to 127.0.0.1"
    assert "0.0.0.0" not in text, "Must not bind to 0.0.0.0"


def test_compose_binds_loopback():
    text = _compose_text()
    assert "127.0.0.1:8000:8000" in text, "compose port must bind to loopback only"
    assert '"0.0.0.0:8000' not in text


def test_compose_no_new_privileges():
    text = _compose_text()
    assert "no-new-privileges:true" in text


def test_compose_drops_all_capabilities():
    text = _compose_text()
    assert "cap_drop" in text
    assert "ALL" in text


def test_compose_stop_gate_comment():
    text = _compose_text()
    assert "STOP GATE" in text or "stop gate" in text.lower(), (
        "compose file must have a stop-gate comment against production data"
    )


def test_compose_no_production_mounts_in_example():
    text = _compose_text().lower()
    assert "onedrive" not in text
    assert "corporate" not in text
    assert "production" not in text or "not" in text


def test_compose_user_is_non_root():
    text = _compose_text()
    assert 'user: "1001:1001"' in text or "user: '1001:1001'" in text


def test_compose_read_only_filesystem():
    text = _compose_text()
    assert "read_only: true" in text
