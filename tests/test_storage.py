from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from secure_transcribe.errors import NotFoundError, StudioError
from secure_transcribe.models import utc_now
from secure_transcribe.storage import JobStore


def create_job(store: JobStore, name: str = "meeting.mp4"):
    return store.create_job(display_name=name, language="auto", model_id="fixture:v1")


def test_store_capacity_and_uuid_boundary(tmp_path: Path) -> None:
    store = JobStore(tmp_path, max_jobs=1)
    created = create_job(store)
    assert store.has_job(created.id)
    assert not store.has_job("../../outside")

    with pytest.raises(NotFoundError):
        store.get_job("../../outside")
    with pytest.raises(StudioError) as capacity:
        create_job(store, "second.mp4")
    assert capacity.value.code == "JOB_CAPACITY_REACHED"
    with pytest.raises(StudioError) as invalid_request:
        store.ensure_capacity(0)
    assert invalid_request.value.code == "JOB_CAPACITY_REACHED"


def test_retention_removes_only_expired_jobs(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    expired = create_job(store, "expired.mp4")
    current = create_job(store, "current.mp4")
    store.update_job(expired.id, created_at=utc_now() - timedelta(days=8))

    assert store.sweep_expired(7) == 1
    assert not store.has_job(expired.id)
    assert store.has_job(current.id)

    events = [
        json.loads(line)
        for line in (tmp_path / "audit" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    deletion = next(event for event in events if event["event"] == "job_deleted")
    assert deletion["job_id"] == expired.id
    assert deletion["details"]["reason"] == "retention_expired"


def test_corrupt_job_record_is_excluded_without_hiding_valid_jobs(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    valid = create_job(store)
    corrupt = tmp_path / "jobs" / "00000000-0000-0000-0000-000000000001"
    corrupt.mkdir()
    (corrupt / "job.json").write_text("not json", encoding="utf-8")

    assert [job.id for job in store.list_jobs()] == [valid.id]
