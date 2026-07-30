from __future__ import annotations

import asyncio
import json
import hashlib
import time
from pathlib import Path

from fastapi.testclient import TestClient

from secure_transcribe.analysis import analyze_transcript
from secure_transcribe.app import RequestBodyLimitMiddleware, create_app
from secure_transcribe.config import Settings
from secure_transcribe.models import JobStatus, TranscriptDocument, TranscriptSegment, utc_now


class ReadyMedia:
    @staticmethod
    def is_ffmpeg_ready() -> bool:
        return True

    @staticmethod
    def is_ffprobe_ready() -> bool:
        return True

    def probe(self, source):  # not used by the synchronous fixture processor
        raise AssertionError("unexpected probe")

    def extract_audio(self, source, destination):
        raise AssertionError("unexpected extraction")


class ReadyTranscriber:
    model_id = "fixture-model:v1"

    @staticmethod
    def is_ready() -> bool:
        return True

    def transcribe(self, audio_path, language):
        raise AssertionError("unexpected transcription")


class FixtureProcessor:
    def __init__(self, store, *_):
        self.store = store

    def submit(self, job_id: str) -> None:
        self.store.get_job(job_id)
        segments = [
            TranscriptSegment(id=0, start=0, end=5, text="We will document the local review."),
            TranscriptSegment(id=1, start=5, end=10, text="What should happen next?"),
        ]
        transcript = TranscriptDocument(
            job_id=job_id,
            language="en",
            duration_seconds=10,
            model_id="fixture-model:v1",
            created_at=utc_now(),
            segments=segments,
            text=" ".join(item.text for item in segments),
        )
        self.store.write_transcript(transcript)
        self.store.write_analysis(analyze_transcript(transcript))
        self.store.update_job(
            job_id,
            status=JobStatus.COMPLETE,
            progress=100,
            duration_seconds=10,
            detected_language="en",
            segment_count=2,
        )

    def shutdown(self) -> None:
        return None


class DeferredProcessor:
    def submit(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        return None


def make_client(tmp_path: Path, processor_factory=None, **settings_overrides) -> TestClient:
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
        media=ReadyMedia(),
        transcriber=ReadyTranscriber(),
        processor_factory=processor_factory or (lambda store, *args: FixtureProcessor(store)),
    )
    return TestClient(app)


def test_local_api_vertical_slice_and_delete_propagation(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        session = client.get("/api/session").json()
        token = session["request_token"]
        mp4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom"
        response = client.post(
            "/api/jobs",
            headers={"X-Studio-Token": token},
            files={"file": ("board-review.mp4", mp4, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        )
        assert response.status_code == 202
        job = response.json()["job"]
        assert job["status"] == "complete"
        transcript = client.get(f"/api/jobs/{job['id']}/transcript").json()["transcript"]
        assert transcript["text"].startswith("We will document")
        exported = client.get(f"/api/jobs/{job['id']}/export?format=srt")
        assert "00:00:00,000" in exported.text
        assert "attachment" in exported.headers["content-disposition"]
        deleted = client.delete(f"/api/jobs/{job['id']}", headers={"X-Studio-Token": token})
        assert deleted.status_code == 204
        assert client.get(f"/api/jobs/{job['id']}").status_code == 404


def test_mutations_require_request_token_and_consent(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        mp4 = b"\x00\x00\x00\x18ftypisom"
        no_token = client.post(
            "/api/jobs",
            files={"file": ("meeting.mp4", mp4, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        )
        assert no_token.status_code == 403
        token = client.get("/api/session").json()["request_token"]
        no_consent = client.post(
            "/api/jobs",
            headers={"X-Studio-Token": token},
            files={"file": ("meeting.mp4", mp4, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "false"},
        )
        assert no_consent.status_code == 400
        assert no_consent.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_request_size_and_validation_errors_use_stable_envelope(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        oversized = client.post(
            "/api/jobs",
            headers={
                "X-Studio-Token": token,
                "Content-Type": "application/octet-stream",
            },
            content=b"x" * (1024 + 64 * 1024 + 1),
        )
        assert oversized.status_code == 413
        assert oversized.json()["error"]["code"] == "REQUEST_TOO_LARGE"

        invalid = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={"input_folder": "incoming", "consent_confirmed": True},
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


def manifest_csv(secret_ref: str = "prompt://api-canary-label") -> bytes:
    return (
        "schema_version,row_id,source_type,source_locator,secret_ref,display_name,"
        "expected_sha256\n"
        f"1.0,row-1,local_archive,incoming/review.zip,{secret_ref},Quarterly review,\n"
    ).encode("utf-8")


def test_manifest_preview_is_disabled_by_default_and_requires_token(tmp_path: Path) -> None:
    payload = manifest_csv()
    with make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        disabled = client.post(
            "/api/import-plans/preview",
            headers={"X-Studio-Token": token},
            files={"file": ("recordings.csv", payload, "text/csv")},
        )
        assert disabled.status_code == 404
        assert disabled.json()["error"]["code"] == "FEATURE_DISABLED"

    with make_client(tmp_path / "enabled", manifest_intake_enabled=True) as client:
        missing_token = client.post(
            "/api/import-plans/preview",
            files={"file": ("recordings.csv", payload, "text/csv")},
        )
        assert missing_token.status_code == 403
        assert missing_token.json()["error"]["code"] == "REQUEST_TOKEN_INVALID"


def test_manifest_preview_is_sanitized_memory_only_and_audited(tmp_path: Path) -> None:
    secret_ref = "prompt://do-not-return-this-label"
    payload = manifest_csv(secret_ref)
    with make_client(tmp_path, manifest_intake_enabled=True) as client:
        session = client.get("/api/session").json()
        token = session["request_token"]
        assert session["manifest_intake_enabled"] is True
        assert session["protected_archive_enabled"] is False
        assert session["zoom_connector_enabled"] is False
        assert session["network_required"] is False
        response = client.post(
            "/api/import-plans/preview",
            headers={"X-Studio-Token": token},
            files={"file": ("recordings.csv", payload, "text/csv")},
        )
        assert response.status_code == 201
        plan = response.json()["plan"]
        assert plan["row_count"] == 1
        assert plan["manifest_sha256"] == hashlib.sha256(payload).hexdigest()
        assert plan["rows"][0]["secret_provider"] == "prompt"
        assert plan["rows"][0]["secret_required"] is True
        assert secret_ref not in response.text
        assert client.get("/api/jobs").json()["jobs"] == []
        stored = client.app.state.import_plan_store.get(plan["plan_id"])
        assert stored.rows[0].secret_ref == secret_ref
        plan_store = client.app.state.import_plan_store

    assert plan_store.active_count() == 0
    persisted = b"\n".join(
        path.read_bytes() for path in (tmp_path / "data").rglob("*") if path.is_file()
    )
    assert secret_ref.encode("utf-8") not in persisted
    audit = (tmp_path / "data" / "audit" / "events.jsonl").read_text(encoding="utf-8")
    assert "import_plan_previewed" in audit
    assert "manifest_sha256" in audit


def test_manifest_preview_request_and_parser_limits_use_stable_errors(tmp_path: Path) -> None:
    with make_client(
        tmp_path,
        manifest_intake_enabled=True,
        max_manifest_bytes=64 * 1024,
    ) as client:
        token = client.get("/api/session").json()["request_token"]
        parser_limit = client.post(
            "/api/import-plans/preview",
            headers={"X-Studio-Token": token},
            files={"file": ("recordings.csv", b"x" * (64 * 1024 + 1), "text/csv")},
        )
        assert parser_limit.status_code == 413
        assert parser_limit.json()["error"]["code"] == "MANIFEST_REQUEST_TOO_LARGE"

        request_limit = client.post(
            "/api/import-plans/preview",
            headers={"X-Studio-Token": token, "Content-Type": "application/octet-stream"},
            content=b"x" * (128 * 1024 + 1),
        )
        assert request_limit.status_code == 413
        assert request_limit.json()["error"]["code"] == "MANIFEST_REQUEST_TOO_LARGE"


def test_manifest_stream_without_content_length_is_bounded_before_parser() -> None:
    sent: list[dict] = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"a" * 40, "more_body": True},
            {"type": "http.request", "body": b"b" * 30, "more_body": False},
        ]
    )

    async def receive():
        return next(incoming)

    async def send(message):
        sent.append(message)

    async def downstream(scope, bounded_receive, downstream_send):
        await bounded_receive()
        await bounded_receive()
        await downstream_send({"type": "http.response.start", "status": 204, "headers": []})

    middleware = RequestBodyLimitMiddleware(
        downstream,
        upload_max_bytes=100,
        manifest_max_bytes=64,
    )
    asyncio.run(
        middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/import-plans/preview",
                "headers": [],
            },
            receive,
            send,
        )
    )

    assert sent[0]["status"] == 413
    body = json.loads(sent[1]["body"])
    assert body["error"]["code"] == "MANIFEST_REQUEST_TOO_LARGE"


def test_active_job_deletion_is_rejected_until_processing_finishes(tmp_path: Path) -> None:
    with make_client(tmp_path, processor_factory=lambda *_: DeferredProcessor()) as client:
        token = client.get("/api/session").json()["request_token"]
        created = client.post(
            "/api/jobs",
            headers={"X-Studio-Token": token},
            files={"file": ("meeting.mp4", b"\x00\x00\x00\x18ftypisom", "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        ).json()["job"]

        deleted = client.delete(f"/api/jobs/{created['id']}", headers={"X-Studio-Token": token})
        assert deleted.status_code == 409
        assert deleted.json()["error"]["code"] == "JOB_STILL_RUNNING"
        assert client.get(f"/api/jobs/{created['id']}").status_code == 200


def test_security_headers_and_host_validation(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "default-src 'self'" in response.headers["content-security-policy"]
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cross-origin-opener-policy"] == "same-origin"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert response.headers["x-permitted-cross-domain-policies"] == "none"
        assert response.headers["permissions-policy"] == (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-content-type-options"] == "nosniff"
        rejected = client.get("http://untrusted.example/api/health")
        assert rejected.status_code == 400


def wait_for_batch(client: TestClient, batch_id: str, timeout: float = 3.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/batches/{batch_id}")
        assert response.status_code == 200
        batch = response.json()["batch"]
        if batch["status"] in {"complete", "partial", "failed"}:
            return batch
        time.sleep(0.05)
    raise AssertionError("batch did not reach a terminal state")


def test_folder_batch_writes_selected_formats_manifest_and_cleans_managed_copies(
    tmp_path: Path,
) -> None:
    batch_root = tmp_path / "data" / "batch-workspace"
    incoming = batch_root / "incoming"
    incoming.mkdir(parents=True)
    mp4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom"
    (incoming / "board review.mp4").write_bytes(mp4)
    (incoming / "planning-review.mp4").write_bytes(mp4)

    with make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        response = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={
                "input_folder": "incoming",
                "output_folder": "transcripts",
                "formats": ["txt", "md", "json"],
                "language": "auto",
                "consent_confirmed": True,
            },
        )
        assert response.status_code == 202
        batch = wait_for_batch(client, response.json()["batch"]["id"])
        assert batch["status"] == "complete"
        assert batch["completed_files"] == 2
        assert batch["failed_files"] == 0
        assert all(len(item["outputs"]) == 3 for item in batch["items"])

        output = batch_root / "transcripts"
        assert (
            (output / "board_review.txt").read_text(encoding="utf-8").startswith("We will document")
        )
        assert "# Transcript" in (output / "planning-review.md").read_text(encoding="utf-8")
        evidence = json.loads((output / "board_review.json").read_text(encoding="utf-8"))
        assert evidence["transcript"]["model_id"] == "fixture-model:v1"
        manifest = json.loads((output / batch["manifest_name"]).read_text(encoding="utf-8"))
        assert manifest["completed_files"] == 2

        managed_delete = client.delete(
            f"/api/jobs/{batch['items'][0]['job_id']}",
            headers={"X-Studio-Token": token},
        )
        assert managed_delete.status_code == 409
        assert managed_delete.json()["error"]["code"] == "JOB_MANAGED_BY_BATCH"

        deleted = client.delete(f"/api/batches/{batch['id']}", headers={"X-Studio-Token": token})
        assert deleted.status_code == 204
        assert client.get("/api/batches").json()["batches"] == []
        assert client.get("/api/jobs").json()["jobs"] == []
        assert (incoming / "board review.mp4").is_file()
        assert (output / "board_review.txt").is_file()


def test_folder_batch_isolates_empty_file_failure(tmp_path: Path) -> None:
    incoming = tmp_path / "data" / "batch-workspace" / "incoming"
    incoming.mkdir(parents=True)
    (incoming / "empty.mp4").write_bytes(b"")
    (incoming / "valid.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")

    with make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        response = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={
                "input_folder": "incoming",
                "output_folder": "out",
                "formats": ["txt"],
                "language": "en",
                "consent_confirmed": True,
            },
        )
        batch = wait_for_batch(client, response.json()["batch"]["id"])
        assert batch["status"] == "partial"
        assert batch["completed_files"] == 1
        assert batch["failed_files"] == 1
        rejected = next(item for item in batch["items"] if item["source_name"] == "empty.mp4")
        assert rejected["status"] == "rejected"
        assert rejected["error"]["code"] == "EMPTY_UPLOAD"


def test_folder_batch_filesystem_failure_reaches_terminal_state(tmp_path: Path) -> None:
    incoming = tmp_path / "data" / "batch-workspace" / "incoming"
    incoming.mkdir(parents=True)
    (incoming / "valid.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")

    with make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]

        def fail_output(*_):
            raise OSError("simulated local write failure")

        client.app.state.batch_manager._write_output = fail_output
        response = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={
                "input_folder": "incoming",
                "output_folder": "out",
                "formats": ["txt"],
                "language": "auto",
                "consent_confirmed": True,
            },
        )
        batch = wait_for_batch(client, response.json()["batch"]["id"])

        assert batch["status"] == "failed"
        assert batch["error"]["code"] == "BATCH_MONITOR_FAILED"
        assert batch["items"][0]["status"] == "failed"
        assert batch["items"][0]["error"]["code"] == "BATCH_ITEM_IO_FAILED"


def test_folder_batch_empty_same_folder_file_limit_and_name_collision(tmp_path: Path) -> None:
    batch_root = tmp_path / "data" / "batch-workspace"
    incoming = batch_root / "incoming"
    incoming.mkdir(parents=True)

    with make_client(tmp_path, max_batch_files=1) as client:
        token = client.get("/api/session").json()["request_token"]
        request = {
            "input_folder": "incoming",
            "output_folder": "out",
            "formats": ["txt"],
            "language": "auto",
            "consent_confirmed": True,
        }
        empty = client.post("/api/batches", headers={"X-Studio-Token": token}, json=request)
        assert empty.status_code == 400
        assert empty.json()["error"]["code"] == "NO_MP4_FILES"

        (incoming / "first.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
        same = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={**request, "output_folder": "incoming"},
        )
        assert same.status_code == 400
        assert same.json()["error"]["code"] == "BATCH_FOLDERS_MUST_DIFFER"

        (incoming / "second.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
        too_many = client.post("/api/batches", headers={"X-Studio-Token": token}, json=request)
        assert too_many.status_code == 413
        assert too_many.json()["error"]["code"] == "BATCH_FILE_LIMIT_EXCEEDED"

    collision_root = tmp_path / "collision" / "data" / "batch-workspace"
    collision_input = collision_root / "incoming"
    collision_input.mkdir(parents=True)
    (collision_input / "review notes.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
    (collision_input / "review_notes.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
    with make_client(tmp_path / "collision", max_batch_files=5) as client:
        token = client.get("/api/session").json()["request_token"]
        collision = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json=request,
        )
        assert collision.status_code == 409
        assert collision.json()["error"]["code"] == "OUTPUT_NAME_COLLISION"


def test_folder_batch_blocks_traversal_missing_consent_and_overwrite(tmp_path: Path) -> None:
    batch_root = tmp_path / "data" / "batch-workspace"
    incoming = batch_root / "incoming"
    output = batch_root / "out"
    incoming.mkdir(parents=True)
    output.mkdir()
    (incoming / "meeting.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
    (output / "meeting.txt").write_text("do not replace", encoding="utf-8")

    with make_client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        base = {
            "input_folder": "incoming",
            "output_folder": "out",
            "formats": ["txt"],
            "language": "auto",
            "consent_confirmed": True,
        }
        traversal = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={**base, "input_folder": "../outside"},
        )
        assert traversal.status_code == 400
        assert traversal.json()["error"]["code"] == "INVALID_BATCH_FOLDER"

        no_consent = client.post(
            "/api/batches",
            headers={"X-Studio-Token": token},
            json={**base, "consent_confirmed": False},
        )
        assert no_consent.status_code == 400
        assert no_consent.json()["error"]["code"] == "CONSENT_REQUIRED"

        collision = client.post("/api/batches", headers={"X-Studio-Token": token}, json=base)
        assert collision.status_code == 409
        assert collision.json()["error"]["code"] == "OUTPUT_EXISTS"
        assert (output / "meeting.txt").read_text(encoding="utf-8") == "do not replace"
        assert client.get("/api/jobs").json()["jobs"] == []
