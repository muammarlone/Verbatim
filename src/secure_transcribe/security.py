from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .errors import StudioError

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_ALLOWED_MIME_TYPES = {"video/mp4", "application/mp4", "application/octet-stream"}


def sanitize_display_name(name: str | None) -> str:
    candidate = Path(name or "recording.mp4").name
    candidate = _CONTROL_CHARACTERS.sub("", candidate).strip()
    if not candidate:
        candidate = "recording.mp4"
    return candidate[:180]


def validate_upload_metadata(filename: str | None, content_type: str | None) -> str:
    display_name = sanitize_display_name(filename)
    if Path(display_name).suffix.lower() != ".mp4":
        raise StudioError("UNSUPPORTED_EXTENSION", "Select an MP4 video file.")
    if content_type and content_type.lower() not in _ALLOWED_MIME_TYPES:
        raise StudioError("UNSUPPORTED_MEDIA_TYPE", "The uploaded file is not an MP4 video.")
    return display_name


def validate_mp4_signature(path: Path) -> None:
    with path.open("rb") as handle:
        header = handle.read(64)
    if len(header) < 12 or header[4:8] != b"ftyp":
        raise StudioError("INVALID_MP4_SIGNATURE", "The file does not have a valid MP4 signature.")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_loopback_host(host: str) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise StudioError(
            "NON_LOOPBACK_BIND_BLOCKED",
            "Secure Transcription Studio may only bind to the local machine.",
        )
