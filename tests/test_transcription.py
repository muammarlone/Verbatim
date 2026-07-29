from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import pytest

from secure_transcribe.errors import StudioError
from secure_transcribe.transcription import LocalWhisperEngine


def slow_worker(model_path: str, audio_path: str, language: str, output_path: str) -> None:
    del model_path, audio_path, language, output_path
    time.sleep(10)


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
