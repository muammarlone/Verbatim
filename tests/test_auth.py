"""Tests for STS-103 OS auth interface — ADR-008."""

from __future__ import annotations

import logging
import platform

import pytest

from secure_transcribe.auth import (
    AuthProvider,
    DevAuthStub,
    WindowsCredentialLockerProvider,
    get_auth_provider,
)
from secure_transcribe.config import Settings


# ---------------------------------------------------------------------------
# DevAuthStub tests
# ---------------------------------------------------------------------------


def test_dev_stub_is_authenticated_returns_true() -> None:
    stub = DevAuthStub()
    assert stub.is_authenticated() is True


def test_dev_stub_get_credential_returns_none() -> None:
    stub = DevAuthStub()
    assert stub.get_credential("any-key") is None
    assert stub.get_credential("") is None


def test_dev_stub_store_credential_is_noop() -> None:
    stub = DevAuthStub()
    stub.store_credential("key", "secret-value")
    # After store, get still returns None (no persistence)
    assert stub.get_credential("key") is None


def test_dev_stub_delete_credential_is_noop() -> None:
    stub = DevAuthStub()
    # No exception raised even for non-existent key
    stub.delete_credential("nonexistent-key")


def test_dev_stub_no_plaintext_log(caplog: pytest.LogCaptureFixture) -> None:
    stub = DevAuthStub()
    secret = "super-secret-value-12345"
    with caplog.at_level(logging.DEBUG):
        stub.store_credential("key", secret)
    assert secret not in caplog.text


def test_dev_stub_satisfies_auth_provider_interface() -> None:
    stub = DevAuthStub()
    assert isinstance(stub, AuthProvider)


# ---------------------------------------------------------------------------
# get_auth_provider factory tests
# ---------------------------------------------------------------------------


def test_get_auth_provider_returns_dev_stub_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STS_OS_AUTH_ENABLED", raising=False)
    provider = get_auth_provider()
    assert isinstance(provider, DevAuthStub)


def test_get_auth_provider_returns_dev_stub_when_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STS_OS_AUTH_ENABLED", "false")
    provider = get_auth_provider()
    assert isinstance(provider, DevAuthStub)


def test_get_auth_provider_returns_dev_stub_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STS_OS_AUTH_ENABLED", "0")
    provider = get_auth_provider()
    assert isinstance(provider, DevAuthStub)


@pytest.mark.skipif(platform.system() == "Windows", reason="Guard only fires on non-Windows")
def test_get_auth_provider_raises_on_non_windows_with_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STS_OS_AUTH_ENABLED", "true")
    with pytest.raises(RuntimeError, match="requires Windows"):
        get_auth_provider()


# ---------------------------------------------------------------------------
# WindowsCredentialLockerProvider class-level tests (no API calls)
# ---------------------------------------------------------------------------


def test_target_prefix_set() -> None:
    assert WindowsCredentialLockerProvider._TARGET_PREFIX == "Verbatim/"


def test_cred_type_generic_set() -> None:
    assert WindowsCredentialLockerProvider._CRED_TYPE_GENERIC == 1


# ---------------------------------------------------------------------------
# Settings integration
# ---------------------------------------------------------------------------


def test_settings_os_auth_enabled_defaults_false(tmp_path: pytest.TempPathFactory) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",  # type: ignore[arg-type]
        model_path=tmp_path / "model.pt",  # type: ignore[arg-type]
    )
    assert settings.os_auth_enabled is False


def test_settings_os_auth_enabled_can_be_set_true(tmp_path: pytest.TempPathFactory) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",  # type: ignore[arg-type]
        model_path=tmp_path / "model.pt",  # type: ignore[arg-type]
        os_auth_enabled=True,
    )
    assert settings.os_auth_enabled is True
