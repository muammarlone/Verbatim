from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from secure_transcribe.errors import StudioError
from secure_transcribe.transcription import FFmpegMediaPipeline, LocalWhisperEngine


def slow_worker(model_path: str, audio_path: str, language: str, output_path: str) -> None:
    del model_path, audio_path, language, output_path
    time.sleep(10)


def successful_worker(model_path: str, audio_path: str, language: str, output_path: str) -> None:
    del model_path, audio_path, language
    Path(output_path).write_text(
        json.dumps(
            {
                "ok": True,
                "language": "en",
                "segments": [{"id": 0, "start": 0, "end": 1, "text": "Approved text"}],
            }
        ),
        encoding="utf-8",
    )


def malformed_worker(model_path: str, audio_path: str, language: str, output_path: str) -> None:
    del model_path, audio_path, language
    Path(output_path).write_text("not json", encoding="utf-8")


def no_speech_worker(model_path: str, audio_path: str, language: str, output_path: str) -> None:
    del model_path, audio_path, language
    Path(output_path).write_text(
        json.dumps({"ok": False, "code": "NO_SPEECH_DETECTED"}), encoding="utf-8"
    )


def invalid_schema_worker(
    model_path: str, audio_path: str, language: str, output_path: str
) -> None:
    del model_path, audio_path, language
    Path(output_path).write_text(
        json.dumps({"ok": True, "language": "en", "segments": [{"text": "missing fields"}]}),
        encoding="utf-8",
    )


def test_model_id_fingerprints_exact_artifact(tmp_path: Path) -> None:
    model = tmp_path / "base.pt"
    model.write_bytes(b"approved model fixture")
    digest = hashlib.sha256(b"approved model fixture").hexdigest()
    engine = LocalWhisperEngine(model)
    assert engine.model_id == f"openai-whisper:base.pt@sha256:{digest}"


def test_transcription_budget_exhaustion_stops_safely(tmp_path: Path) -> None:
    model = tmp_path / "base.pt"
    audio = tmp_path / "audio.wav"
    model.write_bytes(b"approved model fixture")
    audio.write_bytes(b"audio fixture")
    engine = LocalWhisperEngine(model, timeout_seconds=1, worker_target=slow_worker)
    started = time.monotonic()
    with pytest.raises(StudioError) as exc:
        engine.transcribe(audio, "en")
    assert exc.value.code == "TRANSCRIPTION_TIMEOUT"
    assert time.monotonic() - started < 8
    assert not audio.with_suffix(".whisper-result.json").exists()


def test_active_transcription_can_be_cancelled(tmp_path: Path) -> None:
    model = tmp_path / "base.pt"
    job_dir = tmp_path / "00000000-0000-0000-0000-000000000001"
    job_dir.mkdir()
    audio = job_dir / "working.wav"
    model.write_bytes(b"approved model fixture")
    audio.write_bytes(b"audio fixture")
    engine = LocalWhisperEngine(model, timeout_seconds=20, worker_target=slow_worker)
    captured: list[StudioError] = []

    def run() -> None:
        try:
            engine.transcribe(audio, "en")
        except StudioError as exc:
            captured.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    time.sleep(1)
    engine.cancel(job_dir.name)
    thread.join(timeout=8)
    assert not thread.is_alive()
    assert captured[0].code == "TRANSCRIPTION_CANCELLED"
    assert not audio.with_suffix(".whisper-result.json").exists()


def test_ffprobe_success_and_fixed_argument_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "meeting.mp4"
    source.write_bytes(b"fixture")
    pipeline = FFmpegMediaPipeline(timeout_seconds=90)
    monkeypatch.setattr(pipeline, "is_ffprobe_ready", lambda: True)
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return SimpleNamespace(
            stdout=json.dumps(
                {
                    "streams": [
                        {"codec_type": "audio", "codec_name": "aac"},
                        {"codec_type": "video", "codec_name": "h264"},
                    ],
                    "format": {"duration": "12.5", "format_name": "mov,mp4"},
                }
            )
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = pipeline.probe(source)

    assert result.duration_seconds == 12.5
    assert result.audio_codec == "aac"
    assert result.video_codec == "h264"
    assert captured["command"][0] == "ffprobe"
    assert captured["command"][-1] == str(source)
    assert "shell" not in captured["kwargs"]


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"streams": [], "format": {"duration": "1"}}, "AUDIO_TRACK_MISSING"),
        (
            {
                "streams": [{"codec_type": "audio", "codec_name": "aac"}],
                "format": {"duration": "0", "format_name": "mp4"},
            },
            "INVALID_DURATION",
        ),
    ],
)
def test_ffprobe_rejects_invalid_media_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict, code: str
) -> None:
    pipeline = FFmpegMediaPipeline(timeout_seconds=90)
    monkeypatch.setattr(pipeline, "is_ffprobe_ready", lambda: True)
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(payload))
    )

    with pytest.raises(StudioError) as exc:
        pipeline.probe(tmp_path / "meeting.mp4")
    assert exc.value.code == code


def test_ffprobe_dependency_timeout_and_failure_are_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = FFmpegMediaPipeline(timeout_seconds=90)
    monkeypatch.setattr(pipeline, "is_ffprobe_ready", lambda: False)
    with pytest.raises(StudioError) as missing:
        pipeline.probe(tmp_path / "meeting.mp4")
    assert missing.value.code == "FFPROBE_NOT_FOUND"

    monkeypatch.setattr(pipeline, "is_ffprobe_ready", lambda: True)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="ffprobe", timeout=90)
        ),
    )
    with pytest.raises(StudioError) as timeout:
        pipeline.probe(tmp_path / "meeting.mp4")
    assert timeout.value.code == "FFPROBE_TIMEOUT"

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(returncode=1, cmd="ffprobe")
        ),
    )
    with pytest.raises(StudioError) as failed:
        pipeline.probe(tmp_path / "meeting.mp4")
    assert failed.value.code == "MEDIA_PROBE_FAILED"


def test_ffmpeg_extract_success_dependency_timeout_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = FFmpegMediaPipeline(timeout_seconds=90)
    source = tmp_path / "meeting.mp4"
    destination = tmp_path / "working.wav"
    monkeypatch.setattr(pipeline, "is_ffmpeg_ready", lambda: True)
    calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command))
    pipeline.extract_audio(source, destination)
    assert calls[0][0] == "ffmpeg"
    assert calls[0][-1] == str(destination)

    monkeypatch.setattr(pipeline, "is_ffmpeg_ready", lambda: False)
    with pytest.raises(StudioError) as missing:
        pipeline.extract_audio(source, destination)
    assert missing.value.code == "FFMPEG_NOT_FOUND"

    monkeypatch.setattr(pipeline, "is_ffmpeg_ready", lambda: True)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="ffmpeg", timeout=90)
        ),
    )
    with pytest.raises(StudioError) as timeout:
        pipeline.extract_audio(source, destination)
    assert timeout.value.code == "AUDIO_EXTRACTION_TIMEOUT"

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(returncode=1, cmd="ffmpeg")
        ),
    )
    with pytest.raises(StudioError) as failed:
        pipeline.extract_audio(source, destination)
    assert failed.value.code == "AUDIO_EXTRACTION_FAILED"


def test_whisper_success_missing_model_and_malformed_worker_result(tmp_path: Path) -> None:
    missing = LocalWhisperEngine(tmp_path / "missing.pt")
    assert missing.model_id.endswith("@missing")
    with pytest.raises(StudioError) as not_ready:
        missing.transcribe(tmp_path / "audio.wav", "auto")
    assert not_ready.value.code == "MODEL_NOT_FOUND"

    model = tmp_path / "base.pt"
    audio = tmp_path / "audio.wav"
    model.write_bytes(b"fixture model")
    audio.write_bytes(b"fixture audio")
    success = LocalWhisperEngine(model, worker_target=successful_worker)
    language, segments = success.transcribe(audio, "auto")
    assert language == "en"
    assert segments[0].text == "Approved text"

    malformed = LocalWhisperEngine(model, worker_target=malformed_worker)
    with pytest.raises(StudioError) as invalid:
        malformed.transcribe(audio, "auto")
    assert invalid.value.code == "TRANSCRIPTION_FAILED"

    no_speech = LocalWhisperEngine(model, worker_target=no_speech_worker)
    with pytest.raises(StudioError) as empty:
        no_speech.transcribe(audio, "auto")
    assert empty.value.code == "NO_SPEECH_DETECTED"

    invalid_schema = LocalWhisperEngine(model, worker_target=invalid_schema_worker)
    with pytest.raises(StudioError) as schema:
        invalid_schema.transcribe(audio, "auto")
    assert schema.value.code == "TRANSCRIPTION_FAILED"
