from __future__ import annotations

import os
from pathlib import Path

import pytest

from secure_transcribe.batch import BatchManager, BatchStore, discover_workspace_folders, resolve_workspace_folder
from secure_transcribe.config import Settings
from secure_transcribe.errors import StudioError
from secure_transcribe.models import BatchRecord, BatchStatus, utc_now
from secure_transcribe.storage import JobStore


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


def _make_batch_record(batch_id: str, *, status: BatchStatus = BatchStatus.QUEUED) -> BatchRecord:
    now = utc_now()
    return BatchRecord(
        id=batch_id,
        status=status,
        created_at=now,
        updated_at=now,
        input_folder="in",
        output_folder="out",
        formats=["txt"],
        language_requested="auto",
        total_files=0,
        completed_files=0,
        failed_files=0,
        total_bytes=0,
        items=[],
    )


def test_resolve_workspace_folder_rejects_invalid_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "sub").mkdir()
    # Empty string rejected
    with pytest.raises(StudioError) as exc:
        resolve_workspace_folder(workspace, "")
    assert exc.value.code == "INVALID_BATCH_FOLDER"
    # Dotdot traversal rejected (the ".." part hits the parts check)
    with pytest.raises(StudioError) as exc2:
        resolve_workspace_folder(workspace, "../outside")
    assert exc2.value.code == "INVALID_BATCH_FOLDER"
    # Workspace root itself (no sub-path) rejected as outside root
    with pytest.raises(StudioError) as exc3:
        resolve_workspace_folder(workspace, ".")
    assert exc3.value.code in {"INVALID_BATCH_FOLDER", "BATCH_PATH_OUTSIDE_ROOT"}


def test_resolve_workspace_folder_missing_dir_raises(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    with pytest.raises(StudioError) as exc:
        resolve_workspace_folder(workspace, "nonexistent")
    assert exc.value.code == "BATCH_FOLDER_NOT_FOUND"


def test_discover_workspace_folders_lists_only_real_dirs(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "alpha").mkdir()
    (ws / "beta").mkdir()
    (ws / ".hidden").mkdir()
    (ws / "file.txt").write_text("x")
    result = discover_workspace_folders(ws)
    assert result == ["alpha", "beta"]


def test_batch_store_get_raises_on_missing(tmp_path: Path) -> None:
    from secure_transcribe.errors import BatchNotFoundError
    store = BatchStore(tmp_path)
    with pytest.raises(BatchNotFoundError):
        store.get("00000000-0000-0000-0000-000000000099")


def test_batch_store_list_skips_corrupt_entries(tmp_path: Path) -> None:
    store = BatchStore(tmp_path)
    import uuid
    bid = str(uuid.uuid4())
    (tmp_path / bid).mkdir()
    (tmp_path / bid / "batch.json").write_text("not json")
    result = store.list()
    assert all(r.id != bid for r in result)


def test_delete_batch_raises_when_still_running(tmp_path: Path) -> None:
    import uuid

    class _FakeProcessor:
        def submit(self, job_id: str) -> None: ...
        def cancel(self, job_id: str) -> None: ...

    settings = Settings(data_dir=tmp_path, model_path=tmp_path / "model.pt")
    job_store = JobStore(tmp_path)
    batch_store = BatchStore(tmp_path)
    manager = BatchManager.__new__(BatchManager)
    manager.store = job_store
    manager.batch_store = batch_store
    manager.settings = settings
    manager.processor = _FakeProcessor()
    manager._lock = __import__("threading").Lock()
    manager._monitored = set()
    manager._monitor_futures = {}
    manager.executor = __import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor(max_workers=1)
    manager.model_id = "fixture:v1"
    manager._shutdown = __import__("threading").Event()

    bid = str(uuid.uuid4())
    record = _make_batch_record(bid, status=BatchStatus.RUNNING)
    batch_store.create(record)

    with pytest.raises(StudioError) as exc:
        manager.delete_batch(bid)
    assert exc.value.code == "BATCH_STILL_RUNNING"
    manager.executor.shutdown(wait=False)


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
