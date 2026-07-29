from __future__ import annotations

import os
from pathlib import Path

import pytest

from secure_transcribe.batch import BatchManager
from secure_transcribe.errors import StudioError


def test_output_publish_failure_leaves_no_partial_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "transcript.txt"
    manager = object.__new__(BatchManager)

    def fail_link(*_):
        raise OSError("simulated publish failure")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(StudioError) as exc:
        manager._write_output(target, "approved transcript\n")

    assert exc.value.code == "OUTPUT_WRITE_FAILED"
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_output_publish_is_idempotent_and_never_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "transcript.txt"
    manager = object.__new__(BatchManager)

    manager._write_output(target, "approved transcript\n")
    manager._write_output(target, "approved transcript\n")
    assert target.read_text(encoding="utf-8") == "approved transcript\n"

    with pytest.raises(StudioError) as exc:
        manager._write_output(target, "replacement\n")
    assert exc.value.code == "OUTPUT_EXISTS"
    assert target.read_text(encoding="utf-8") == "approved transcript\n"
