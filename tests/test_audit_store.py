"""Tests for AuditStore — encrypted append-only derivation tree.

STS-123 / ADR-007 / AUDIT_SINGLE_PURPOSE_PRINCIPLE.md
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from secure_transcribe.audit_store import AuditStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# 32 zero-bytes encoded as hex — used on non-Windows to select Fernet path.
# On Windows the DPAPI path is selected regardless; the env var is ignored.
TEST_HMAC_KEY = bytes(32)  # deterministic HMAC key for all tests


@pytest.fixture()
def audit_store(tmp_path: Path) -> AuditStore:
    """Return an AuditStore with a deterministic HMAC key for test isolation."""
    return AuditStore(tmp_path / "audit-tree", hmac_key=TEST_HMAC_KEY)


# Convenience: fake job id (AuditStore does not validate UUID format)
JOB = "test-job-001"

# ---------------------------------------------------------------------------
# Helper: write a source record (used in many tests)
# ---------------------------------------------------------------------------


def _write_source(store: AuditStore, job_id: str = JOB) -> None:
    store.write_source(
        job_id,
        source_hash="sha256:abc123",
        size_bytes=1_048_576,
        format="mp4",
        duration_seconds=120.5,
    )


# ---------------------------------------------------------------------------
# Test 1: write_source creates the encrypted tree file
# ---------------------------------------------------------------------------


def test_write_source_creates_encrypted_file(audit_store: AuditStore) -> None:
    assert not audit_store.tree_exists(JOB)
    _write_source(audit_store)
    assert audit_store.tree_exists(JOB)
    # The raw file must exist on disk
    assert audit_store._tree_path(JOB).is_file()


# ---------------------------------------------------------------------------
# Test 2: append-only — successive writes grow the provenance list
# ---------------------------------------------------------------------------


def test_append_only_records_grow(audit_store: AuditStore) -> None:
    _write_source(audit_store)
    audit_store.write_extraction(
        JOB,
        ffmpeg_version="6.0",
        params_hash="sha256:deadbeef",
        output_hash="sha256:cafebabe",
    )
    audit_store.write_transcription(
        JOB,
        model_id="openai-whisper:base",
        model_hash="sha256:modeldigest",
        language="en",
        params_hash="sha256:paramshash",
        segment_count=3,
    )
    records = audit_store.read_provenance(JOB)
    assert len(records) == 3
    assert records[0]["record_type"] == "source"
    assert records[1]["record_type"] == "extraction"
    assert records[2]["record_type"] == "transcription"


# ---------------------------------------------------------------------------
# Test 3: HMAC tampering raises ValueError on read
# ---------------------------------------------------------------------------


def test_hmac_verified_on_read(audit_store: AuditStore) -> None:
    _write_source(audit_store)
    path = audit_store._tree_path(JOB)

    # Decrypt, corrupt HMAC, re-encrypt
    raw = audit_store._decrypt(path.read_bytes())
    lines = raw.decode().splitlines()
    record = json.loads(lines[0])
    record["_hmac"] = "00" * 32  # garbage HMAC (64 hex chars)
    corrupted_line = (
        json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
    )
    path.write_bytes(audit_store._encrypt(corrupted_line.encode()))

    with pytest.raises(ValueError, match="HMAC"):
        audit_store.read_provenance(JOB)


# ---------------------------------------------------------------------------
# Test 4: every record carries purpose="audit_only"
# ---------------------------------------------------------------------------


def test_purpose_marker_on_every_record(audit_store: AuditStore) -> None:
    _write_source(audit_store)
    audit_store.write_extraction(
        JOB,
        ffmpeg_version="6.0",
        params_hash="sha256:p",
        output_hash="sha256:o",
    )
    records = audit_store.read_provenance(JOB)
    for record in records:
        assert record.get("purpose") == AuditStore.PURPOSE, (
            f"Record missing purpose marker: {record}"
        )


# ---------------------------------------------------------------------------
# Test 5: write_segment stores hash — never the raw text
# ---------------------------------------------------------------------------


def test_no_text_content_in_write_segment(audit_store: AuditStore) -> None:
    secret_text = "This transcript text must never appear in the audit file."
    text_hash = f"sha256:{hashlib.sha256(secret_text.encode()).hexdigest()}"
    audit_store.write_segment(
        JOB,
        index=0,
        start_ms=0,
        end_ms=5000,
        text_hash=text_hash,
        avg_logprob=-0.3,
        no_speech_prob=0.01,
    )
    # The raw file bytes (post-decrypt) must not contain the original text
    path = audit_store._tree_path(JOB)
    raw = audit_store._decrypt(path.read_bytes())
    assert secret_text.encode() not in raw

    # But the hash IS present
    assert text_hash.encode() in raw

    # And read_provenance returns the hash — not the text
    records = audit_store.read_provenance(JOB)
    assert len(records) == 1
    assert records[0]["text_hash"] == text_hash
    assert "text" not in records[0]


# ---------------------------------------------------------------------------
# Test 6: deletion record is written but tree file survives
# ---------------------------------------------------------------------------


def test_deletion_record_survives_when_tree_exists(audit_store: AuditStore) -> None:
    _write_source(audit_store)
    assert audit_store.tree_exists(JOB)

    audit_store.write_deletion(
        JOB,
        scope="managed_source_and_derived",
        surviving_artifacts=["audit_tree"],
    )

    # Tree file must still exist after writing a deletion record
    assert audit_store.tree_exists(JOB)

    records = audit_store.read_provenance(JOB)
    deletion_records = [r for r in records if r["record_type"] == "deletion"]
    assert len(deletion_records) == 1
    assert deletion_records[0]["surviving_artifacts"] == ["audit_tree"]


# ---------------------------------------------------------------------------
# Test 7: new file does not reach 365-day retention floor
# ---------------------------------------------------------------------------


def test_retention_floor_not_reached_for_new_file(audit_store: AuditStore) -> None:
    _write_source(audit_store)
    assert not audit_store.retention_floor_reached(JOB, min_days=365)


# ---------------------------------------------------------------------------
# Test 8: all seven record types round-trip through encrypt/decrypt + HMAC
# ---------------------------------------------------------------------------


def test_all_eight_record_types_round_trip(audit_store: AuditStore) -> None:
    """Write one record of each type and verify all survive the round-trip."""
    job = "round-trip-job"

    audit_store.write_source(
        job,
        source_hash="sha256:src",
        size_bytes=512,
        format="mp4",
        duration_seconds=30.0,
    )
    audit_store.write_extraction(
        job,
        ffmpeg_version="6.0",
        params_hash="sha256:ep",
        output_hash="sha256:eo",
    )
    audit_store.write_transcription(
        job,
        model_id="openai-whisper:base",
        model_hash="sha256:mh",
        language="en",
        params_hash="sha256:tp",
        segment_count=2,
    )
    audit_store.write_segment(
        job,
        index=0,
        start_ms=0,
        end_ms=2000,
        text_hash="sha256:seg0",
        avg_logprob=-0.2,
        no_speech_prob=0.05,
    )
    audit_store.write_revision(
        job,
        revision_id="rev-001",
        segment_index=0,
        operation="correct",
        original_hash="sha256:orig",
        corrected_hash="sha256:corr",
    )
    audit_store.write_export(
        job,
        format="txt",
        destination_scope="managed_export",
        content_hash="sha256:export",
    )
    audit_store.write_deletion(
        job,
        scope="managed_source_and_derived",
        surviving_artifacts=["audit_tree"],
    )

    records = audit_store.read_provenance(job)
    assert len(records) == 7

    expected_types = [
        "source",
        "extraction",
        "transcription",
        "segment",
        "revision",
        "export",
        "deletion",
    ]
    actual_types = [r["record_type"] for r in records]
    assert actual_types == expected_types


# ---------------------------------------------------------------------------
# Test 9: use_restriction on every record
# ---------------------------------------------------------------------------


def test_use_restriction_on_every_record(audit_store: AuditStore) -> None:
    _write_source(audit_store)
    audit_store.write_extraction(
        JOB,
        ffmpeg_version="6.0",
        params_hash="sha256:p",
        output_hash="sha256:o",
    )
    records = audit_store.read_provenance(JOB)
    for record in records:
        assert record.get("use_restriction") == AuditStore.USE_RESTRICTION, (
            f"Record missing use_restriction: {record}"
        )


# ---------------------------------------------------------------------------
# Test 10: write_revision appends, never overwrites
# ---------------------------------------------------------------------------


def test_write_revision_appends_not_overwrites(audit_store: AuditStore) -> None:
    audit_store.write_revision(
        JOB,
        revision_id="rev-001",
        segment_index=0,
        operation="correct",
        original_hash="sha256:orig1",
        corrected_hash="sha256:corr1",
    )
    audit_store.write_revision(
        JOB,
        revision_id="rev-002",
        segment_index=1,
        operation="correct",
        original_hash="sha256:orig2",
        corrected_hash="sha256:corr2",
    )

    records = audit_store.read_provenance(JOB)
    revision_records = [r for r in records if r["record_type"] == "revision"]
    assert len(revision_records) == 2
    assert revision_records[0]["revision_id"] == "rev-001"
    assert revision_records[1]["revision_id"] == "rev-002"
