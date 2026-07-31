from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    model_path: Path
    batch_root: Path | None = None
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024
    max_batch_bytes: int = 10 * 1024 * 1024 * 1024
    max_batch_files: int = 25
    max_media_seconds: int = 4 * 60 * 60
    ffmpeg_timeout_seconds: int = 2 * 60 * 60
    transcription_timeout_seconds: int = 2 * 60 * 60
    retention_days: int = 7
    max_jobs: int = 100
    manifest_intake_enabled: bool = False
    protected_archive_enabled: bool = False
    zoom_connector_enabled: bool = False
    max_manifest_bytes: int = 5 * 1024 * 1024
    import_plan_ttl_seconds: int = 30 * 60
    max_import_plans: int = 100
    app_version: str = "0.2.0"
    audit_tree_dir: Path | None = None
    audit_min_retention_days: int = 365
    audit_query_enabled: bool = False

    def __post_init__(self) -> None:
        if self.max_batch_files > 25:
            raise ValueError("max_batch_files cannot exceed the governed 25-file limit")
        if not 64 * 1024 <= self.max_manifest_bytes <= 5 * 1024**2:
            raise ValueError("max_manifest_bytes must remain between 64 KiB and 5 MiB")
        if not 60 <= self.import_plan_ttl_seconds <= 1_800:
            raise ValueError("import_plan_ttl_seconds must remain between 60 and 1800")
        if not 1 <= self.max_import_plans <= 1_000:
            raise ValueError("max_import_plans must remain between 1 and 1000")
        if self.protected_archive_enabled or self.zoom_connector_enabled:
            raise ValueError(
                "protected archive and Zoom flags cannot be enabled before their gates ship"
            )
        if not 1 <= self.audit_min_retention_days <= 2555:
            raise ValueError("audit_min_retention_days must be between 1 and 2555")

    @property
    def batch_workspace(self) -> Path:
        return (self.batch_root or (self.data_dir / "batch-workspace")).resolve()

    @property
    def effective_audit_tree_dir(self) -> Path:
        return self.audit_tree_dir or (self.data_dir / "audit-tree")

    @classmethod
    def from_env(cls) -> "Settings":
        default_data = Path.cwd() / "data"
        default_model = Path.home() / ".cache" / "whisper" / "base.pt"
        return cls(
            data_dir=Path(os.getenv("STS_DATA_DIR", default_data)).expanduser().resolve(),
            model_path=Path(os.getenv("STS_MODEL_PATH", default_model)).expanduser().resolve(),
            batch_root=(
                Path(os.environ["STS_BATCH_ROOT"]).expanduser().resolve()
                if os.getenv("STS_BATCH_ROOT")
                else None
            ),
            max_upload_bytes=_env_int("STS_MAX_UPLOAD_BYTES", 2 * 1024**3, 1024**2, 20 * 1024**3),
            max_media_seconds=_env_int("STS_MAX_MEDIA_SECONDS", 14_400, 60, 86_400),
            max_batch_bytes=_env_int("STS_MAX_BATCH_BYTES", 10 * 1024**3, 1024**2, 100 * 1024**3),
            max_batch_files=_env_int("STS_MAX_BATCH_FILES", 25, 1, 25),
            ffmpeg_timeout_seconds=_env_int("STS_FFMPEG_TIMEOUT_SECONDS", 7_200, 30, 86_400),
            transcription_timeout_seconds=_env_int(
                "STS_TRANSCRIPTION_TIMEOUT_SECONDS", 7_200, 30, 86_400
            ),
            retention_days=_env_int("STS_RETENTION_DAYS", 7, 1, 365),
            max_jobs=_env_int("STS_MAX_JOBS", 100, 1, 10_000),
            manifest_intake_enabled=_env_bool("STS_MANIFEST_INTAKE_ENABLED"),
            protected_archive_enabled=_env_bool("STS_PROTECTED_ARCHIVE_ENABLED"),
            zoom_connector_enabled=_env_bool("STS_ZOOM_CONNECTOR_ENABLED"),
            max_manifest_bytes=_env_int(
                "STS_MAX_MANIFEST_BYTES", 5 * 1024**2, 64 * 1024, 5 * 1024**2
            ),
            import_plan_ttl_seconds=_env_int(
                "STS_IMPORT_PLAN_TTL_SECONDS", 1_800, 60, 1_800
            ),
            max_import_plans=_env_int("STS_MAX_IMPORT_PLANS", 100, 1, 1_000),
            audit_tree_dir=(
                Path(os.environ["STS_AUDIT_TREE_DIR"]).expanduser().resolve()
                if os.getenv("STS_AUDIT_TREE_DIR")
                else None
            ),
            audit_min_retention_days=_env_int("STS_AUDIT_MIN_RETENTION_DAYS", 365, 1, 2555),
            audit_query_enabled=_env_bool("STS_AUDIT_QUERY_ENABLED", False),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "jobs").mkdir(exist_ok=True)
        (self.data_dir / "audit").mkdir(exist_ok=True)
        (self.data_dir / "batches").mkdir(exist_ok=True)
        self.batch_workspace.mkdir(parents=True, exist_ok=True)
        self.effective_audit_tree_dir.mkdir(parents=True, exist_ok=True)
