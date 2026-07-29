from pathlib import Path

import pytest

from secure_transcribe.errors import StudioError
from secure_transcribe.security import (
    require_loopback_host,
    sanitize_display_name,
    validate_mp4_signature,
    validate_upload_metadata,
)


def test_display_name_removes_paths_and_control_characters() -> None:
    assert sanitize_display_name("../../board\x00 meeting.mp4") == "board meeting.mp4"
    assert sanitize_display_name("C:\\secret\\review.mp4") == "review.mp4"


def test_upload_metadata_rejects_non_mp4() -> None:
    with pytest.raises(StudioError, match="Select an MP4"):
        validate_upload_metadata("notes.txt", "text/plain")


def test_mp4_signature_is_checked(tmp_path: Path) -> None:
    valid = tmp_path / "valid.mp4"
    valid.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom")
    validate_mp4_signature(valid)
    invalid = tmp_path / "invalid.mp4"
    invalid.write_bytes(b"not an mp4")
    with pytest.raises(StudioError) as exc:
        validate_mp4_signature(invalid)
    assert exc.value.code == "INVALID_MP4_SIGNATURE"


def test_non_loopback_bind_is_blocked() -> None:
    require_loopback_host("127.0.0.1")
    with pytest.raises(StudioError) as exc:
        require_loopback_host("0.0.0.0")
    assert exc.value.code == "NON_LOOPBACK_BIND_BLOCKED"
