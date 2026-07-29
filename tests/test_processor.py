from pathlib import Path

from secure_transcribe.config import Settings
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
