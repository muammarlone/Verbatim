from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from secure_transcribe.analysis import analyze_transcript
from secure_transcribe.app import create_app
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


def make_client(tmp_path: Path, processor_factory=None) -> TestClient:
    model = tmp_path / "base.pt"
    model.write_bytes(b"fixture")
    settings = Settings(data_dir=tmp_path / "data", model_path=model, max_upload_bytes=1024)
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
