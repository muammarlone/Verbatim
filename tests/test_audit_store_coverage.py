"""Additional coverage for audit_store.py — Fernet path, retention, provenance.

On Windows the code takes the DPAPI path. These tests force non-Windows mode
via platform.system mock so the Fernet and plaintext paths can be exercised
on any OS without touching real DPAPI or requiring the cryptography package
to be absent.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from secure_transcribe.audit_store import AuditStore

_DEV_KEY = os.urandom(32).hex()  # valid 32-byte hex key, re-used across tests


def _source_kwargs(job_id: str) -> dict:
    return {
        "source_hash": hashlib.sha256(f"{job_id}.mp4".encode()).hexdigest(),
        "size_bytes": 1024,
        "format": "mp4",
        "duration_seconds": 10.5,
    }


def _non_windows_store(tmp_path: Path, *, dev_key: str | None = _DEV_KEY) -> AuditStore:
    """Return an AuditStore forced into non-Windows mode."""
    env_patch = {k: v for k, v in {"STS_AUDIT_DEV_KEY": dev_key}.items() if v is not None}
    with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
        with patch.dict(os.environ, env_patch, clear=False):
            return AuditStore(tmp_path)


# ---------------------------------------------------------------------------
# Fernet encryption path
# ---------------------------------------------------------------------------


class TestFernetPath:
    def test_fernet_write_and_read(self, tmp_path: Path) -> None:
        env = {"STS_AUDIT_DEV_KEY": _DEV_KEY}
        with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
            with patch.dict(os.environ, env):
                store = AuditStore(tmp_path)
                store.write_source("fernet-j1", **_source_kwargs("fernet-j1"))
                records = store.read_provenance("fernet-j1")
        assert len(records) == 1
        assert records[0]["record_type"] == "source"
        assert records[0]["job_id"] == "fernet-j1"

    def test_fernet_file_is_not_plaintext(self, tmp_path: Path) -> None:
        env = {"STS_AUDIT_DEV_KEY": _DEV_KEY}
        with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
            with patch.dict(os.environ, env):
                store = AuditStore(tmp_path)
                store.write_source("fernet-j2", **_source_kwargs("fernet-j2"))
        # Raw file bytes must not contain readable JSON
        raw = (tmp_path / "fernet-j2.audit.ndjson").read_bytes()
        assert b"record_type" not in raw

    def test_fernet_multiple_records(self, tmp_path: Path) -> None:
        env = {"STS_AUDIT_DEV_KEY": _DEV_KEY}
        with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
            with patch.dict(os.environ, env):
                store = AuditStore(tmp_path)
                job = "fernet-multi"
                store.write_source(job, **_source_kwargs(job))
                store.write_extraction(
                    job,
                    ffmpeg_version="5.1",
                    params_hash=hashlib.sha256(b"p").hexdigest(),
                    output_hash=hashlib.sha256(b"o").hexdigest(),
                )
                records = store.read_provenance(job)
        assert len(records) == 2
        types = [r["record_type"] for r in records]
        assert "source" in types
        assert "extraction" in types

    def test_fernet_invalid_key_raises_on_write(self, tmp_path: Path) -> None:
        env = {"STS_AUDIT_DEV_KEY": "not-hex"}
        with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
            with patch.dict(os.environ, env):
                store = AuditStore(tmp_path)
                with pytest.raises(Exception):
                    store.write_source("bad-key-job", **_source_kwargs("bad-key-job"))

    def test_plaintext_dev_mode_readable(self, tmp_path: Path) -> None:
        """No STS_AUDIT_DEV_KEY + non-Windows = plaintext mode."""
        with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
            # Ensure key is not set
            env_without_key = {k: v for k, v in os.environ.items() if k != "STS_AUDIT_DEV_KEY"}
            with patch.dict(os.environ, env_without_key, clear=True):
                store = AuditStore(tmp_path)
                store.write_source("plain-j1", **_source_kwargs("plain-j1"))
                records = store.read_provenance("plain-j1")
        assert len(records) == 1
        assert records[0]["record_type"] == "source"

    def test_fernet_key_never_logged(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        env = {"STS_AUDIT_DEV_KEY": _DEV_KEY}
        with caplog.at_level(logging.DEBUG):
            with patch("secure_transcribe.audit_store.platform.system", return_value="Linux"):
                with patch.dict(os.environ, env):
                    store = AuditStore(tmp_path)
                    store.write_source("log-check", **_source_kwargs("log-check"))
        assert _DEV_KEY not in caplog.text


# ---------------------------------------------------------------------------
# retention_floor_reached
# ---------------------------------------------------------------------------


class TestRetentionFloor:
    def test_floor_not_reached_for_fresh_file(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        store.write_source("ret-fresh", **_source_kwargs("ret-fresh"))
        # Fresh file: 0 days old — 7 day floor not reached
        assert store.retention_floor_reached("ret-fresh", min_days=7) is False

    def test_floor_reached_when_mtime_old(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        store.write_source("ret-old", **_source_kwargs("ret-old"))
        tree_file = tmp_path / "ret-old.audit.ndjson"
        # Back-date mtime by 8 days
        old_time = time.time() - 8 * 86_400
        os.utime(tree_file, (old_time, old_time))
        assert store.retention_floor_reached("ret-old", min_days=7) is True

    def test_floor_false_for_missing_job(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        assert store.retention_floor_reached("ghost", min_days=0) is False

    def test_floor_exactly_at_boundary(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        store.write_source("ret-edge", **_source_kwargs("ret-edge"))
        tree_file = tmp_path / "ret-edge.audit.ndjson"
        # Exactly 7 days minus 1 second — not reached
        almost_7_days = time.time() - (7 * 86_400 - 1)
        os.utime(tree_file, (almost_7_days, almost_7_days))
        assert store.retention_floor_reached("ret-edge", min_days=7) is False


# ---------------------------------------------------------------------------
# read_provenance
# ---------------------------------------------------------------------------


class TestReadProvenance:
    def test_returns_empty_list_for_missing_job(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        result = store.read_provenance("ghost-job")
        assert result == []

    def test_returns_all_record_types(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        job = "prov-all"
        store.write_source(job, **_source_kwargs(job))
        store.write_extraction(
            job,
            ffmpeg_version="5.1",
            params_hash=hashlib.sha256(b"params").hexdigest(),
            output_hash=hashlib.sha256(b"output").hexdigest(),
        )
        store.write_transcription(
            job,
            model_id="base",
            model_hash=hashlib.sha256(b"model").hexdigest(),
            language="en",
            params_hash=hashlib.sha256(b"tp").hexdigest(),
            segment_count=3,
        )
        records = store.read_provenance(job)
        types = {r["record_type"] for r in records}
        assert types == {"source", "extraction", "transcription"}

    def test_provenance_records_have_purpose_field(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        store.write_source("prov-purpose", **_source_kwargs("prov-purpose"))
        records = store.read_provenance("prov-purpose")
        assert all(r.get("purpose") == "audit_only" for r in records)

    def test_provenance_raises_on_tampered_hmac(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        job = "prov-tamper"
        store.write_source(job, **_source_kwargs(job))
        # Decrypt, corrupt one byte, re-encrypt without HMAC check
        tree_file = tmp_path / f"{job}.audit.ndjson"
        raw_plaintext = store._decrypt(tree_file.read_bytes())
        # Flip a character in the HMAC field
        corrupted = raw_plaintext[:-5] + b"XXXXX"
        tree_file.write_bytes(store._encrypt(corrupted))
        with pytest.raises((ValueError, Exception)):
            store.read_provenance(job)


# ---------------------------------------------------------------------------
# tree_exists
# ---------------------------------------------------------------------------


class TestTreeExists:
    def test_exists_after_first_write(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        assert store.tree_exists("no-write") is False
        store.write_source("no-write", **_source_kwargs("no-write"))
        assert store.tree_exists("no-write") is True

    def test_not_exists_for_unknown(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        assert store.tree_exists("ghost") is False


# ---------------------------------------------------------------------------
# HMAC integrity
# ---------------------------------------------------------------------------


class TestHmacIntegrity:
    def test_hmac_tag_absent_raises_on_read(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        job = "no-hmac-job"
        store.write_source(job, **_source_kwargs(job))
        # Write a record without _hmac directly to the encrypted blob
        tree_file = tmp_path / f"{job}.audit.ndjson"
        import json as _json
        raw = store._decrypt(tree_file.read_bytes())
        lines = [l for l in raw.decode().splitlines() if l.strip()]
        # Replace first line with a version that has no _hmac
        rec = _json.loads(lines[0])
        rec.pop("_hmac", None)
        bad_line = _json.dumps(rec) + "\n"
        tree_file.write_bytes(store._encrypt(bad_line.encode()))
        with pytest.raises(ValueError, match="_hmac"):
            store.read_provenance(job)

    def test_records_verified_by_default_hmac_key(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        store.write_source("hmac-ok", **_source_kwargs("hmac-ok"))
        records = store.read_provenance("hmac-ok")
        assert len(records) == 1

    def test_all_write_methods_produce_readable_records(self, tmp_path: Path) -> None:
        store = _non_windows_store(tmp_path)
        job = "all-writes"
        fh = hashlib.sha256(b"f.mp4").hexdigest()
        store.write_source(job, source_hash=fh, size_bytes=512, format="mp4", duration_seconds=5.0)
        store.write_extraction(
            job, ffmpeg_version="5.1", params_hash=fh, output_hash=fh
        )
        store.write_transcription(
            job, model_id="base", model_hash=fh, language="en", params_hash=fh, segment_count=2
        )
        store.write_segment(
            job, index=0, start_ms=0, end_ms=3000, text_hash=fh, avg_logprob=-0.1, no_speech_prob=0.01
        )
        store.write_revision(
            job, revision_id="r1", segment_index=0, operation="replace",
            original_hash=fh, corrected_hash=fh
        )
        store.write_export(job, format="txt", destination_scope="local", content_hash=fh)
        store.write_deletion(job, scope="job", surviving_artifacts=["audit"])
        records = store.read_provenance(job)
        assert len(records) == 7
        types = {r["record_type"] for r in records}
        expected = {"source", "extraction", "transcription", "segment", "revision", "export", "deletion"}
        assert types == expected
