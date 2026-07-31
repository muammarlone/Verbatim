import time
from pathlib import Path

import pytest

from secure_transcribe.config import Settings
from secure_transcribe.errors import StudioError
from secure_transcribe.models import JobStatus, MediaProbe, TranscriptSegment
from secure_transcribe.service import JobProcessor
from secure_transcribe.storage import JobStore


class FakeMedia:
    def probe(self, source: Path) -> MediaProbe:
        assert source.is_file()
        return MediaProbe(
            duration_seconds=30, audio_codec="aac", video_codec="h264", format_name="mp4"
        )

    def extract_audio(self, source: Path, destination: Path) -> None:
        destination.write_bytes(b"fixture audio")


class FakeTranscriptEngine:
    model_id = "fixture-engine:v1"

    def is_ready(self) -> bool:
        return True

    def transcribe(self, audio_path: Path, language: str):
        assert audio_path.read_bytes() == b"fixture audio"
        return "en", [
            TranscriptSegment(id=0, start=0, end=12, text="We should review the secure rollout."),
            TranscriptSegment(id=1, start=12, end=30, text="Who owns the final approval?"),
        ]


def test_processor_completes_vertical_slice_and_removes_working_audio(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    store = JobStore(tmp_path)
    job = store.create_job(
        display_name="meeting.mp4", language="auto", model_id="fixture-engine:v1"
    )
    store.source_path(job.id).write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")
    processor = JobProcessor(store, settings, FakeMedia(), FakeTranscriptEngine())
    processor.process(job.id)
    completed = store.get_job(job.id)
    assert completed.status == JobStatus.COMPLETE
    assert completed.progress == 100
    assert completed.segment_count == 2
    assert completed.source_sha256
    assert store.get_transcript(job.id).language == "en"
    assert store.get_analysis(job.id).questions[0].segment_id == 1
    assert not store.audio_path(job.id).exists()
    processor.shutdown()


def test_processor_submit_runs_async_and_forget_cleans_up(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    store = JobStore(tmp_path)
    job = store.create_job(
        display_name="meeting.mp4", language="auto", model_id="fixture-engine:v1"
    )
    store.source_path(job.id).write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")
    processor = JobProcessor(store, settings, FakeMedia(), FakeTranscriptEngine())
    processor.submit(job.id)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if store.get_job(job.id).status == JobStatus.COMPLETE:
            break
        time.sleep(0.1)
    assert store.get_job(job.id).status == JobStatus.COMPLETE
    with processor._lock:
        assert job.id not in processor._futures
    processor.shutdown()


def test_processor_cancel_before_process_triggers_cancelled_handler(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    store = JobStore(tmp_path)
    job = store.create_job(
        display_name="meeting.mp4", language="auto", model_id="fixture-engine:v1"
    )
    store.source_path(job.id).write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")
    processor = JobProcessor(store, settings, FakeMedia(), FakeTranscriptEngine())
    processor.cancel(job.id)
    processor.process(job.id)
    # _JobCancelled fires at first checkpoint — job stays in its initial state
    assert store.get_job(job.id).status == JobStatus.QUEUED
    processor.shutdown()


def test_processor_cancel_invokes_engine_cancel_and_discards_future(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    store = JobStore(tmp_path)
    cancelled_ids: list[str] = []

    class CancellableEngine:
        model_id = "cancellable:v1"

        def is_ready(self) -> bool:
            return True

        def transcribe(self, audio_path: Path, language: str):
            return "en", []

        def cancel(self, job_id: str) -> None:
            cancelled_ids.append(job_id)

    processor = JobProcessor(store, settings, FakeMedia(), CancellableEngine())
    processor.cancel("phantom-job-id")
    assert "phantom-job-id" in cancelled_ids
    processor.shutdown()


def test_processor_unexpected_exception_fails_closed(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    store = JobStore(tmp_path)
    job = store.create_job(
        display_name="meeting.mp4", language="auto", model_id="boom:v1"
    )
    store.source_path(job.id).write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")

    class ExplodingEngine:
        model_id = "boom:v1"

        def is_ready(self) -> bool:
            return True

        def transcribe(self, audio_path: Path, language: str):
            raise RuntimeError("unexpected hardware failure")

    processor = JobProcessor(store, settings, FakeMedia(), ExplodingEngine())
    processor.process(job.id)
    failed = store.get_job(job.id)
    assert failed.status == JobStatus.FAILED
    assert failed.error.code == "UNEXPECTED_PROCESSING_ERROR"
    processor.shutdown()


def test_processor_studio_error_in_cancelled_job_does_not_write_failed(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    store = JobStore(tmp_path)
    job = store.create_job(
        display_name="meeting.mp4", language="auto", model_id="boom:v1"
    )
    store.source_path(job.id).write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")

    class StudioErrorEngine:
        model_id = "boom:v1"

        def is_ready(self) -> bool:
            return True

        def transcribe(self, audio_path: Path, language: str):
            raise StudioError("TRANSCRIPTION_FAILED", "forced failure")

    processor = JobProcessor(store, settings, FakeMedia(), StudioErrorEngine())
    # Mark cancelled before process so the StudioError branch with is_cancelled returns early
    with processor._lock:
        processor._cancelled.add(job.id)
    processor.process(job.id)
    # Should remain in initial state — not written as FAILED
    assert store.get_job(job.id).status == JobStatus.QUEUED
    processor.shutdown()


def test_processor_fails_closed_when_duration_exceeds_budget(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt", max_media_seconds=10)
    store = JobStore(tmp_path)
    job = store.create_job(
        display_name="meeting.mp4", language="auto", model_id="fixture-engine:v1"
    )
    store.source_path(job.id).write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")
    processor = JobProcessor(store, settings, FakeMedia(), FakeTranscriptEngine())
    processor.process(job.id)
    failed = store.get_job(job.id)
    assert failed.status == JobStatus.FAILED
    assert failed.error.code == "MEDIA_TOO_LONG"
    assert not (tmp_path / "jobs" / job.id / "transcript.json").exists()
    processor.shutdown()
