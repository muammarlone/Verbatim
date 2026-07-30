from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class BatchStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class BatchItemStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    REJECTED = "rejected"


class ManifestSourceType(StrEnum):
    LOCAL_ARCHIVE = "local_archive"
    ZOOM_RECORDING = "zoom_recording"


class SecretProvider(StrEnum):
    NONE = "none"
    PROMPT = "prompt"
    WINDOWS_CREDENTIAL = "windows_credential"
    ZOOM_OAUTH = "zoom_oauth"


class JobError(BaseModel):
    code: str
    message: str


class JobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    size_bytes: int = Field(ge=0)
    language_requested: str = "auto"
    detected_language: str | None = None
    duration_seconds: float | None = None
    model_id: str
    source_sha256: str | None = None
    segment_count: int = 0
    error: JobError | None = None


class BatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str
    job_id: str | None = None
    status: BatchItemStatus
    outputs: list[str] = Field(default_factory=list)
    error: JobError | None = None


class BatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    id: str
    status: BatchStatus
    created_at: datetime
    updated_at: datetime
    input_folder: str
    output_folder: str
    formats: list[str]
    language_requested: str = "auto"
    total_files: int = Field(ge=0)
    completed_files: int = Field(ge=0)
    failed_files: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    manifest_name: str | None = None
    error: JobError | None = None
    items: list[BatchItem]


class BatchCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_folder: str = Field(min_length=1, max_length=240)
    output_folder: str = Field(min_length=1, max_length=240)
    formats: list[str] = Field(min_length=1, max_length=5)
    language: str = "auto"
    consent_confirmed: bool


class ImportPlanRow(BaseModel):
    """Internal normalized row. Never serialize this model into an API or audit response."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    row_id: str
    source_type: ManifestSourceType
    source_locator: str
    secret_ref: str = ""
    display_name: str
    expected_sha256: str | None = None


class ImportPlanPreviewRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: str
    source_type: ManifestSourceType
    source_locator: str
    secret_provider: SecretProvider
    secret_required: bool
    display_name: str
    expected_sha256: str | None = None


class ImportPlan(BaseModel):
    """Memory-only plan containing credential references but never credential values."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    id: str
    created_at: datetime
    expires_at: datetime
    manifest_sha256: str
    row_count: int = Field(ge=1, le=25)
    rows: list[ImportPlanRow]


class ImportPlanPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    plan_id: str
    created_at: datetime
    expires_at: datetime
    manifest_sha256: str
    row_count: int = Field(ge=1, le=25)
    rows: list[ImportPlanPreviewRow]


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str = Field(min_length=1, max_length=20_000)


class TranscriptDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    job_id: str
    language: str
    duration_seconds: float = Field(ge=0)
    model_id: str
    created_at: datetime
    segments: list[TranscriptSegment]
    text: str


class TermCount(BaseModel):
    term: str
    count: int = Field(ge=1)


class AnalysisItem(BaseModel):
    segment_id: int
    timestamp_seconds: float = Field(ge=0)
    text: str


class AnalysisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    job_id: str
    generated_at: datetime
    method: str = "deterministic-extractive-v1"
    word_count: int
    speaking_minutes: float
    words_per_minute: float
    top_terms: list[TermCount]
    key_moments: list[AnalysisItem]
    action_candidates: list[AnalysisItem]
    questions: list[AnalysisItem]
    limitations: list[str]


class HealthReport(BaseModel):
    status: str
    app_version: str
    ffmpeg_ready: bool
    ffprobe_ready: bool
    model_ready: bool
    model_id: str
    network_required: bool = False


class MediaProbe(BaseModel):
    duration_seconds: float = Field(gt=0)
    audio_codec: str
    video_codec: str | None = None
    format_name: str


class AuditEvent(BaseModel):
    timestamp: datetime
    event: str
    job_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
