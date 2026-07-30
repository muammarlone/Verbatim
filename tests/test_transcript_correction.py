"""STS-102: Transcript correction with version history."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from secure_transcribe.analysis import analyze_transcript
from secure_transcribe.app import create_app
from secure_transcribe.config import Settings
from secure_transcribe.models import JobStatus, TranscriptDocument, TranscriptSegment, utc_now


_MP4_MAGIC = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom"


class _ReadyMedia:
    @staticmethod
    def is_ffmpeg_ready() -> bool:
        return True

    @staticmethod
    def is_ffprobe_ready() -> bool:
        return True


class _ReadyTranscriber:
    model_id = "fixture-model:v1"

    @staticmethod
    def is_ready() -> bool:
        return True


class _CompleteProcessor:
    def __init__(self, store, *_):
        self.store = store

    def submit(self, job_id: str) -> None:
        segments = [
            TranscriptSegment(id=0, start=0.0, end=4.0, text="The budget is approved."),
            TranscriptSegment(id=1, start=4.0, end=8.0, text="Please review the action items."),
        ]
        doc = TranscriptDocument(
            job_id=job_id,
            language="en",
            duration_seconds=8.0,
            model_id="fixture-model:v1",
            created_at=utc_now(),
            segments=segments,
            text=" ".join(s.text for s in segments),
        )
        self.store.write_transcript(doc)
        self.store.write_analysis(analyze_transcript(doc))
        self.store.update_job(
            job_id, status=JobStatus.COMPLETE, progress=100,
            duration_seconds=8.0, detected_language="en", segment_count=2,
        )

    def shutdown(self) -> None:
        return None


class _QueuedProcessor:
    def __init__(self, store, *_):
        self.store = store

    def submit(self, job_id: str) -> None:
        pass

    def shutdown(self) -> None:
        return None


def _client(tmp_path: Path, processor_cls=_CompleteProcessor) -> TestClient:
    tmp_path.mkdir(parents=True, exist_ok=True)
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
        processor_factory=lambda store, *args: processor_cls(store),
    )
    return TestClient(app)


def _upload_job(client: TestClient, token: str) -> dict:
    resp = client.post(
        "/api/jobs",
        headers={"X-Studio-Token": token},
        files={"file": ("meeting.mp4", _MP4_MAGIC, "video/mp4")},
        data={"language": "auto", "consent_confirmed": "true"},
    )
    assert resp.status_code == 202
    return resp.json()["job"]


def test_correct_segment_returns_revision(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "The budget is approved by the committee."},
        )
        assert resp.status_code == 200
        rev = resp.json()["revision"]
        assert rev["segment_id"] == 0
        assert rev["corrected_text"] == "The budget is approved by the committee."
        assert rev["original_text"] == "The budget is approved."
        assert "revision_id" in rev
        assert "corrected_at" in rev


def test_correct_segment_updates_transcript(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "Updated text here."},
        )
        transcript = client.get(f"/api/jobs/{job['id']}/transcript").json()["transcript"]
        seg = next(s for s in transcript["segments"] if s["id"] == 0)
        assert seg["text"] == "Updated text here."


def test_correct_segment_updates_full_text(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/1",
            headers={"X-Studio-Token": token},
            json={"text": "Revised action items."},
        )
        transcript = client.get(f"/api/jobs/{job['id']}/transcript").json()["transcript"]
        assert "Revised action items." in transcript["text"]


def test_correction_recorded_in_revisions(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "Corrected segment text.", "reason": "Misheard word"},
        )
        resp = client.get(f"/api/jobs/{job['id']}/transcript/revisions")
        assert resp.status_code == 200
        revisions = resp.json()["revisions"]
        assert len(revisions) == 1
        assert revisions[0]["segment_id"] == 0
        assert revisions[0]["reason"] == "Misheard word"
        assert revisions[0]["original_text"] == "The budget is approved."


def test_correction_reason_optional(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "No reason provided."},
        )
        assert resp.status_code == 200
        assert resp.json()["revision"]["reason"] is None


def test_multiple_corrections_all_recorded(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "First correction."},
        )
        client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/1",
            headers={"X-Studio-Token": token},
            json={"text": "Second correction."},
        )
        revisions = client.get(f"/api/jobs/{job['id']}/transcript/revisions").json()["revisions"]
        assert len(revisions) == 2
        seg_ids = {r["segment_id"] for r in revisions}
        assert seg_ids == {0, 1}


def test_correction_requires_csrf_token(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            json={"text": "No token."},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "REQUEST_TOKEN_INVALID"


def test_correction_rejects_empty_text(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": ""},
        )
        assert resp.status_code == 422


def test_correction_rejects_oversized_text(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "x" * 20_001},
        )
        assert resp.status_code == 422


def test_correction_rejects_oversized_reason(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "Valid text.", "reason": "r" * 501},
        )
        assert resp.status_code == 422


def test_correction_rejects_nonexistent_segment(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/999",
            headers={"X-Studio-Token": token},
            json={"text": "No such segment."},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SEGMENT_NOT_FOUND"


def test_correction_rejects_non_complete_job(tmp_path: Path) -> None:
    with _client(tmp_path, processor_cls=_QueuedProcessor) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        assert job["status"] == "queued"
        resp = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "Too early."},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "JOB_NOT_COMPLETE"


def test_revisions_empty_before_any_correction(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        resp = client.get(f"/api/jobs/{job['id']}/transcript/revisions")
        assert resp.status_code == 200
        assert resp.json()["revisions"] == []


def test_correction_audit_event_recorded(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        token = client.get("/api/session").json()["request_token"]
        job = _upload_job(client, token)
        rev = client.patch(
            f"/api/jobs/{job['id']}/transcript/segments/0",
            headers={"X-Studio-Token": token},
            json={"text": "Audited correction."},
        ).json()["revision"]
        audit_path = (
            Path(client.app.state.settings.data_dir) / "audit" / "events.jsonl"
        )
        events = [line for line in audit_path.read_text().splitlines() if "segment_corrected" in line]
        assert len(events) == 1
        import json
        evt = json.loads(events[0])
        assert evt["details"]["revision_id"] == rev["revision_id"]
        assert evt["details"]["segment_id"] == 0
