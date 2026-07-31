"""Additional security header tests for QG-04 pre-pentest hardening.

Supplements tests/test_owasp_acceptance.py with explicit checks for
COOP, CORP, Permissions-Policy, Referrer-Policy, no-wildcard CSP,
and no server-version leak.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from secure_transcribe.app import create_app
from secure_transcribe.config import Settings


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        data_dir=tmp_path / "data",
        model_path=tmp_path / "model.pt",
    )
    app = create_app(settings=settings)
    return TestClient(app, raise_server_exceptions=False)


def _get_headers(client: TestClient) -> dict[str, str]:
    resp = client.get("/health")
    return dict(resp.headers)


def test_csp_no_wildcard_sources(client: TestClient) -> None:
    headers = _get_headers(client)
    csp = headers.get("content-security-policy", "")
    assert "*" not in csp, f"CSP must not contain wildcard sources: {csp}"


def test_csp_default_src_self(client: TestClient) -> None:
    headers = _get_headers(client)
    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp


def test_csp_object_src_none(client: TestClient) -> None:
    headers = _get_headers(client)
    csp = headers.get("content-security-policy", "")
    assert "object-src 'none'" in csp


def test_csp_frame_ancestors_none(client: TestClient) -> None:
    headers = _get_headers(client)
    csp = headers.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in csp


def test_csp_no_unsafe_inline_scripts(client: TestClient) -> None:
    headers = _get_headers(client)
    csp = headers.get("content-security-policy", "")
    # 'unsafe-inline' must not appear in script-src
    # Allow it in style-src only (inline styles)
    directives = {d.strip().split(" ")[0]: d.strip() for d in csp.split(";")}
    script_src = directives.get("script-src", "")
    assert "'unsafe-inline'" not in script_src, f"script-src must not contain 'unsafe-inline': {script_src}"


def test_cross_origin_opener_policy(client: TestClient) -> None:
    headers = _get_headers(client)
    coop = headers.get("cross-origin-opener-policy", "")
    assert coop == "same-origin", f"COOP must be same-origin, got: {coop}"


def test_cross_origin_resource_policy(client: TestClient) -> None:
    headers = _get_headers(client)
    corp = headers.get("cross-origin-resource-policy", "")
    assert corp == "same-origin", f"CORP must be same-origin, got: {corp}"


def test_permissions_policy_camera_blocked(client: TestClient) -> None:
    headers = _get_headers(client)
    policy = headers.get("permissions-policy", "")
    assert "camera=()" in policy


def test_permissions_policy_microphone_blocked(client: TestClient) -> None:
    headers = _get_headers(client)
    policy = headers.get("permissions-policy", "")
    assert "microphone=()" in policy


def test_referrer_policy_no_referrer(client: TestClient) -> None:
    headers = _get_headers(client)
    rp = headers.get("referrer-policy", "")
    assert rp == "no-referrer", f"Referrer-Policy must be no-referrer, got: {rp}"


def test_no_server_header_leaked(client: TestClient) -> None:
    headers = _get_headers(client)
    server = headers.get("server", "")
    assert not server or "uvicorn" not in server.lower(), \
        f"Server header must not reveal version info: {server}"
