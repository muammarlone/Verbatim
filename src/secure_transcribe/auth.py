"""OS-backed authentication provider for Verbatim STS.

Governed by ADR-008. Default: disabled (STS_OS_AUTH_ENABLED=false).

Dev stub is always-authenticated and never stores credentials — safe for CI and
single-user local deployments.  Windows Credential Locker implementation is gated
on STS_OS_AUTH_ENABLED=true and only available on Windows.

No credential value is ever written to any log, audit record, or stdout.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import platform
from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """Authentication and credential storage contract (ADR-008)."""

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Return True if the current session is authenticated."""

    @abstractmethod
    def get_credential(self, key: str) -> str | None:
        """Return the stored credential for *key*, or None if not found."""

    @abstractmethod
    def store_credential(self, key: str, value: str) -> None:
        """Store *value* under *key*.  Never log the value."""

    @abstractmethod
    def delete_credential(self, key: str) -> None:
        """Delete the stored credential for *key* if it exists."""


class DevAuthStub(AuthProvider):
    """Always-authenticated no-op stub for dev and single-user deployments.

    Never persists credentials.  Safe for CI and synthetic testing.
    """

    def is_authenticated(self) -> bool:
        return True

    def get_credential(self, key: str) -> str | None:
        return None

    def store_credential(self, key: str, value: str) -> None:
        # Intentional no-op: dev stub does not persist credentials.
        return

    def delete_credential(self, key: str) -> None:
        return


# ---------------------------------------------------------------------------
# Windows Credential Locker implementation
# ---------------------------------------------------------------------------

_CRED_TYPE_GENERIC = 1
_ERROR_NOT_FOUND = 1168


class _CREDENTIAL(ctypes.Structure):
    """Minimal subset of CREDENTIALW needed for CredRead / CredWrite."""

    _fields_ = [
        ("Flags", ctypes.wintypes.DWORD),
        ("Type", ctypes.wintypes.DWORD),
        ("TargetName", ctypes.wintypes.LPWSTR),
        ("Comment", ctypes.wintypes.LPWSTR),
        ("LastWritten", ctypes.wintypes.FILETIME),
        ("CredentialBlobSize", ctypes.wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", ctypes.wintypes.DWORD),
        ("AttributeCount", ctypes.wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", ctypes.wintypes.LPWSTR),
        ("UserName", ctypes.wintypes.LPWSTR),
    ]


class WindowsCredentialLockerProvider(AuthProvider):
    """Windows Credential Locker via CredWrite/CredRead/CredDelete (advapi32).

    Credentials are stored per-user, session-bound.
    Target name: 'Verbatim/{key}'.
    Credential blob is UTF-8 encoded value bytes — never logged.
    """

    _CRED_TYPE_GENERIC = _CRED_TYPE_GENERIC
    _TARGET_PREFIX = "Verbatim/"
    _PERSIST_LOCAL_MACHINE = 2

    def _target(self, key: str) -> str:
        return f"{self._TARGET_PREFIX}{key}"

    def is_authenticated(self) -> bool:
        # Windows user session is the authentication boundary.
        return True

    def get_credential(self, key: str) -> str | None:
        advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]
        cred_ptr = ctypes.POINTER(_CREDENTIAL)()
        target = self._target(key)
        ok = advapi32.CredReadW(
            target,
            _CRED_TYPE_GENERIC,
            0,
            ctypes.byref(cred_ptr),
        )
        if not ok:
            err = ctypes.GetLastError()
            if err == _ERROR_NOT_FOUND:
                return None
            raise RuntimeError(f"CredReadW failed with error {err}")
        try:
            blob_size = cred_ptr.contents.CredentialBlobSize
            blob_ptr = cred_ptr.contents.CredentialBlob
            if blob_size == 0 or not blob_ptr:
                return None
            raw = bytes(blob_ptr[:blob_size])
            return raw.decode("utf-8")
        finally:
            advapi32.CredFree(cred_ptr)

    def store_credential(self, key: str, value: str) -> None:
        advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]
        blob = value.encode("utf-8")
        blob_arr = (ctypes.c_ubyte * len(blob))(*blob)
        target = self._target(key)
        cred = _CREDENTIAL()
        cred.Type = _CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = blob_arr
        cred.Persist = self._PERSIST_LOCAL_MACHINE
        if not advapi32.CredWriteW(ctypes.byref(cred), 0):
            raise RuntimeError(f"CredWriteW failed with error {ctypes.GetLastError()}")
        # Value is never referenced after this point — not logged.

    def delete_credential(self, key: str) -> None:
        advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]
        target = self._target(key)
        ok = advapi32.CredDeleteW(target, _CRED_TYPE_GENERIC, 0)
        if not ok:
            err = ctypes.GetLastError()
            if err != _ERROR_NOT_FOUND:
                raise RuntimeError(f"CredDeleteW failed with error {err}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_auth_provider() -> AuthProvider:
    """Return the appropriate AuthProvider based on STS_OS_AUTH_ENABLED.

    Returns DevAuthStub unless STS_OS_AUTH_ENABLED=true on Windows.
    Raises RuntimeError if STS_OS_AUTH_ENABLED=true on non-Windows.
    """
    if os.getenv("STS_OS_AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
        if platform.system() != "Windows":
            raise RuntimeError(
                "STS_OS_AUTH_ENABLED=true requires Windows. "
                "Set STS_OS_AUTH_ENABLED=false for non-Windows dev environments."
            )
        return WindowsCredentialLockerProvider()
    return DevAuthStub()
