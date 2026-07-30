from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .errors import StudioError

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")

SUPPORTED_MEDIA_EXTENSIONS = frozenset({
    ".mp4", ".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma",
})

_ALLOWED_MIME_TYPES = frozenset({
    # MP4 video / audio containers (M4A is MP4 with audio-only)
    "video/mp4", "application/mp4", "audio/mp4", "audio/m4a", "audio/x-m4a",
    # MP3
    "audio/mpeg", "audio/mp3",
    # WAV
    "audio/wav", "audio/wave", "audio/x-wav",
    # AAC
    "audio/aac", "audio/x-aac",
    # FLAC
    "audio/flac", "audio/x-flac",
    # OGG
    "audio/ogg", "application/ogg",
    # WMA
    "audio/x-ms-wma",
    # Generic — browsers send this when they don't know the type
    "application/octet-stream",
})

_EXT_LABEL = {
    ".mp4": "MP4",  ".m4a": "M4A",  ".mp3": "MP3",
    ".wav": "WAV",  ".aac": "AAC",  ".flac": "FLAC",
    ".ogg": "OGG",  ".wma": "WMA",
}


def sanitize_display_name(name: str | None) -> str:
    candidate = Path(name or "recording.mp4").name
    candidate = _CONTROL_CHARACTERS.sub("", candidate).strip()
    if not candidate:
        candidate = "recording.mp4"
    return candidate[:180]


def validate_upload_metadata(filename: str | None, content_type: str | None) -> str:
    display_name = sanitize_display_name(filename)
    ext = Path(display_name).suffix.lower()
    if ext not in SUPPORTED_MEDIA_EXTENSIONS:
        supported = ", ".join(sorted(e.lstrip(".").upper() for e in SUPPORTED_MEDIA_EXTENSIONS))
        raise StudioError(
            "UNSUPPORTED_EXTENSION",
            f"Select an MP4, M4A, MP3, WAV, AAC, FLAC, OGG, or WMA file. Supported: {supported}.",
        )
    mime = (content_type or "").lower().split(";")[0].strip()
    if mime and mime not in _ALLOWED_MIME_TYPES:
        raise StudioError("UNSUPPORTED_MEDIA_TYPE", "The uploaded file type is not supported.")
    return display_name


def validate_mp4_signature(path: Path) -> None:
    """Legacy: validates MP4/M4A ftyp box. Use validate_media_signature for all formats."""
    with path.open("rb") as handle:
        header = handle.read(64)
    if len(header) < 12 or header[4:8] != b"ftyp":
        raise StudioError("INVALID_MP4_SIGNATURE", "The file does not have a valid MP4 signature.")


def validate_media_signature(path: Path) -> None:
    with path.open("rb") as handle:
        header = handle.read(64)
    ext = path.suffix.lower()
    if ext in {".mp4", ".m4a"}:
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise StudioError(
                "INVALID_MEDIA_SIGNATURE",
                f"The file does not have a valid {_EXT_LABEL.get(ext, 'MP4/M4A')} signature.",
            )
    elif ext == ".wav":
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise StudioError("INVALID_MEDIA_SIGNATURE", "The file does not have a valid WAV signature.")
    elif ext == ".mp3":
        # Accept ID3-tagged MP3s or MPEG sync-word frames (0xFF 0xEx or 0xFF 0xFx)
        if len(header) < 3 or (
            header[:3] != b"ID3"
            and not (header[0] == 0xFF and (header[1] & 0xE0) == 0xE0)
        ):
            raise StudioError("INVALID_MEDIA_SIGNATURE", "The file does not have a valid MP3 signature.")
    elif ext == ".flac":
        if len(header) < 4 or header[:4] != b"fLaC":
            raise StudioError("INVALID_MEDIA_SIGNATURE", "The file does not have a valid FLAC signature.")
    elif ext == ".ogg":
        if len(header) < 4 or header[:4] != b"OggS":
            raise StudioError("INVALID_MEDIA_SIGNATURE", "The file does not have a valid OGG signature.")
    # AAC and WMA have complex/variable headers — defer to FFprobe validation


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
