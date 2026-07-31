"""Encrypted append-only audit store for transcript derivation trees.

Governed by:
  - governance/AUDIT_SINGLE_PURPOSE_PRINCIPLE.md
  - architecture/decisions/ADR-007-encrypted-audit-store.md

Purpose restriction: every record carries purpose="audit_only" and
use_restriction="authorized_audit_query_only".  Audit records must never
be returned by normal application paths.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
import hmac as hmac_mod
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# DPAPI helpers (Windows only)
# ---------------------------------------------------------------------------


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_protect(data: bytes) -> bytes:
    """Encrypt *data* using Windows DPAPI CryptProtectData (current-user key)."""
    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    buf = (ctypes.c_ubyte * len(data))(*data)
    blob_in = _DATA_BLOB(len(data), buf)
    blob_out = _DATA_BLOB()

    if not crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,  # szDataDescr
        None,  # pOptionalEntropy
        None,  # pvReserved
        None,  # pPromptStruct
        0,     # dwFlags — current-user key
        ctypes.byref(blob_out),
    ):
        raise RuntimeError(f"CryptProtectData failed: {ctypes.GetLastError()}")

    try:
        result = bytes(blob_out.pbData[: blob_out.cbData])
    finally:
        kernel32.LocalFree(blob_out.pbData)
    return result


def _dpapi_unprotect(data: bytes) -> bytes:
    """Decrypt *data* using Windows DPAPI CryptUnprotectData (current-user key)."""
    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    buf = (ctypes.c_ubyte * len(data))(*data)
    blob_in = _DATA_BLOB(len(data), buf)
    blob_out = _DATA_BLOB()

    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,  # pszDataDescr (out, optional)
        None,  # pOptionalEntropy
        None,  # pvReserved
        None,  # pPromptStruct
        0,     # dwFlags
        ctypes.byref(blob_out),
    ):
        raise RuntimeError(f"CryptUnprotectData failed: {ctypes.GetLastError()}")

    try:
        result = bytes(blob_out.pbData[: blob_out.cbData])
    finally:
        kernel32.LocalFree(blob_out.pbData)
    return result


# ---------------------------------------------------------------------------
# Fernet helpers (non-Windows dev/test)
# ---------------------------------------------------------------------------


def _fernet_encrypt(data: bytes, key_hex: str) -> bytes:
    """Encrypt *data* using Fernet with the 32-byte key encoded as *key_hex*."""
    import base64

    from cryptography.fernet import Fernet

    key_bytes = bytes.fromhex(key_hex)
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key).encrypt(data)


def _fernet_decrypt(data: bytes, key_hex: str) -> bytes:
    """Decrypt *data* using Fernet with the 32-byte key encoded as *key_hex*."""
    import base64

    from cryptography.fernet import Fernet

    key_bytes = bytes.fromhex(key_hex)
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key).decrypt(data)


# ---------------------------------------------------------------------------
# AuditStore
# ---------------------------------------------------------------------------


class AuditStore:
    """Append-only encrypted derivation tree store.

    Encryption tiers (evaluated in order):
      1. Windows: DPAPI CryptProtectData / CryptUnprotectData
      2. Non-Windows + STS_AUDIT_DEV_KEY env var: Fernet (32-byte key as hex)
      3. Non-Windows without key: plaintext (dev/test mode only)

    HMAC key:
      - STS_AUDIT_HMAC_KEY env var (hex string) — takes precedence
      - Else: SHA-256 of the audit_tree_dir path string (stable across restarts)
      - The *hmac_key* constructor parameter overrides both env vars.

    File layout: one ``{job_id}.audit.ndjson`` per job.  The entire file is
    encrypted as a single blob; individual records are newline-delimited JSON
    inside the plaintext.
    """

    PURPOSE = "audit_only"
    USE_RESTRICTION = "authorized_audit_query_only"

    def __init__(
        self,
        audit_tree_dir: Path,
        *,
        hmac_key: bytes | None = None,
    ) -> None:
        self._dir = Path(audit_tree_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

        # HMAC key resolution
        if hmac_key is not None:
            self._hmac_key = hmac_key
        elif env_key := os.getenv("STS_AUDIT_HMAC_KEY"):
            self._hmac_key = bytes.fromhex(env_key)
        else:
            self._hmac_key = hashlib.sha256(str(audit_tree_dir).encode()).digest()

        # Encryption mode
        self._dev_key: str | None = os.getenv("STS_AUDIT_DEV_KEY")
        self._use_dpapi: bool = platform.system() == "Windows"

    # ------------------------------------------------------------------
    # Internal encryption helpers
    # ------------------------------------------------------------------

    def _encrypt(self, data: bytes) -> bytes:
        if self._use_dpapi:
            return _dpapi_protect(data)
        if self._dev_key:
            return _fernet_encrypt(data, self._dev_key)
        return data  # plaintext dev mode

    def _decrypt(self, data: bytes) -> bytes:
        if self._use_dpapi:
            return _dpapi_unprotect(data)
        if self._dev_key:
            return _fernet_decrypt(data, self._dev_key)
        return data  # plaintext dev mode

    def _tree_path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.audit.ndjson"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Core append primitive
    # ------------------------------------------------------------------

    def _append(self, job_id: str, record: dict) -> None:
        """Append one record to the derivation tree for *job_id*.

        The record is stamped with purpose/use_restriction fields and an
        HMAC-SHA-256 tag before encryption.  The HMAC is computed over the
        serialised record payload *without* the ``_hmac`` field itself.
        """
        record["purpose"] = self.PURPOSE
        record["use_restriction"] = self.USE_RESTRICTION
        payload = json.dumps(record, separators=(",", ":"), sort_keys=True).encode()
        tag = hmac_mod.new(self._hmac_key, payload, hashlib.sha256).hexdigest()
        line = (
            json.dumps({**record, "_hmac": tag}, separators=(",", ":"), sort_keys=True) + "\n"
        )
        path = self._tree_path(job_id)
        existing = self._decrypt(path.read_bytes()) if path.exists() else b""
        path.write_bytes(self._encrypt(existing + line.encode()))

    # ------------------------------------------------------------------
    # Write methods — one per derivation record type
    # ------------------------------------------------------------------

    def write_source(
        self,
        job_id: str,
        *,
        source_hash: str,
        size_bytes: int,
        format: str,
        duration_seconds: float,
    ) -> None:
        """Record ingestion of the source media file."""
        self._append(
            job_id,
            {
                "record_type": "source",
                "job_id": job_id,
                "source_hash": source_hash,
                "size_bytes": size_bytes,
                "format": format,
                "duration_seconds": duration_seconds,
                "ingested_at": self._now(),
            },
        )

    def write_extraction(
        self,
        job_id: str,
        *,
        ffmpeg_version: str,
        params_hash: str,
        output_hash: str,
    ) -> None:
        """Record the audio extraction step."""
        self._append(
            job_id,
            {
                "record_type": "extraction",
                "job_id": job_id,
                "ffmpeg_version": ffmpeg_version,
                "params_hash": params_hash,
                "output_hash": output_hash,
                "extracted_at": self._now(),
            },
        )

    def write_transcription(
        self,
        job_id: str,
        *,
        model_id: str,
        model_hash: str,
        language: str,
        params_hash: str,
        segment_count: int,
    ) -> None:
        """Record the transcription step."""
        self._append(
            job_id,
            {
                "record_type": "transcription",
                "job_id": job_id,
                "model_id": model_id,
                "model_hash": model_hash,
                "language": language,
                "params_hash": params_hash,
                "segment_count": segment_count,
                "transcribed_at": self._now(),
            },
        )

    def write_segment(
        self,
        job_id: str,
        *,
        index: int,
        start_ms: int,
        end_ms: int,
        text_hash: str,
        avg_logprob: float,
        no_speech_prob: float,
    ) -> None:
        """Record one transcript segment (content-free: only hash of text stored)."""
        self._append(
            job_id,
            {
                "record_type": "segment",
                "job_id": job_id,
                "index": index,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text_hash": text_hash,
                "avg_logprob": avg_logprob,
                "no_speech_prob": no_speech_prob,
            },
        )

    def write_revision(
        self,
        job_id: str,
        *,
        revision_id: str,
        segment_index: int,
        operation: str,
        original_hash: str,
        corrected_hash: str,
    ) -> None:
        """Record a transcript correction (content-free: only hashes stored)."""
        self._append(
            job_id,
            {
                "record_type": "revision",
                "job_id": job_id,
                "revision_id": revision_id,
                "segment_index": segment_index,
                "operation": operation,
                "original_hash": original_hash,
                "corrected_hash": corrected_hash,
                "revised_at": self._now(),
            },
        )

    def write_export(
        self,
        job_id: str,
        *,
        format: str,
        destination_scope: str,
        content_hash: str,
    ) -> None:
        """Record a transcript export operation."""
        self._append(
            job_id,
            {
                "record_type": "export",
                "job_id": job_id,
                "format": format,
                "destination_scope": destination_scope,
                "content_hash": content_hash,
                "exported_at": self._now(),
            },
        )

    def write_deletion(
        self,
        job_id: str,
        *,
        scope: str,
        surviving_artifacts: list[str],
    ) -> None:
        """Record deletion of managed job data (audit tree always survives)."""
        self._append(
            job_id,
            {
                "record_type": "deletion",
                "job_id": job_id,
                "scope": scope,
                "surviving_artifacts": surviving_artifacts,
                "deleted_at": self._now(),
            },
        )

    # ------------------------------------------------------------------
    # Read / query
    # ------------------------------------------------------------------

    def read_provenance(self, job_id: str) -> list[dict]:
        """Decrypt and return all derivation records for *job_id*.

        Raises:
            ValueError: if any record's HMAC tag does not match.
        """
        path = self._tree_path(job_id)
        if not path.exists():
            return []
        raw = self._decrypt(path.read_bytes())
        records: list[dict] = []
        for lineno, line in enumerate(raw.decode().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            record: dict = json.loads(line)
            stored_hmac = record.pop("_hmac", None)
            if stored_hmac is None:
                raise ValueError(
                    f"Record {lineno} for job {job_id} is missing the _hmac field"
                )
            # Re-serialise without _hmac and verify
            payload = json.dumps(record, separators=(",", ":"), sort_keys=True).encode()
            expected_hmac = hmac_mod.new(self._hmac_key, payload, hashlib.sha256).hexdigest()
            if not hmac_mod.compare_digest(stored_hmac, expected_hmac):
                raise ValueError(
                    f"HMAC verification failed for record {lineno} in job {job_id}"
                )
            records.append(record)
        return records

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def tree_exists(self, job_id: str) -> bool:
        """Return True if a derivation tree file exists for *job_id*."""
        return self._tree_path(job_id).exists()

    def retention_floor_reached(self, job_id: str, min_days: int) -> bool:
        """Return True if the derivation tree for *job_id* is at least *min_days* old."""
        path = self._tree_path(job_id)
        if not path.exists():
            return False
        age_seconds = time.time() - path.stat().st_mtime
        age_days = age_seconds / 86_400
        return age_days >= min_days
