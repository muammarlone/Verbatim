"""QG-04: OWASP application-security acceptance tests.

Covers the application-security half of the manual accessibility and
application-security acceptance gate. Static header checks in test_api.py
confirm the eight required response headers are present; this file
verifies the OWASP-scope detail that the gate exit criteria require:

- CSP directive completeness (frame-ancestors, base-uri, object-src, form-action,
  no unsafe-inline scripts)
- Cache-Control: no-store on all /api/ endpoints
- JSON-only error responses (no HTML reflection of user input)
- Content-Disposition: attachment on exports (XSS download protection)
- No server-version disclosure
- CSRF token required on every state-changing endpoint
- Feature-disabled gate for disabled connector paths
- Connector flags off by default
- No filesystem paths or sensitive config in session response

These tests do not replace manual penetration testing (QG-03) or
manual screen-reader UAT (QG-04 manual component).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from secure_transcribe.app import create_app
from secure_transcribe.config import Settings


# ─── Fixture helpers ─────────────────────────────────────────────────────────

MP4_MAGIC = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom"


class _ReadyMedia:
    @staticmethod
    def is_ffmpeg_ready() -> bool:
        return True

    @staticmethod
    def is_ffprobe_ready() -> bool:
        return True

    def probe(self, source):
        raise AssertionError("unexpected probe")

    def extract_audio(self, source, destination):
        raise AssertionError("unexpected extraction")


class _ReadyTranscriber:
    model_id = "fixture-model:v1"

    @staticmethod
    def is_ready() -> bool:
        return True

    def transcribe(self, audio_path, language):
        raise AssertionError("unexpected transcription")


class _DeferredProcessor:
    def submit(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        return None


def _make_client(tmp_path: Path, **settings_overrides) -> TestClient:
    tmp_path.mkdir(parents=True, exist_ok=True)
    model = tmp_path / "base.pt"
    model.write_bytes(b"fixture")
    settings = Settings(
        data_dir=tmp_path / "data",
        model_path=model,
        max_upload_bytes=1024,
        **settings_overrides,
    )
    app = create_app(
        settings,
        media=_ReadyMedia(),
        transcriber=_ReadyTranscriber(),
        processor_factory=lambda *_: _DeferredProcessor(),
    )
    return TestClient(app)


# ─── CSP directive completeness ───────────────────────────────────────────────

def test_csp_includes_frame_ancestors_none(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        csp = client.get("/").headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp


def test_csp_includes_base_uri_none(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        csp = client.get("/").headers["content-security-policy"]
    assert "base-uri 'none'" in csp


def test_csp_restricts_object_src_to_none(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        csp = client.get("/").headers["content-security-policy"]
    assert "object-src 'none'" in csp


def test_csp_restricts_form_action_to_self(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        csp = client.get("/").headers["content-security-policy"]
    assert "form-action 'self'" in csp


def test_csp_does_not_allow_unsafe_inline_scripts(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        csp = client.get("/").headers["content-security-policy"]
    directives = {d.strip() for d in csp.split(";")}
    script_src = next((d for d in directives if d.startswith("script-src")), "")
    assert "'unsafe-inline'" not in script_src


def test_csp_allows_self_for_scripts(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        csp = client.get("/").headers["content-security-policy"]
    directives = {d.strip() for d in csp.split(";")}
    script_src = next((d for d in directives if d.startswith("script-src")), "")
    assert "'self'" in script_src


# ─── Cache-Control: no-store on API endpoints ─────────────────────────────────

@pytest.mark.parametrize("path", ["/api/session", "/api/jobs", "/api/batches"])
def test_api_endpoints_set_cache_control_no_store(tmp_path: Path, path: str) -> None:
    with _make_client(tmp_path) as client:
        cache = client.get(path).headers.get("cache-control", "")
    assert "no-store" in cache


def test_static_assets_do_not_force_no_store(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        static_response = client.get("/")
    # Static root must NOT carry no-store (it's cacheable); only /api/ is restricted
    assert "no-store" not in static_response.headers.get("cache-control", "")


# ─── Error responses: JSON only, no HTML reflection ───────────────────────────

def test_api_errors_return_json_content_type(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.post(
            "/api/jobs",
            # No X-Studio-Token → 403
            files={"file": ("test.mp4", MP4_MAGIC, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        )
    assert response.status_code == 403
    assert "application/json" in response.headers["content-type"]


def test_error_body_has_stable_code_and_message_envelope(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.post(
            "/api/jobs",
            files={"file": ("test.mp4", MP4_MAGIC, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        )
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "traceback" not in body
    assert "stack" not in body


def test_error_body_does_not_contain_internal_path(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        response = client.post(
            "/api/jobs",
            headers={"X-Studio-Token": token},
            files={"file": ("notes.txt", b"not an mp4", "text/plain")},
            data={"language": "auto", "consent_confirmed": "true"},
        )
    body = response.text
    assert str(tmp_path).replace("\\", "/") not in body
    assert "site-packages" not in body


# ─── Security headers on error responses ─────────────────────────────────────

@pytest.mark.parametrize("expected_code", [403, 404])
def test_security_headers_present_on_error_responses(
    tmp_path: Path, expected_code: int
) -> None:
    with _make_client(tmp_path) as client:
        if expected_code == 403:
            response = client.post(
                "/api/jobs",
                files={"file": ("f.mp4", MP4_MAGIC, "video/mp4")},
                data={"language": "auto", "consent_confirmed": "true"},
            )
        else:
            response = client.get("/api/jobs/nonexistent-id")
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert "content-security-policy" in response.headers


# ─── Server version disclosure ────────────────────────────────────────────────

def test_no_server_version_in_response_headers(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.get("/api/session")
    server = response.headers.get("server", "").lower()
    # Must not expose uvicorn version, Python version, or framework identity
    assert "uvicorn" not in server
    assert "python" not in server
    assert "fastapi" not in server


def test_no_x_powered_by_header(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.get("/")
    assert "x-powered-by" not in response.headers


# ─── Export content-disposition (download protection) ────────────────────────

def test_export_uses_content_disposition_attachment(tmp_path: Path) -> None:
    """Exports must use attachment disposition to prevent XSS via downloaded HTML."""
    from secure_transcribe.models import JobStatus, TranscriptDocument, TranscriptSegment, utc_now
    from secure_transcribe.analysis import analyze_transcript

    class _InstantProcessor:
        def __init__(self, store, *_):
            self.store = store

        def submit(self, job_id: str) -> None:
            segments = [TranscriptSegment(id=0, start=0, end=5, text="Test content.")]
            transcript = TranscriptDocument(
                job_id=job_id,
                language="en",
                duration_seconds=5,
                model_id="fixture-model:v1",
                created_at=utc_now(),
                segments=segments,
                text="Test content.",
            )
            self.store.write_transcript(transcript)
            self.store.write_analysis(analyze_transcript(transcript))
            self.store.update_job(
                job_id,
                status=JobStatus.COMPLETE,
                progress=100,
                duration_seconds=5,
                detected_language="en",
                segment_count=1,
            )

        def shutdown(self) -> None:
            return None

    model = tmp_path / "base.pt"
    model.write_bytes(b"fixture")
    settings = Settings(
        data_dir=tmp_path / "data",
        model_path=model,
        max_upload_bytes=1024,
    )
    app = create_app(
        settings,
        media=_ReadyMedia(),
        transcriber=_ReadyTranscriber(),
        processor_factory=lambda store, *args: _InstantProcessor(store),
    )
    with TestClient(app) as client:
        token = client.get("/api/session").json()["request_token"]
        job = client.post(
            "/api/jobs",
            headers={"X-Studio-Token": token},
            files={"file": ("meeting.mp4", MP4_MAGIC, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        ).json()["job"]
        for fmt in ("txt", "srt", "vtt", "md"):
            export = client.get(f"/api/jobs/{job['id']}/export?format={fmt}")
            assert export.status_code == 200
            cd = export.headers.get("content-disposition", "")
            assert "attachment" in cd, f"format {fmt}: expected attachment, got: {cd}"


# ─── CSRF enforcement on all mutation endpoints ───────────────────────────────

def test_delete_job_requires_csrf_token(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.delete("/api/jobs/any-job-id")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REQUEST_TOKEN_INVALID"


def test_delete_batch_requires_csrf_token(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.delete("/api/batches/any-batch-id")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REQUEST_TOKEN_INVALID"


def test_post_batch_requires_csrf_token(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        response = client.post(
            "/api/batches",
            json={
                "input_folder": "incoming",
                "output_folder": "out",
                "formats": ["txt"],
                "language": "auto",
                "consent_confirmed": True,
            },
        )
    assert response.status_code == 403


# ─── Connector flags off by default ──────────────────────────────────────────

def test_all_connector_flags_off_by_default(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        session = client.get("/api/session").json()
    assert session["manifest_intake_enabled"] is False
    assert session["protected_archive_enabled"] is False
    assert session["zoom_connector_enabled"] is False


def test_manifest_intake_feature_disabled_returns_stable_error(tmp_path: Path) -> None:
    payload = (
        "schema_version,row_id,source_type,source_locator,secret_ref,display_name,"
        "expected_sha256\n1.0,r1,local_archive,folder/file.zip/entry.mp4,"
        "prompt://label,Test,\n"
    ).encode("utf-8")
    with _make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        response = client.post(
            "/api/import-plans/preview",
            headers={"X-Studio-Token": token},
            files={"file": ("recordings.csv", payload, "text/csv")},
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEATURE_DISABLED"


# ─── Session response: no sensitive config ────────────────────────────────────

def test_session_response_does_not_expose_model_path(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        session_text = client.get("/api/session").text
    assert "base.pt" not in session_text
    assert str(tmp_path).replace("\\", "/") not in session_text


def test_network_required_is_false_in_session(tmp_path: Path) -> None:
    with _make_client(tmp_path) as client:
        session = client.get("/api/session").json()
    assert session.get("network_required") is False
