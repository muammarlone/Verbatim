"""Mock-based tests for WindowsCredentialLockerProvider.

Uses unittest.mock to patch secure_transcribe.auth.ctypes so these tests
run on any platform (Windows or not) without touching the real Credential Store.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from secure_transcribe.auth import WindowsCredentialLockerProvider, _ERROR_NOT_FOUND


def _make_provider() -> WindowsCredentialLockerProvider:
    return WindowsCredentialLockerProvider()


# ---------------------------------------------------------------------------
# get_credential
# ---------------------------------------------------------------------------


@patch("secure_transcribe.auth.ctypes")
def test_get_credential_not_found_returns_none(mock_ctypes: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredReadW.return_value = 0
    mock_ctypes.GetLastError.return_value = _ERROR_NOT_FOUND
    mock_ctypes.POINTER.return_value = MagicMock(return_value=MagicMock())
    mock_ctypes.byref = MagicMock(side_effect=lambda x: x)

    result = _make_provider().get_credential("missing-key")
    assert result is None


@patch("secure_transcribe.auth.ctypes")
def test_get_credential_read_error_raises(mock_ctypes: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredReadW.return_value = 0
    mock_ctypes.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED
    mock_ctypes.POINTER.return_value = MagicMock(return_value=MagicMock())
    mock_ctypes.byref = MagicMock(side_effect=lambda x: x)

    with pytest.raises(RuntimeError, match="CredReadW failed"):
        _make_provider().get_credential("bad-key")


@patch("secure_transcribe.auth.ctypes")
def test_get_credential_empty_blob_returns_none(mock_ctypes: MagicMock) -> None:
    mock_cred = MagicMock()
    mock_cred.contents.CredentialBlobSize = 0
    mock_cred.contents.CredentialBlob = None
    mock_ctypes.POINTER.return_value = MagicMock(return_value=mock_cred)
    mock_ctypes.windll.advapi32.CredReadW.return_value = 1  # success
    mock_ctypes.byref = MagicMock(side_effect=lambda x: x)

    result = _make_provider().get_credential("empty")
    assert result is None
    mock_ctypes.windll.advapi32.CredFree.assert_called_once()


@patch("secure_transcribe.auth.ctypes")
def test_get_credential_found_returns_value(mock_ctypes: MagicMock) -> None:
    secret = b"s3cr3t-v4lue"
    mock_cred = MagicMock()
    mock_cred.contents.CredentialBlobSize = len(secret)
    mock_cred.contents.CredentialBlob = secret
    mock_ctypes.POINTER.return_value = MagicMock(return_value=mock_cred)
    mock_ctypes.windll.advapi32.CredReadW.return_value = 1  # success
    mock_ctypes.byref = MagicMock(side_effect=lambda x: x)

    result = _make_provider().get_credential("my-api-key")
    assert result == "s3cr3t-v4lue"
    mock_ctypes.windll.advapi32.CredFree.assert_called_once()


# ---------------------------------------------------------------------------
# store_credential
# ---------------------------------------------------------------------------


@patch("secure_transcribe.auth._CREDENTIAL")
@patch("secure_transcribe.auth.ctypes")
def test_store_credential_success(mock_ctypes: MagicMock, mock_cred_class: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredWriteW.return_value = 1
    _make_provider().store_credential("api-key", "my-secret-value")
    mock_ctypes.windll.advapi32.CredWriteW.assert_called_once()


@patch("secure_transcribe.auth._CREDENTIAL")
@patch("secure_transcribe.auth.ctypes")
def test_store_credential_write_error_raises(mock_ctypes: MagicMock, mock_cred_class: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredWriteW.return_value = 0
    mock_ctypes.GetLastError.return_value = 5

    with pytest.raises(RuntimeError, match="CredWriteW failed"):
        _make_provider().store_credential("key", "value")


@patch("secure_transcribe.auth._CREDENTIAL")
@patch("secure_transcribe.auth.ctypes")
def test_store_credential_does_not_log_value(
    mock_ctypes: MagicMock, mock_cred_class: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_ctypes.windll.advapi32.CredWriteW.return_value = 1
    import logging
    with caplog.at_level(logging.DEBUG):
        try:
            _make_provider().store_credential("key", "super-secret-value")
        except Exception:
            pass
    assert "super-secret-value" not in caplog.text


# ---------------------------------------------------------------------------
# delete_credential
# ---------------------------------------------------------------------------


@patch("secure_transcribe.auth.ctypes")
def test_delete_credential_success(mock_ctypes: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredDeleteW.return_value = 1
    _make_provider().delete_credential("old-key")
    mock_ctypes.windll.advapi32.CredDeleteW.assert_called_once()


@patch("secure_transcribe.auth.ctypes")
def test_delete_credential_not_found_is_silent(mock_ctypes: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredDeleteW.return_value = 0
    mock_ctypes.GetLastError.return_value = _ERROR_NOT_FOUND
    # Should not raise — deleting a non-existent credential is a no-op
    _make_provider().delete_credential("already-gone")


@patch("secure_transcribe.auth.ctypes")
def test_delete_credential_other_error_raises(mock_ctypes: MagicMock) -> None:
    mock_ctypes.windll.advapi32.CredDeleteW.return_value = 0
    mock_ctypes.GetLastError.return_value = 5  # ACCESS_DENIED
    with pytest.raises(RuntimeError, match="CredDeleteW failed"):
        _make_provider().delete_credential("denied-key")


# ---------------------------------------------------------------------------
# target prefix
# ---------------------------------------------------------------------------


def test_target_prefix_format() -> None:
    p = _make_provider()
    assert p._target("my-cred") == "Verbatim/my-cred"


def test_is_authenticated_always_true() -> None:
    # Windows session boundary = authentication
    assert _make_provider().is_authenticated() is True


# ---------------------------------------------------------------------------
# get_auth_provider factory
# ---------------------------------------------------------------------------


def test_get_auth_provider_returns_stub_by_default() -> None:
    from secure_transcribe.auth import DevAuthStub, get_auth_provider
    with patch.dict(os.environ, {"STS_OS_AUTH_ENABLED": "false"}):
        provider = get_auth_provider()
    assert isinstance(provider, DevAuthStub)


@patch("secure_transcribe.auth.platform")
def test_get_auth_provider_non_windows_raises_when_enabled(mock_platform: MagicMock) -> None:
    import os as _os
    from secure_transcribe.auth import get_auth_provider
    mock_platform.system.return_value = "Linux"
    with patch.dict(_os.environ, {"STS_OS_AUTH_ENABLED": "true"}):
        with pytest.raises(RuntimeError, match="requires Windows"):
            get_auth_provider()


def test_get_auth_provider_env_off_variants() -> None:
    from secure_transcribe.auth import DevAuthStub, get_auth_provider
    for val in ("false", "0", "no", "off"):
        with patch.dict(os.environ, {"STS_OS_AUTH_ENABLED": val}):
            assert isinstance(get_auth_provider(), DevAuthStub)
