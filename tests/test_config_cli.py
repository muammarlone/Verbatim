from __future__ import annotations

import sys
from pathlib import Path

import pytest

from secure_transcribe import cli
from secure_transcribe.config import Settings, _env_int


def test_env_int_uses_default_and_enforces_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STS_TEST_LIMIT", raising=False)
    assert _env_int("STS_TEST_LIMIT", 7, 1, 10) == 7

    monkeypatch.setenv("STS_TEST_LIMIT", "10")
    assert _env_int("STS_TEST_LIMIT", 7, 1, 10) == 10

    monkeypatch.setenv("STS_TEST_LIMIT", "11")
    with pytest.raises(ValueError, match="must be between 1 and 10"):
        _env_int("STS_TEST_LIMIT", 7, 1, 10)


def test_settings_from_env_creates_managed_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "managed-data"
    model_path = tmp_path / "models" / "base.pt"
    batch_root = tmp_path / "approved-batch"
    monkeypatch.setenv("STS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("STS_MODEL_PATH", str(model_path))
    monkeypatch.setenv("STS_BATCH_ROOT", str(batch_root))
    monkeypatch.setenv("STS_MAX_BATCH_FILES", "12")

    settings = Settings.from_env()
    settings.ensure_directories()

    assert settings.data_dir == data_dir.resolve()
    assert settings.model_path == model_path.resolve()
    assert settings.batch_workspace == batch_root.resolve()
    assert settings.max_batch_files == 12
    assert (data_dir / "jobs").is_dir()
    assert (data_dir / "audit").is_dir()
    assert (data_dir / "batches").is_dir()
    assert batch_root.is_dir()


def test_cli_starts_on_loopback_without_opening_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = object()
    calls: dict[str, object] = {}
    monkeypatch.setattr(sys, "argv", ["verbatim", "--port", "9876", "--no-browser"])
    monkeypatch.setattr(cli, "create_app", lambda: app)
    monkeypatch.setattr(cli, "require_loopback_host", lambda host: calls.update(host=host))
    monkeypatch.setattr(
        cli.uvicorn, "run", lambda target, **kwargs: calls.update(target=target, **kwargs)
    )

    cli.main()

    assert calls == {
        "host": "127.0.0.1",
        "target": app,
        "port": 9876,
        "log_level": "warning",
        "access_log": False,
    }


def test_cli_rejects_unprivileged_port_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["verbatim", "--port", "1023", "--no-browser"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
