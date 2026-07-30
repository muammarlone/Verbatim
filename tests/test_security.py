from pathlib import Path

import pytest

from secure_transcribe.errors import StudioError
from secure_transcribe.security import (
    SUPPORTED_MEDIA_EXTENSIONS,
    require_loopback_host,
    sanitize_display_name,
    validate_media_signature,
    validate_mp4_signature,
    validate_upload_metadata,
)


def test_display_name_removes_paths_and_control_characters() -> None:
    assert sanitize_display_name("../../board\x00 meeting.mp4") == "board meeting.mp4"
    assert sanitize_display_name("C:\\secret\\review.mp4") == "review.mp4"


def test_upload_metadata_accepts_mp4() -> None:
    assert validate_upload_metadata("meeting.mp4", "video/mp4") == "meeting.mp4"


def test_upload_metadata_accepts_m4a() -> None:
    assert validate_upload_metadata("recording.m4a", "audio/x-m4a") == "recording.m4a"


def test_upload_metadata_accepts_mp3() -> None:
    assert validate_upload_metadata("podcast.mp3", "audio/mpeg") == "podcast.mp3"


def test_upload_metadata_accepts_wav() -> None:
    assert validate_upload_metadata("interview.wav", "audio/wav") == "interview.wav"


def test_upload_metadata_accepts_flac() -> None:
    assert validate_upload_metadata("archive.flac", "audio/flac") == "archive.flac"


def test_upload_metadata_accepts_ogg() -> None:
    assert validate_upload_metadata("session.ogg", "audio/ogg") == "session.ogg"


def test_upload_metadata_accepts_octet_stream_mime() -> None:
    # Browsers often send this when the MIME type is unknown
    assert validate_upload_metadata("recording.m4a", "application/octet-stream") == "recording.m4a"


def test_upload_metadata_rejects_unsupported_extension() -> None:
    with pytest.raises(StudioError) as exc:
        validate_upload_metadata("notes.txt", "text/plain")
    assert exc.value.code == "UNSUPPORTED_EXTENSION"


def test_upload_metadata_rejects_pdf() -> None:
    with pytest.raises(StudioError) as exc:
        validate_upload_metadata("report.pdf", "application/pdf")
    assert exc.value.code == "UNSUPPORTED_EXTENSION"


def test_upload_metadata_rejects_unsupported_mime_for_mp4() -> None:
    with pytest.raises(StudioError) as exc:
        validate_upload_metadata("meeting.mp4", "text/html")
    assert exc.value.code == "UNSUPPORTED_MEDIA_TYPE"


def test_supported_extensions_constant_covers_required_formats() -> None:
    for ext in (".mp4", ".m4a", ".mp3", ".wav"):
        assert ext in SUPPORTED_MEDIA_EXTENSIONS


# ---------- signature validation ----------

def test_mp4_signature_is_checked(tmp_path: Path) -> None:
    valid = tmp_path / "valid.mp4"
    valid.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")
    validate_mp4_signature(valid)
    validate_media_signature(valid)
    invalid = tmp_path / "invalid.mp4"
    invalid.write_bytes(b"not an mp4")
    with pytest.raises(StudioError) as exc:
        validate_mp4_signature(invalid)
    assert exc.value.code == "INVALID_MP4_SIGNATURE"
    with pytest.raises(StudioError) as exc2:
        validate_media_signature(invalid)
    assert exc2.value.code == "INVALID_MEDIA_SIGNATURE"


def test_m4a_signature_valid(tmp_path: Path) -> None:
    # M4A uses the same ftyp box as MP4
    valid = tmp_path / "valid.m4a"
    valid.write_bytes(b"\x00\x00\x00\x1cftypM4A \x00\x00\x00\x00M4A mp42")
    validate_media_signature(valid)


def test_m4a_signature_invalid(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.m4a"
    invalid.write_bytes(b"RIFF" + b"\x00" * 20)
    with pytest.raises(StudioError) as exc:
        validate_media_signature(invalid)
    assert exc.value.code == "INVALID_MEDIA_SIGNATURE"


def test_wav_signature_valid(tmp_path: Path) -> None:
    valid = tmp_path / "valid.wav"
    valid.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    validate_media_signature(valid)


def test_wav_signature_invalid(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.wav"
    invalid.write_bytes(b"\x00\x00\x00\x18ftypisom")
    with pytest.raises(StudioError) as exc:
        validate_media_signature(invalid)
    assert exc.value.code == "INVALID_MEDIA_SIGNATURE"


def test_mp3_signature_valid_id3(tmp_path: Path) -> None:
    valid = tmp_path / "valid.mp3"
    valid.write_bytes(b"ID3\x03\x00\x00" + b"\x00" * 58)
    validate_media_signature(valid)


def test_mp3_signature_valid_sync_word(tmp_path: Path) -> None:
    # MPEG sync: 0xFF 0xFB (MPEG1 Layer3 CBR)
    valid = tmp_path / "valid2.mp3"
    valid.write_bytes(b"\xFF\xFB" + b"\x00" * 62)
    validate_media_signature(valid)


def test_mp3_signature_invalid(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.mp3"
    invalid.write_bytes(b"not mp3 content here at all")
    with pytest.raises(StudioError) as exc:
        validate_media_signature(invalid)
    assert exc.value.code == "INVALID_MEDIA_SIGNATURE"


def test_flac_signature_valid(tmp_path: Path) -> None:
    valid = tmp_path / "valid.flac"
    valid.write_bytes(b"fLaC" + b"\x00" * 60)
    validate_media_signature(valid)


def test_flac_signature_invalid(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.flac"
    invalid.write_bytes(b"RIFF" + b"\x00" * 60)
    with pytest.raises(StudioError) as exc:
        validate_media_signature(invalid)
    assert exc.value.code == "INVALID_MEDIA_SIGNATURE"


def test_ogg_signature_valid(tmp_path: Path) -> None:
    valid = tmp_path / "valid.ogg"
    valid.write_bytes(b"OggS" + b"\x00" * 60)
    validate_media_signature(valid)


def test_ogg_signature_invalid(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.ogg"
    invalid.write_bytes(b"\x00\x00\x00\x00" + b"\x00" * 60)
    with pytest.raises(StudioError) as exc:
        validate_media_signature(invalid)
    assert exc.value.code == "INVALID_MEDIA_SIGNATURE"


def test_non_loopback_bind_is_blocked() -> None:
    require_loopback_host("127.0.0.1")
    with pytest.raises(StudioError) as exc:
        require_loopback_host("0.0.0.0")
    assert exc.value.code == "NON_LOOPBACK_BIND_BLOCKED"
