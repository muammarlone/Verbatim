from __future__ import annotations

import json
import os
import shutil
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from time import monotonic
from uuid import UUID, uuid4

from .config import Settings
from .errors import BatchNotFoundError, StudioError
from .exports import SUPPORTED_EXPORT_FORMATS, render_export, safe_export_base
from .security import SUPPORTED_MEDIA_EXTENSIONS
from .models import (
    BatchItem,
    BatchItemStatus,
    BatchRecord,
    BatchStatus,
    JobError,
    JobStatus,
    utc_now,
)
from .storage import JobStore


def _is_link_or_junction(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda _: False)
    return path.is_symlink() or bool(is_junction(path))


def resolve_workspace_folder(root: Path, value: str, *, create: bool = False) -> tuple[Path, str]:
    root = root.resolve()
    raw = value.strip().replace("\\", "/")
    relative = Path(raw)
    if not raw or relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise StudioError(
            "INVALID_BATCH_FOLDER",
            "Choose a relative folder inside the approved batch workspace.",
        )
    unresolved = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and _is_link_or_junction(current):
            raise StudioError(
                "BATCH_LINK_BLOCKED",
                "Linked or redirected folders are not allowed in the batch workspace.",
            )
    candidate = unresolved.resolve()
    if candidate == root or not candidate.is_relative_to(root):
        raise StudioError(
            "BATCH_PATH_OUTSIDE_ROOT",
            "The batch folder must stay inside the approved batch workspace.",
        )
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir():
        raise StudioError("BATCH_FOLDER_NOT_FOUND", "The selected input folder does not exist.")
    normalized = candidate.relative_to(root).as_posix()
    return candidate, normalized


def discover_workspace_folders(root: Path) -> list[str]:
    folders: list[str] = []
    for path in root.iterdir():
        if path.name.startswith(".") or not path.is_dir() or _is_link_or_junction(path):
            continue
        folders.append(path.relative_to(root).as_posix())
    return sorted(folders, key=str.casefold)


class BatchStore:
    def __init__(self, data_dir: Path) -> None:
        self.batches_dir = data_dir.resolve() / "batches"
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _batch_dir(self, batch_id: str) -> Path:
        try:
            normalized = str(UUID(batch_id))
        except ValueError as exc:
            raise BatchNotFoundError() from exc
        candidate = (self.batches_dir / normalized).resolve()
        if candidate.parent != self.batches_dir:
            raise BatchNotFoundError()
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

    def create(self, record: BatchRecord) -> BatchRecord:
        with self._lock:
            directory = self._batch_dir(record.id)
            directory.mkdir(mode=0o700)
            self._write_json_atomic(directory / "batch.json", record.model_dump(mode="json"))
        return record

    def get(self, batch_id: str) -> BatchRecord:
        path = self._batch_dir(batch_id) / "batch.json"
        if not path.is_file():
            raise BatchNotFoundError()
        with self._lock, path.open("r", encoding="utf-8") as handle:
            return BatchRecord.model_validate(json.load(handle))

    def list(self) -> list[BatchRecord]:
        records: list[BatchRecord] = []
        for directory in self.batches_dir.iterdir():
            if not directory.is_dir():
                continue
            try:
                records.append(self.get(directory.name))
            except (BatchNotFoundError, json.JSONDecodeError, OSError):
                continue
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def update(self, batch_id: str, **changes: object) -> BatchRecord:
        with self._lock:
            record = self.get(batch_id)
            payload = record.model_dump()
            payload.update(changes)
            payload["updated_at"] = utc_now()
            updated = BatchRecord.model_validate(payload)
            self._write_json_atomic(
                self._batch_dir(batch_id) / "batch.json", updated.model_dump(mode="json")
            )
            return updated

    def delete(self, batch_id: str) -> None:
        directory = self._batch_dir(batch_id)
        if not directory.is_dir():
            raise BatchNotFoundError()
        with self._lock:
            shutil.rmtree(directory)

    def sweep_expired(self, retention_days: int) -> int:
        cutoff = utc_now() - timedelta(days=retention_days)
        removed = 0
        for record in self.list():
            if record.created_at < cutoff:
                self.delete(record.id)
                removed += 1
        return removed


class BatchManager:
    def __init__(
        self,
        store: JobStore,
        batch_store: BatchStore,
        settings: Settings,
        processor,
        model_id: str,
    ) -> None:
        self.store = store
        self.batch_store = batch_store
        self.settings = settings
        self.processor = processor
        self.model_id = model_id
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="batch-monitor")
        self._shutdown = threading.Event()
        self._monitored: set[str] = set()
        self._monitor_futures: dict[str, Future] = {}
        self._lock = threading.Lock()

    def _normalize_formats(self, formats: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in formats:
            item = value.strip().lower()
            if item not in SUPPORTED_EXPORT_FORMATS:
                raise StudioError(
                    "UNSUPPORTED_EXPORT",
                    "Choose TXT, SRT, VTT, Markdown, or JSON.",
                )
            if item not in normalized:
                normalized.append(item)
        if not normalized:
            raise StudioError("EXPORT_FORMAT_REQUIRED", "Choose at least one output format.")
        return normalized

    def create_batch(
        self,
        *,
        input_folder: str,
        output_folder: str,
        formats: list[str],
        language: str,
    ) -> BatchRecord:
        selected_formats = self._normalize_formats(formats)
        input_path, input_name = resolve_workspace_folder(
            self.settings.batch_workspace, input_folder
        )
        output_path, output_name = resolve_workspace_folder(
            self.settings.batch_workspace, output_folder, create=True
        )
        if input_path == output_path:
            raise StudioError(
                "BATCH_FOLDERS_MUST_DIFFER",
                "Choose different input and output folders.",
            )

        paths = sorted(
            (
                path
                for path in input_path.iterdir()
                if path.is_file()
                and not _is_link_or_junction(path)
                and path.suffix.casefold() in SUPPORTED_MEDIA_EXTENSIONS
                and path.resolve().parent == input_path
            ),
            key=lambda item: item.name.casefold(),
        )
        if not paths:
            supported = ", ".join(sorted(e.lstrip(".").upper() for e in SUPPORTED_MEDIA_EXTENSIONS))
            raise StudioError(
                "NO_MEDIA_FILES",
                f"The input folder contains no supported media files ({supported}).",
            )
        if len(paths) > self.settings.max_batch_files:
            raise StudioError(
                "BATCH_FILE_LIMIT_EXCEEDED",
                f"Select a folder with no more than {self.settings.max_batch_files} media files.",
                http_status=413,
            )
        total_bytes = sum(path.stat().st_size for path in paths)
        if total_bytes > self.settings.max_batch_bytes:
            raise StudioError(
                "BATCH_SIZE_LIMIT_EXCEEDED",
                "The combined media size exceeds the configured batch limit.",
                http_status=413,
            )

        acceptable = [
            path for path in paths if 0 < path.stat().st_size <= self.settings.max_upload_bytes
        ]
        if acceptable:
            self.store.ensure_capacity(len(acceptable))
        output_names: set[str] = set()
        for path in acceptable:
            base = safe_export_base(path.name)
            for export_format in selected_formats:
                filename = f"{base}.{export_format}"
                key = filename.casefold()
                if key in output_names:
                    raise StudioError(
                        "OUTPUT_NAME_COLLISION",
                        "Two source files would create the same output name.",
                        http_status=409,
                    )
                output_names.add(key)
                if (output_path / filename).exists():
                    raise StudioError(
                        "OUTPUT_EXISTS",
                        f"Output already exists: {filename}. Existing files are never overwritten.",
                        http_status=409,
                    )

        batch_id = str(uuid4())
        items: list[BatchItem] = []
        created_job_ids: list[str] = []
        try:
            for path in paths:
                size = path.stat().st_size
                if size == 0:
                    items.append(
                        BatchItem(
                            source_name=path.name,
                            status=BatchItemStatus.REJECTED,
                            error=JobError(code="EMPTY_UPLOAD", message="The MP4 file is empty."),
                        )
                    )
                    continue
                if size > self.settings.max_upload_bytes:
                    items.append(
                        BatchItem(
                            source_name=path.name,
                            status=BatchItemStatus.REJECTED,
                            error=JobError(
                                code="UPLOAD_TOO_LARGE",
                                message="The MP4 file exceeds the per-file size limit.",
                            ),
                        )
                    )
                    continue
                job = self.store.create_job(
                    display_name=path.name,
                    language=language,
                    model_id=self.model_id,
                    size_bytes=size,
                )
                created_job_ids.append(job.id)
                try:
                    shutil.copyfile(path, self.store.source_path(job.id))
                except OSError:
                    self.store.delete_job(job.id, reason="batch_copy_rejected")
                    created_job_ids.remove(job.id)
                    items.append(
                        BatchItem(
                            source_name=path.name,
                            status=BatchItemStatus.REJECTED,
                            error=JobError(
                                code="FILE_COPY_FAILED",
                                message="The MP4 could not be copied into managed local storage.",
                            ),
                        )
                    )
                    continue
                items.append(
                    BatchItem(
                        source_name=path.name,
                        job_id=job.id,
                        status=BatchItemStatus.QUEUED,
                    )
                )

            now = utc_now()
            rejected = sum(item.status == BatchItemStatus.REJECTED for item in items)
            record = BatchRecord(
                id=batch_id,
                status=BatchStatus.QUEUED if created_job_ids else BatchStatus.FAILED,
                created_at=now,
                updated_at=now,
                input_folder=input_name,
                output_folder=output_name,
                formats=selected_formats,
                language_requested=language,
                total_files=len(items),
                completed_files=0,
                failed_files=rejected,
                total_bytes=total_bytes,
                items=items,
            )
            self.batch_store.create(record)
        except Exception:
            for job_id in created_job_ids:
                if self.store.has_job(job_id):
                    self.store.delete_job(job_id, reason="batch_setup_rollback")
            raise

        self.store.audit(
            "batch_created",
            details={
                "batch_id": batch_id,
                "file_count": len(items),
                "accepted_count": len(created_job_ids),
                "format_count": len(selected_formats),
            },
        )
        for job_id in created_job_ids:
            self.processor.submit(job_id)
        if created_job_ids:
            self._start_monitor(batch_id)
        else:
            self._finalize(batch_id)
        return self.batch_store.get(batch_id)

    def _start_monitor(self, batch_id: str) -> None:
        with self._lock:
            if batch_id in self._monitored:
                return
            self._monitored.add(batch_id)
            future = self.executor.submit(self._monitor, batch_id)
            self._monitor_futures[batch_id] = future
        future.add_done_callback(lambda _: self._forget_monitor(batch_id))

    def _forget_monitor(self, batch_id: str) -> None:
        with self._lock:
            self._monitored.discard(batch_id)
            self._monitor_futures.pop(batch_id, None)

    def _write_output(self, target: Path, body: str) -> None:
        encoded = body.encode("utf-8")
        if target.exists():
            if target.is_file() and target.read_bytes() == encoded:
                return
            raise StudioError(
                "OUTPUT_EXISTS",
                f"Output already exists: {target.name}. Existing files are never overwritten.",
                http_status=409,
            )
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.is_file() and target.read_bytes() == encoded:
                    return
                raise StudioError(
                    "OUTPUT_EXISTS",
                    f"Output already exists: {target.name}. Existing files are never overwritten.",
                    http_status=409,
                )
            except OSError as exc:
                raise StudioError(
                    "OUTPUT_WRITE_FAILED",
                    f"Output could not be published: {target.name}.",
                    http_status=507,
                ) from exc
        except OSError as exc:
            raise StudioError(
                "OUTPUT_WRITE_FAILED",
                f"Output could not be written: {target.name}.",
                http_status=507,
            ) from exc
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _item_error(exc: StudioError | OSError) -> JobError:
        if isinstance(exc, StudioError):
            return JobError(code=exc.code, message=exc.message)
        return JobError(
            code="BATCH_ITEM_IO_FAILED",
            message="A local filesystem error stopped this file from completing.",
        )

    def _export_completed_item(
        self, batch: BatchRecord, item: BatchItem, output_path: Path
    ) -> BatchItem:
        if not item.job_id:
            return item
        transcript = self.store.get_transcript(item.job_id)
        analysis = self.store.get_analysis(item.job_id)
        outputs = list(item.outputs)
        base = safe_export_base(item.source_name)
        for export_format in batch.formats:
            _, _, extension = render_export(transcript, analysis, export_format)
            filename = f"{base}.{extension}"
            if filename in outputs:
                continue
            body, _, _ = render_export(transcript, analysis, export_format)
            self._write_output(output_path / filename, body)
            outputs.append(filename)
        return item.model_copy(
            update={"status": BatchItemStatus.COMPLETE, "outputs": outputs, "error": None}
        )

    def _monitor(self, batch_id: str) -> None:
        started = monotonic()
        max_wait = self.settings.max_batch_files * (
            self.settings.ffmpeg_timeout_seconds + self.settings.transcription_timeout_seconds
        )
        try:
            while not self._shutdown.is_set():
                batch = self.batch_store.get(batch_id)
                output_path, _ = resolve_workspace_folder(
                    self.settings.batch_workspace, batch.output_folder
                )
                items: list[BatchItem] = []
                all_terminal = True
                for item in batch.items:
                    if not item.job_id or item.status in {
                        BatchItemStatus.COMPLETE,
                        BatchItemStatus.FAILED,
                        BatchItemStatus.REJECTED,
                    }:
                        items.append(item)
                        continue
                    try:
                        job = self.store.get_job(item.job_id)
                        if job.status == JobStatus.COMPLETE:
                            items.append(self._export_completed_item(batch, item, output_path))
                        elif job.status == JobStatus.FAILED:
                            items.append(
                                item.model_copy(
                                    update={
                                        "status": BatchItemStatus.FAILED,
                                        "error": job.error,
                                    }
                                )
                            )
                        else:
                            all_terminal = False
                            items.append(
                                item.model_copy(update={"status": BatchItemStatus.PROCESSING})
                            )
                    except (StudioError, OSError) as exc:
                        items.append(
                            item.model_copy(
                                update={
                                    "status": BatchItemStatus.FAILED,
                                    "error": self._item_error(exc),
                                }
                            )
                        )
                completed = sum(item.status == BatchItemStatus.COMPLETE for item in items)
                failed = sum(
                    item.status in {BatchItemStatus.FAILED, BatchItemStatus.REJECTED}
                    for item in items
                )
                self.batch_store.update(
                    batch_id,
                    status=BatchStatus.RUNNING,
                    items=items,
                    completed_files=completed,
                    failed_files=failed,
                )
                if all_terminal:
                    self._finalize(batch_id)
                    return
                if monotonic() - started > max_wait:
                    self._timeout(batch_id)
                    return
                self._shutdown.wait(0.25)
        except BatchNotFoundError:
            return
        except Exception as exc:
            self._fail_batch(batch_id, exc)

    def _fail_batch(self, batch_id: str, exc: Exception) -> None:
        reason = exc.code if isinstance(exc, StudioError) else "BATCH_MONITOR_FAILED"
        message = (
            exc.message
            if isinstance(exc, StudioError)
            else "Batch processing stopped because of an unexpected local error."
        )
        try:
            batch = self.batch_store.get(batch_id)
            items: list[BatchItem] = []
            for item in batch.items:
                if item.status in {
                    BatchItemStatus.COMPLETE,
                    BatchItemStatus.FAILED,
                    BatchItemStatus.REJECTED,
                }:
                    items.append(item)
                else:
                    items.append(
                        item.model_copy(
                            update={
                                "status": BatchItemStatus.FAILED,
                                "error": JobError(code=reason, message=message),
                            }
                        )
                    )
            completed = sum(item.status == BatchItemStatus.COMPLETE for item in items)
            failed = sum(
                item.status in {BatchItemStatus.FAILED, BatchItemStatus.REJECTED} for item in items
            )
            self.batch_store.update(
                batch_id,
                status=BatchStatus.FAILED,
                completed_files=completed,
                failed_files=failed,
                error=JobError(code=reason, message=message),
                items=items,
            )
        except (BatchNotFoundError, OSError, ValueError, json.JSONDecodeError):
            pass
        self.store.audit(
            "batch_failed",
            details={"batch_id": batch_id, "reason_code": reason},
        )

    def _timeout(self, batch_id: str) -> None:
        batch = self.batch_store.get(batch_id)
        items: list[BatchItem] = []
        for item in batch.items:
            if item.job_id and item.status not in {
                BatchItemStatus.COMPLETE,
                BatchItemStatus.FAILED,
                BatchItemStatus.REJECTED,
            }:
                cancel = getattr(self.processor, "cancel", None)
                if cancel:
                    cancel(item.job_id)
                item = item.model_copy(
                    update={
                        "status": BatchItemStatus.FAILED,
                        "error": JobError(
                            code="BATCH_TIMEOUT",
                            message="The bounded batch processing window was exhausted.",
                        ),
                    }
                )
            items.append(item)
        self.batch_store.update(batch_id, items=items)
        self._finalize(batch_id)

    def _finalize(self, batch_id: str) -> BatchRecord:
        batch = self.batch_store.get(batch_id)
        completed = sum(item.status == BatchItemStatus.COMPLETE for item in batch.items)
        failed = sum(
            item.status in {BatchItemStatus.FAILED, BatchItemStatus.REJECTED}
            for item in batch.items
        )
        status = (
            BatchStatus.COMPLETE
            if completed == batch.total_files
            else BatchStatus.PARTIAL
            if completed
            else BatchStatus.FAILED
        )
        final = batch.model_copy(
            update={
                "status": status,
                "completed_files": completed,
                "failed_files": failed,
                "updated_at": utc_now(),
                "error": None,
            }
        )
        manifest_name = f"verbatim-batch-{batch.id}.json"
        manifest = {
            "schema_version": "1.0",
            "batch_id": final.id,
            "status": final.status,
            "input_folder": final.input_folder,
            "output_folder": final.output_folder,
            "formats": final.formats,
            "total_files": final.total_files,
            "completed_files": final.completed_files,
            "failed_files": final.failed_files,
            "items": [item.model_dump(mode="json") for item in final.items],
            "claim_boundary": "Each transcript requires human review against its source recording.",
        }
        output_path, _ = resolve_workspace_folder(
            self.settings.batch_workspace, final.output_folder
        )
        self._write_output(
            output_path / manifest_name,
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
        )
        final = self.batch_store.update(
            batch_id,
            status=status,
            completed_files=completed,
            failed_files=failed,
            manifest_name=manifest_name,
            error=None,
            items=final.items,
        )
        self.store.audit(
            "batch_completed",
            details={
                "batch_id": batch_id,
                "status": status,
                "completed_count": completed,
                "failed_count": failed,
            },
        )
        return final

    def resume_pending(self) -> None:
        for batch in self.batch_store.list():
            if batch.status not in {BatchStatus.QUEUED, BatchStatus.RUNNING}:
                continue
            for item in batch.items:
                if not item.job_id or not self.store.has_job(item.job_id):
                    continue
                job = self.store.get_job(item.job_id)
                if job.status not in {JobStatus.COMPLETE, JobStatus.FAILED}:
                    self.processor.submit(item.job_id)
            self._start_monitor(batch.id)

    def delete_batch(self, batch_id: str) -> None:
        batch = self.batch_store.get(batch_id)
        if batch.status in {BatchStatus.QUEUED, BatchStatus.RUNNING}:
            raise StudioError(
                "BATCH_STILL_RUNNING",
                "Wait for the batch to finish before removing managed copies.",
                http_status=409,
            )
        deleted_jobs = 0
        for item in batch.items:
            if item.job_id and self.store.has_job(item.job_id):
                self.store.delete_job(item.job_id, reason="batch_cleanup")
                deleted_jobs += 1
        self.batch_store.delete(batch_id)
        self.store.audit(
            "batch_deleted",
            details={"batch_id": batch_id, "managed_job_count": deleted_jobs},
        )

    def owns_job(self, job_id: str) -> bool:
        return any(
            item.job_id == job_id for batch in self.batch_store.list() for item in batch.items
        )

    def shutdown(self) -> None:
        self._shutdown.set()
        self.executor.shutdown(wait=False, cancel_futures=True)
