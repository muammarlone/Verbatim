from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from .errors import NotFoundError, StudioError
from .models import (
    AnalysisReport,
    AuditEvent,
    JobRecord,
    JobStatus,
    TranscriptDocument,
    TranscriptRevisionRecord,
    utc_now,
)


class JobStore:
    def __init__(self, data_dir: Path, *, max_jobs: int = 100) -> None:
        self.data_dir = data_dir.resolve()
        self.jobs_dir = self.data_dir / "jobs"
        self.audit_dir = self.data_dir / "audit"
        self.max_jobs = max_jobs
        self._lock = threading.RLock()
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def _job_dir(self, job_id: str) -> Path:
        try:
            normalized = str(UUID(job_id))
        except ValueError as exc:
            raise NotFoundError() from exc
        candidate = (self.jobs_dir / normalized).resolve()
        if candidate.parent != self.jobs_dir:
            raise NotFoundError()
        return candidate

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)

    def create_job(
        self,
        *,
        display_name: str,
        language: str,
        model_id: str,
        size_bytes: int = 0,
    ) -> JobRecord:
        with self._lock:
            active_count = sum(1 for path in self.jobs_dir.iterdir() if path.is_dir())
            if active_count >= self.max_jobs:
                raise StudioError(
                    "JOB_CAPACITY_REACHED",
                    "The local job limit has been reached. Delete an old job and try again.",
                    http_status=409,
                )
            now = utc_now()
            job = JobRecord(
                id=str(uuid4()),
                display_name=display_name,
                status=JobStatus.QUEUED,
                progress=0,
                created_at=now,
                updated_at=now,
                size_bytes=size_bytes,
                language_requested=language,
                model_id=model_id,
            )
            directory = self._job_dir(job.id)
            directory.mkdir(mode=0o700)
            self._write_json_atomic(directory / "job.json", job.model_dump(mode="json"))
            self.audit("job_created", job.id)
            return job

    def ensure_capacity(self, requested: int) -> None:
        with self._lock:
            active_count = sum(1 for path in self.jobs_dir.iterdir() if path.is_dir())
            if requested < 1 or active_count + requested > self.max_jobs:
                raise StudioError(
                    "JOB_CAPACITY_REACHED",
                    "The local job limit cannot accommodate this batch. Delete old jobs or select fewer files.",
                    http_status=409,
                )

    def has_job(self, job_id: str) -> bool:
        try:
            return (self._job_dir(job_id) / "job.json").is_file()
        except NotFoundError:
            return False

    def get_job(self, job_id: str) -> JobRecord:
        path = self._job_dir(job_id) / "job.json"
        if not path.is_file():
            raise NotFoundError()
        with self._lock, path.open("r", encoding="utf-8") as handle:
            return JobRecord.model_validate(json.load(handle))

    def list_jobs(self) -> list[JobRecord]:
        jobs: list[JobRecord] = []
        for directory in self.jobs_dir.iterdir():
            if not directory.is_dir():
                continue
            try:
                jobs.append(self.get_job(directory.name))
            except (NotFoundError, json.JSONDecodeError, OSError):
                continue
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)

    def update_job(self, job_id: str, **changes: object) -> JobRecord:
        with self._lock:
            job = self.get_job(job_id)
            payload = job.model_dump()
            payload.update(changes)
            payload["updated_at"] = utc_now()
            updated = JobRecord.model_validate(payload)
            self._write_json_atomic(
                self._job_dir(job_id) / "job.json", updated.model_dump(mode="json")
            )
            return updated

    def source_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "source.mp4"

    def audio_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "working.wav"

    def write_transcript(self, document: TranscriptDocument) -> None:
        with self._lock:
            self._write_json_atomic(
                self._job_dir(document.job_id) / "transcript.json",
                document.model_dump(mode="json"),
            )

    def get_transcript(self, job_id: str) -> TranscriptDocument:
        path = self._job_dir(job_id) / "transcript.json"
        if not path.is_file():
            raise StudioError(
                "TRANSCRIPT_NOT_READY", "The transcript is not ready yet.", http_status=409
            )
        with path.open("r", encoding="utf-8") as handle:
            return TranscriptDocument.model_validate(json.load(handle))

    def write_analysis(self, report: AnalysisReport) -> None:
        with self._lock:
            self._write_json_atomic(
                self._job_dir(report.job_id) / "analysis.json",
                report.model_dump(mode="json"),
            )

    def get_analysis(self, job_id: str) -> AnalysisReport:
        path = self._job_dir(job_id) / "analysis.json"
        if not path.is_file():
            raise StudioError("ANALYSIS_NOT_READY", "Analysis is not ready yet.", http_status=409)
        with path.open("r", encoding="utf-8") as handle:
            return AnalysisReport.model_validate(json.load(handle))

    def delete_job(self, job_id: str, *, reason: str = "user_request") -> None:
        directory = self._job_dir(job_id)
        if not directory.is_dir():
            raise NotFoundError()
        with self._lock:
            shutil.rmtree(directory)
            self.audit("job_deleted", job_id, {"reason": reason})

    def sweep_expired(self, retention_days: int) -> int:
        cutoff = utc_now() - timedelta(days=retention_days)
        removed = 0
        for job in self.list_jobs():
            if job.created_at < cutoff:
                self.delete_job(job.id, reason="retention_expired")
                removed += 1
        return removed

    def _revisions_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "transcript_revisions.jsonl"

    def apply_correction(
        self,
        job_id: str,
        segment_id: int,
        corrected_text: str,
        reason: str | None = None,
    ) -> TranscriptRevisionRecord:
        with self._lock:
            doc = self.get_transcript(job_id)
            target = next((s for s in doc.segments if s.id == segment_id), None)
            if target is None:
                raise StudioError(
                    "SEGMENT_NOT_FOUND",
                    f"Segment {segment_id} does not exist in this transcript.",
                    http_status=404,
                )
            revision = TranscriptRevisionRecord(
                revision_id=str(uuid4()),
                job_id=job_id,
                segment_id=segment_id,
                original_text=target.text,
                corrected_text=corrected_text,
                corrected_at=utc_now(),
                reason=reason,
            )
            target.text = corrected_text
            full_text = " ".join(s.text.strip() for s in doc.segments)
            updated_doc = doc.model_copy(update={"text": full_text})
            self.write_transcript(updated_doc)
            rev_path = self._revisions_path(job_id)
            with rev_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(revision.model_dump_json() + "\n")
            self.audit(
                "segment_corrected",
                job_id,
                {"revision_id": revision.revision_id, "segment_id": segment_id},
            )
            return revision

    def get_revisions(self, job_id: str) -> list[TranscriptRevisionRecord]:
        self._job_dir(job_id)
        rev_path = self._revisions_path(job_id)
        if not rev_path.is_file():
            return []
        records: list[TranscriptRevisionRecord] = []
        with self._lock, rev_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(TranscriptRevisionRecord.model_validate_json(line))
        return records

    def audit(self, event: str, job_id: str | None = None, details: dict | None = None) -> None:
        record = AuditEvent(timestamp=utc_now(), event=event, job_id=job_id, details=details or {})
        line = record.model_dump_json() + "\n"
        with (
            self._lock,
            (self.audit_dir / "events.jsonl").open("a", encoding="utf-8", newline="\n") as handle,
        ):
            handle.write(line)
