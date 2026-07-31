from __future__ import annotations

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

from .analysis import analyze_transcript
from .audit_store import AuditStore
from .config import Settings
from .errors import StudioError
from .models import JobError, JobStatus, TranscriptDocument, utc_now
from .security import sha256_file, validate_media_signature
from .storage import JobStore
from .transcription import MediaPipeline, TranscriptEngine


class _JobCancelled(Exception):
    pass


class JobProcessor:
    def __init__(
        self,
        store: JobStore,
        settings: Settings,
        media: MediaPipeline,
        transcriber: TranscriptEngine,
        *,
        executor: ThreadPoolExecutor | None = None,
        audit_store: AuditStore | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.media = media
        self.transcriber = transcriber
        self.audit_store = audit_store
        self.executor = executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="local-transcription"
        )
        self._lock = threading.Lock()
        self._cancelled: set[str] = set()
        self._futures = {}

    def submit(self, job_id: str) -> None:
        future = self.executor.submit(self.process, job_id)
        with self._lock:
            self._futures[job_id] = future
        future.add_done_callback(lambda _: self._forget(job_id))

    def _forget(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)
            self._cancelled.discard(job_id)

    def _checkpoint(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._cancelled:
                raise _JobCancelled()

    def cancel(self, job_id: str) -> None:
        with self._lock:
            self._cancelled.add(job_id)
            future = self._futures.get(job_id)
        if future is not None:
            future.cancel()
        cancel_engine = getattr(self.transcriber, "cancel", None)
        if cancel_engine:
            cancel_engine(job_id)

    def process(self, job_id: str) -> None:
        source = self.store.source_path(job_id)
        audio = self.store.audio_path(job_id)
        try:
            self._checkpoint(job_id)
            self.store.update_job(job_id, status=JobStatus.VALIDATING, progress=8, error=None)
            validate_media_signature(source)
            probe = self.media.probe(source)
            self._checkpoint(job_id)
            if probe.duration_seconds > self.settings.max_media_seconds:
                raise StudioError(
                    "MEDIA_TOO_LONG",
                    f"This video exceeds the {self.settings.max_media_seconds // 3600}-hour limit.",
                )
            source_sha256 = sha256_file(source)
            self.store.update_job(
                job_id,
                status=JobStatus.EXTRACTING,
                progress=18,
                duration_seconds=round(probe.duration_seconds, 3),
                source_sha256=source_sha256,
            )
            if self.audit_store:
                self.audit_store.write_source(
                    job_id,
                    source_hash=f"sha256:{source_sha256}",
                    size_bytes=source.stat().st_size,
                    format=source.suffix.lstrip(".").lower(),
                    duration_seconds=round(probe.duration_seconds, 3),
                )
            self.media.extract_audio(source, audio)
            if self.audit_store:
                self.audit_store.write_extraction(
                    job_id,
                    ffmpeg_version=getattr(self.media, "ffmpeg_version", lambda: "unknown")(),
                    params_hash=hashlib.sha256(b"default-extraction-params").hexdigest(),
                    output_hash=f"sha256:{sha256_file(audio)}",
                )
            self._checkpoint(job_id)
            self.store.update_job(job_id, status=JobStatus.TRANSCRIBING, progress=32)
            job = self.store.get_job(job_id)
            language, segments = self.transcriber.transcribe(audio, job.language_requested)
            self._checkpoint(job_id)
            transcript = TranscriptDocument(
                job_id=job_id,
                language=language,
                duration_seconds=probe.duration_seconds,
                model_id=self.transcriber.model_id,
                created_at=utc_now(),
                segments=segments,
                text=" ".join(item.text for item in segments),
            )
            self.store.write_transcript(transcript)
            if self.audit_store:
                self.audit_store.write_transcription(
                    job_id,
                    model_id=self.transcriber.model_id,
                    model_hash=getattr(self.transcriber, "model_hash", None) or "unknown",
                    language=language,
                    params_hash=hashlib.sha256(job.language_requested.encode()).hexdigest(),
                    segment_count=len(segments),
                )
                for i, seg in enumerate(segments):
                    text_hash = hashlib.sha256(seg.text.encode()).hexdigest()
                    self.audit_store.write_segment(
                        job_id,
                        index=i,
                        start_ms=int(seg.start * 1000),
                        end_ms=int(seg.end * 1000),
                        text_hash=f"sha256:{text_hash}",
                        avg_logprob=float(
                            seg.avg_logprob if seg.avg_logprob is not None else -0.5
                        ),
                        no_speech_prob=float(
                            seg.no_speech_prob if seg.no_speech_prob is not None else 0.0
                        ),
                    )
            self.store.update_job(job_id, status=JobStatus.ANALYZING, progress=88)
            self.store.write_analysis(analyze_transcript(transcript))
            self._checkpoint(job_id)
            self.store.update_job(
                job_id,
                status=JobStatus.COMPLETE,
                progress=100,
                detected_language=language,
                segment_count=len(segments),
                error=None,
            )
            self.store.audit(
                "job_completed",
                job_id,
                {"segment_count": len(segments), "model_id": self.transcriber.model_id},
            )
        except _JobCancelled:
            self.store.audit("job_cancelled", job_id)
        except StudioError as exc:
            with self._lock:
                if job_id in self._cancelled:
                    return
            self.store.update_job(
                job_id,
                status=JobStatus.FAILED,
                progress=100,
                error=JobError(code=exc.code, message=exc.message),
            )
            self.store.audit("job_failed", job_id, {"reason_code": exc.code})
        except Exception:
            with self._lock:
                if job_id in self._cancelled:
                    return
            self.store.update_job(
                job_id,
                status=JobStatus.FAILED,
                progress=100,
                error=JobError(
                    code="UNEXPECTED_PROCESSING_ERROR",
                    message="Processing stopped because of an unexpected local error.",
                ),
            )
            self.store.audit("job_failed", job_id, {"reason_code": "UNEXPECTED_PROCESSING_ERROR"})
        finally:
            audio.unlink(missing_ok=True)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)
