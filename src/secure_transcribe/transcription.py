from __future__ import annotations

import json
import hashlib
import multiprocessing
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Protocol

from .errors import StudioError
from .models import MediaProbe, TranscriptSegment


def _hidden_process_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


class MediaPipeline(Protocol):
    def probe(self, source: Path) -> MediaProbe: ...

    def extract_audio(self, source: Path, destination: Path) -> None: ...


class TranscriptEngine(Protocol):
    @property
    def model_id(self) -> str: ...

    def is_ready(self) -> bool: ...

    def transcribe(
        self, audio_path: Path, language: str
    ) -> tuple[str, list[TranscriptSegment]]: ...


class FFmpegMediaPipeline:
    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def is_ffmpeg_ready() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def is_ffprobe_ready() -> bool:
        return shutil.which("ffprobe") is not None

    def probe(self, source: Path) -> MediaProbe:
        if not self.is_ffprobe_ready():
            raise StudioError(
                "FFPROBE_NOT_FOUND",
                "FFprobe is required. Ask IT to install the approved FFmpeg package.",
            )
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name:stream=codec_type,codec_name",
            "-of",
            "json",
            str(source),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=min(self.timeout_seconds, 120),
                creationflags=_hidden_process_flags(),
            )
            payload = json.loads(result.stdout)
        except subprocess.TimeoutExpired as exc:
            raise StudioError("FFPROBE_TIMEOUT", "Media validation timed out.") from exc
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise StudioError(
                "MEDIA_PROBE_FAILED", "FFprobe could not read this MP4 file."
            ) from exc

        streams = payload.get("streams", [])
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        video = next((item for item in streams if item.get("codec_type") == "video"), None)
        if audio is None:
            raise StudioError("AUDIO_TRACK_MISSING", "This MP4 does not contain an audio track.")
        duration = float(payload["format"]["duration"])
        if duration <= 0:
            raise StudioError("INVALID_DURATION", "The MP4 duration is invalid.")
        return MediaProbe(
            duration_seconds=duration,
            audio_codec=str(audio.get("codec_name", "unknown")),
            video_codec=str(video.get("codec_name")) if video else None,
            format_name=str(payload["format"].get("format_name", "unknown")),
        )

    def extract_audio(self, source: Path, destination: Path) -> None:
        if not self.is_ffmpeg_ready():
            raise StudioError(
                "FFMPEG_NOT_FOUND",
                "FFmpeg is required. Ask IT to install the approved FFmpeg package.",
            )
        command = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
        try:
            subprocess.run(
                command,
                capture_output=True,
                check=True,
                timeout=self.timeout_seconds,
                creationflags=_hidden_process_flags(),
            )
        except subprocess.TimeoutExpired as exc:
            raise StudioError("AUDIO_EXTRACTION_TIMEOUT", "Audio extraction timed out.") from exc
        except subprocess.CalledProcessError as exc:
            raise StudioError("AUDIO_EXTRACTION_FAILED", "Audio extraction failed.") from exc


class LocalWhisperEngine:
    """Killable local Whisper adapter that never downloads model files."""

    def __init__(
        self,
        model_path: Path,
        timeout_seconds: int = 7_200,
        *,
        worker_target: Callable[[str, str, str, str], None] | None = None,
    ) -> None:
        self.model_path = model_path.resolve()
        self.timeout_seconds = timeout_seconds
        self._worker_target = worker_target
        self._model_id: str | None = None
        self._lock = threading.Lock()
        self._process_lock = threading.Lock()
        self._processes: dict[str, multiprocessing.Process] = {}
        self._cancelled: set[str] = set()

    @property
    def model_id(self) -> str:
        if self._model_id is None:
            with self._lock:
                if self._model_id is None:
                    if not self.model_path.is_file():
                        return f"openai-whisper:{self.model_path.name}@missing"
                    digest = hashlib.sha256()
                    with self.model_path.open("rb") as handle:
                        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                            digest.update(chunk)
                    self._model_id = (
                        f"openai-whisper:{self.model_path.name}@sha256:{digest.hexdigest()}"
                    )
        return self._model_id

    def is_ready(self) -> bool:
        return self.model_path.is_file()

    def transcribe(self, audio_path: Path, language: str) -> tuple[str, list[TranscriptSegment]]:
        if not self.is_ready():
            raise StudioError(
                "MODEL_NOT_FOUND",
                f"Local model not found at {self.model_path}. Ask IT to provision an approved model file.",
            )
        output_path = audio_path.with_suffix(".whisper-result.json")
        output_path.unlink(missing_ok=True)
        context = multiprocessing.get_context("spawn")
        process = context.Process(
            target=self._worker_target or _transcribe_worker,
            args=(str(self.model_path), str(audio_path), language, str(output_path)),
            daemon=False,
        )
        job_id = audio_path.parent.name
        try:
            with self._process_lock:
                process.start()
                self._processes[job_id] = process
            process.join(self.timeout_seconds)
            with self._process_lock:
                was_cancelled = job_id in self._cancelled
            if was_cancelled:
                raise StudioError("TRANSCRIPTION_CANCELLED", "Transcription was cancelled.")
            if process.is_alive():
                process.terminate()
                process.join(5)
                if process.is_alive() and hasattr(process, "kill"):
                    process.kill()
                    process.join(5)
                raise StudioError(
                    "TRANSCRIPTION_TIMEOUT",
                    f"Transcription exceeded the {self.timeout_seconds}-second processing budget.",
                )
            if process.exitcode != 0 or not output_path.is_file():
                raise StudioError("TRANSCRIPTION_FAILED", "Local transcription failed.")
            with output_path.open("r", encoding="utf-8") as handle:
                result = json.load(handle)
            if not result.get("ok"):
                code = str(result.get("code", "TRANSCRIPTION_FAILED"))
                message = {
                    "MODEL_LOAD_FAILED": "The approved local Whisper model could not be loaded.",
                    "NO_SPEECH_DETECTED": "No speech was detected in this recording.",
                }.get(code, "Local transcription failed.")
                raise StudioError(code, message)
            return str(result["language"]), [
                TranscriptSegment.model_validate(item) for item in result["segments"]
            ]
        finally:
            with self._process_lock:
                self._processes.pop(job_id, None)
                self._cancelled.discard(job_id)
            output_path.unlink(missing_ok=True)

    def cancel(self, job_id: str) -> None:
        with self._process_lock:
            self._cancelled.add(job_id)
            process = self._processes.get(job_id)
            if process is not None and process.is_alive():
                process.terminate()


def _transcribe_worker(model_path: str, audio_path: str, language: str, output_path: str) -> None:
    payload: dict
    try:
        import whisper

        try:
            model = whisper.load_model(model_path)
        except Exception:
            payload = {"ok": False, "code": "MODEL_LOAD_FAILED"}
        else:
            try:
                options = {
                    "verbose": False,
                    "temperature": 0,
                    "condition_on_previous_text": False,
                    "fp16": False,
                }
                if language != "auto":
                    options["language"] = language
                result = model.transcribe(audio_path, **options)
                segments = [
                    {
                        "id": index,
                        "start": max(0, float(item["start"])),
                        "end": max(0, float(item["end"])),
                        "text": str(item["text"]).strip(),
                    }
                    for index, item in enumerate(result.get("segments", []))
                    if str(item.get("text", "")).strip()
                ]
                payload = (
                    {
                        "ok": True,
                        "language": str(result.get("language") or language or "unknown"),
                        "segments": segments,
                    }
                    if segments
                    else {"ok": False, "code": "NO_SPEECH_DETECTED"}
                )
            except Exception:
                payload = {"ok": False, "code": "TRANSCRIPTION_FAILED"}
    except Exception:
        payload = {"ok": False, "code": "MODEL_LOAD_FAILED"}
    destination = Path(output_path)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
