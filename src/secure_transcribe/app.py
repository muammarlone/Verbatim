from __future__ import annotations

import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Protocol

from fastapi import Depends, FastAPI, File, Form, Header, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .batch import BatchManager, BatchStore, discover_workspace_folders
from .config import Settings
from .errors import StudioError
from .exports import render_export, safe_export_base
from .manifest import ImportPlanStore, parse_manifest
from .models import BatchCreateRequest, HealthReport, JobStatus, TranscriptCorrectionRequest
from .security import validate_upload_metadata
from .service import JobProcessor
from .storage import JobStore
from .transcription import FFmpegMediaPipeline, LocalWhisperEngine, MediaPipeline, TranscriptEngine

STATIC_DIR = Path(__file__).with_name("static")
_LANGUAGE = re.compile(r"^(auto|[a-z]{2})$")
_MULTIPART_OVERHEAD_BYTES = 64 * 1024


class RequestBodyLimitMiddleware:
    def __init__(self, app, *, upload_max_bytes: int, manifest_max_bytes: int) -> None:
        self.app = app
        self.limits = {
            "/api/jobs": (
                upload_max_bytes,
                "REQUEST_TOO_LARGE",
                "The upload request exceeds the configured local limit.",
            ),
            "/api/import-plans/preview": (
                manifest_max_bytes,
                "MANIFEST_REQUEST_TOO_LARGE",
                "The manifest request exceeds the configured local limit.",
            ),
        }

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        limit = self.limits.get(scope["path"])
        if limit is None:
            await self.app(scope, receive, send)
            return
        max_bytes, error_code, error_message = limit
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                parsed_length = int(raw_length)
                if parsed_length < 0 or parsed_length > max_bytes:
                    await self._reject(scope, receive, send, error_code, error_message)
                    return
            except ValueError:
                await self._reject(scope, receive, send, error_code, error_message)
                return
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > max_bytes:
                    raise StudioError(error_code, error_message, http_status=413)
            return message

        try:
            await self.app(scope, limited_receive, send)
        except StudioError as exc:
            if exc.code != error_code:
                raise
            await self._reject(scope, receive, send, error_code, error_message)

    @staticmethod
    async def _reject(scope, receive, send, error_code: str, error_message: str) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": error_code,
                    "message": error_message,
                }
            },
        )
        await response(scope, receive, send)


class Processor(Protocol):
    def submit(self, job_id: str) -> None: ...

    def shutdown(self) -> None: ...

    def cancel(self, job_id: str) -> None: ...


ProcessorFactory = Callable[[JobStore, Settings, MediaPipeline, TranscriptEngine], Processor]


def create_app(
    settings: Settings | None = None,
    *,
    media: MediaPipeline | None = None,
    transcriber: TranscriptEngine | None = None,
    processor_factory: ProcessorFactory | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()
    store = JobStore(settings.data_dir, max_jobs=settings.max_jobs)
    media = media or FFmpegMediaPipeline(settings.ffmpeg_timeout_seconds)
    transcriber = transcriber or LocalWhisperEngine(
        settings.model_path, settings.transcription_timeout_seconds
    )
    active_processor = (
        processor_factory(store, settings, media, transcriber)
        if processor_factory
        else JobProcessor(store, settings, media, transcriber)
    )
    batch_store = BatchStore(settings.data_dir)
    batch_manager = BatchManager(
        store, batch_store, settings, active_processor, transcriber.model_id
    )
    import_plan_store = ImportPlanStore(
        ttl_seconds=settings.import_plan_ttl_seconds,
        max_plans=settings.max_import_plans,
    )
    csrf_token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.sweep_expired(settings.retention_days)
        batch_store.sweep_expired(settings.retention_days)
        import_plan_store.sweep_expired()
        store.audit("application_started", details={"app_version": settings.app_version})
        batch_manager.resume_pending()
        try:
            yield
        finally:
            store.audit("application_stopped", details={"app_version": settings.app_version})
            import_plan_store.close()
            batch_manager.shutdown()
            active_processor.shutdown()

    app = FastAPI(
        title="Secure Transcription Studio",
        version=settings.app_version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"],
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        upload_max_bytes=settings.max_upload_bytes + _MULTIPART_OVERHEAD_BYTES,
        manifest_max_bytes=settings.max_manifest_bytes + _MULTIPART_OVERHEAD_BYTES,
    )
    app.state.settings = settings
    app.state.store = store
    app.state.processor = active_processor
    app.state.transcriber = transcriber
    app.state.batch_store = batch_store
    app.state.batch_manager = batch_manager
    app.state.import_plan_store = import_plan_store

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; media-src 'self'; "
            "style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(StudioError)
    async def studio_error_handler(_, exc: StudioError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(_, __: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_FAILED",
                    "message": "Check the required fields and allowed values, then try again.",
                }
            },
        )

    def require_csrf(x_studio_token: str | None = Header(default=None)) -> None:
        if not x_studio_token or not secrets.compare_digest(x_studio_token, csrf_token):
            raise StudioError(
                "REQUEST_TOKEN_INVALID", "Refresh the page and try again.", http_status=403
            )

    @app.get("/api/session")
    def session() -> dict:
        return {
            "request_token": csrf_token,
            "max_upload_bytes": settings.max_upload_bytes,
            "max_media_seconds": settings.max_media_seconds,
            "retention_days": settings.retention_days,
            "batch_workspace": str(settings.batch_workspace),
            "max_batch_files": settings.max_batch_files,
            "max_batch_bytes": settings.max_batch_bytes,
            "batch_formats": ["txt", "srt", "vtt", "md", "json"],
            "manifest_intake_enabled": settings.manifest_intake_enabled,
            "protected_archive_enabled": settings.protected_archive_enabled,
            "zoom_connector_enabled": settings.zoom_connector_enabled,
            "max_manifest_bytes": settings.max_manifest_bytes,
            "import_plan_ttl_seconds": settings.import_plan_ttl_seconds,
            "network_required": False,
        }

    @app.get("/api/health", response_model=HealthReport)
    def health() -> HealthReport:
        ffmpeg_ready = bool(getattr(media, "is_ffmpeg_ready", lambda: False)())
        ffprobe_ready = bool(getattr(media, "is_ffprobe_ready", lambda: False)())
        model_ready = transcriber.is_ready()
        status = "ready" if ffmpeg_ready and ffprobe_ready and model_ready else "attention"
        return HealthReport(
            status=status,
            app_version=settings.app_version,
            ffmpeg_ready=ffmpeg_ready,
            ffprobe_ready=ffprobe_ready,
            model_ready=model_ready,
            model_id=transcriber.model_id,
        )

    @app.get("/api/jobs")
    def list_jobs():
        return {"jobs": [job.model_dump(mode="json") for job in store.list_jobs()]}

    def require_processing_ready() -> None:
        if (
            not getattr(media, "is_ffmpeg_ready", lambda: False)()
            or not getattr(media, "is_ffprobe_ready", lambda: False)()
        ):
            raise StudioError(
                "FFMPEG_NOT_READY",
                "FFmpeg and FFprobe must be installed before processing media.",
                http_status=503,
            )
        if not transcriber.is_ready():
            raise StudioError(
                "MODEL_NOT_READY",
                "The approved local Whisper model is not provisioned yet.",
                http_status=503,
            )

    @app.get("/api/batch-folders")
    def list_batch_folders():
        return {
            "workspace": str(settings.batch_workspace),
            "folders": discover_workspace_folders(settings.batch_workspace),
        }

    @app.post(
        "/api/import-plans/preview",
        status_code=201,
        dependencies=[Depends(require_csrf)],
    )
    async def preview_import_plan(file: UploadFile = File(...)):
        if not settings.manifest_intake_enabled:
            raise StudioError(
                "FEATURE_DISABLED",
                "Manifest intake is disabled by endpoint policy.",
                http_status=404,
            )
        payload = bytearray()
        try:
            while chunk := await file.read(64 * 1024):
                payload.extend(chunk)
                if len(payload) > settings.max_manifest_bytes:
                    raise StudioError(
                        "MANIFEST_REQUEST_TOO_LARGE",
                        "The manifest exceeds the configured local limit.",
                        http_status=413,
                    )
            rows = parse_manifest(
                filename=file.filename,
                content_type=file.content_type,
                payload=bytes(payload),
            )
        finally:
            await file.close()
        plan = import_plan_store.create(bytes(payload), rows)
        store.audit(
            "import_plan_previewed",
            details={
                "plan_id": plan.id,
                "manifest_sha256": plan.manifest_sha256,
                "row_count": plan.row_count,
                "schema_version": plan.schema_version,
            },
        )
        return {"plan": import_plan_store.preview(plan).model_dump(mode="json")}

    @app.get("/api/batches")
    def list_batches():
        return {"batches": [record.model_dump(mode="json") for record in batch_store.list()]}

    @app.get("/api/batches/{batch_id}")
    def get_batch(batch_id: str):
        return {"batch": batch_store.get(batch_id).model_dump(mode="json")}

    @app.post("/api/batches", status_code=202, dependencies=[Depends(require_csrf)])
    def create_batch(request: BatchCreateRequest):
        if not request.consent_confirmed:
            raise StudioError(
                "CONSENT_REQUIRED",
                "Confirm that you are authorized to process every recording in this folder.",
            )
        if not _LANGUAGE.fullmatch(request.language):
            raise StudioError(
                "INVALID_LANGUAGE", "Choose auto-detect or a two-letter language code."
            )
        require_processing_ready()
        batch = batch_manager.create_batch(
            input_folder=request.input_folder,
            output_folder=request.output_folder,
            formats=request.formats,
            language=request.language,
        )
        return {"batch": batch.model_dump(mode="json")}

    @app.delete("/api/batches/{batch_id}", status_code=204, dependencies=[Depends(require_csrf)])
    def delete_batch(batch_id: str):
        batch_manager.delete_batch(batch_id)
        return Response(status_code=204)

    @app.post("/api/jobs", status_code=202, dependencies=[Depends(require_csrf)])
    async def create_job(
        file: UploadFile = File(...),
        language: str = Form("auto"),
        consent_confirmed: bool = Form(...),
    ):
        if not consent_confirmed:
            raise StudioError(
                "CONSENT_REQUIRED",
                "Confirm that you are authorized to process this recording.",
            )
        if not _LANGUAGE.fullmatch(language):
            raise StudioError(
                "INVALID_LANGUAGE", "Choose auto-detect or a two-letter language code."
            )
        require_processing_ready()
        display_name = validate_upload_metadata(file.filename, file.content_type)
        job = store.create_job(
            display_name=display_name,
            language=language,
            model_id=transcriber.model_id,
        )
        destination = store.source_path(job.id)
        total = 0
        try:
            with destination.open("xb") as handle:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.max_upload_bytes:
                        raise StudioError(
                            "UPLOAD_TOO_LARGE",
                            f"The file exceeds the {settings.max_upload_bytes // 1024**2:,} MB limit.",
                            http_status=413,
                        )
                    handle.write(chunk)
            if total == 0:
                raise StudioError("EMPTY_UPLOAD", "The selected MP4 file is empty.")
            store.update_job(job.id, size_bytes=total)
        except Exception:
            store.delete_job(job.id, reason="upload_rejected")
            raise
        finally:
            await file.close()
        active_processor.submit(job.id)
        return {"job": store.get_job(job.id).model_dump(mode="json")}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return {"job": store.get_job(job_id).model_dump(mode="json")}

    @app.get("/api/jobs/{job_id}/transcript")
    def get_transcript(job_id: str):
        store.get_job(job_id)
        return {"transcript": store.get_transcript(job_id).model_dump(mode="json")}

    @app.get("/api/jobs/{job_id}/analysis")
    def get_analysis(job_id: str):
        store.get_job(job_id)
        return {"analysis": store.get_analysis(job_id).model_dump(mode="json")}

    @app.get("/api/jobs/{job_id}/media")
    def get_media(job_id: str):
        job = store.get_job(job_id)
        source = store.source_path(job_id)
        if not source.is_file():
            raise StudioError(
                "MEDIA_NOT_FOUND", "The source media is unavailable.", http_status=404
            )
        return FileResponse(
            source,
            media_type="video/mp4",
            filename=job.display_name,
            content_disposition_type="inline",
        )

    @app.patch(
        "/api/jobs/{job_id}/transcript/segments/{segment_id}",
        status_code=200,
        dependencies=[Depends(require_csrf)],
    )
    def correct_segment(job_id: str, segment_id: int, body: TranscriptCorrectionRequest):
        job = store.get_job(job_id)
        if job.status != JobStatus.COMPLETE:
            raise StudioError(
                "JOB_NOT_COMPLETE",
                "Transcript corrections require a completed job.",
                http_status=409,
            )
        revision = store.apply_correction(job_id, segment_id, body.text, body.reason)
        return {"revision": revision.model_dump(mode="json")}

    @app.get("/api/jobs/{job_id}/transcript/revisions")
    def get_revisions(job_id: str):
        store.get_job(job_id)
        return {"revisions": [r.model_dump(mode="json") for r in store.get_revisions(job_id)]}

    @app.get("/api/jobs/{job_id}/export")
    def export_job(job_id: str, format: str = Query("txt")):
        job = store.get_job(job_id)
        body, media_type, extension = render_export(
            store.get_transcript(job_id), store.get_analysis(job_id), format
        )
        safe_base = safe_export_base(job.display_name)
        headers = {"Content-Disposition": f'attachment; filename="{safe_base}.{extension}"'}
        return Response(body.encode("utf-8"), media_type=media_type, headers=headers)

    @app.delete("/api/jobs/{job_id}", status_code=204, dependencies=[Depends(require_csrf)])
    def delete_job(job_id: str):
        job = store.get_job(job_id)
        if batch_manager.owns_job(job_id):
            raise StudioError(
                "JOB_MANAGED_BY_BATCH",
                "Remove this recording from its completed batch cleanup control.",
                http_status=409,
            )
        if job.status not in {JobStatus.COMPLETE, JobStatus.FAILED}:
            raise StudioError(
                "JOB_STILL_RUNNING",
                "Wait for processing to finish before deleting this recording.",
                http_status=409,
            )
        store.delete_job(job_id)
        return Response(status_code=204)

    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    return app
