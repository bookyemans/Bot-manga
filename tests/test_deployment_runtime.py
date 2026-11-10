from __future__ import annotations

import os
from pathlib import Path

import pytest

from utils.instance_lock import InstanceAlreadyRunning, SingleInstanceLock


def test_single_instance_lock_excludes_second_process_handle(tmp_path):
    lock_path = tmp_path / "run" / "bot.lock"
    first = SingleInstanceLock(lock_path)
    second = SingleInstanceLock(lock_path)
    first.acquire()
    try:
        with pytest.raises(InstanceAlreadyRunning):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()
    assert f"pid={os.getpid()}" in lock_path.read_text()


def test_lock_context_releases_after_exception(tmp_path):
    lock_path = tmp_path / "bot.lock"
    with pytest.raises(ValueError):
        with SingleInstanceLock(lock_path):
            raise ValueError("test")
    with SingleInstanceLock(lock_path):
        pass


def test_healthcheck_with_valid_environment(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("MANGA_BOT_TELEGRAM_BOT_TOKEN", "123456:abcdefghijklmnopqrstuvwxyzABCDE")
    monkeypatch.setenv("MANGA_BOT_DATABASE_PATH", str(tmp_path / "data" / "bot.db"))
    monkeypatch.setenv("MANGA_BOT_INSTANCE_LOCK_PATH", str(tmp_path / "run" / "bot.lock"))
    from utils.healthcheck import main

    assert main() == 0
    assert "HEALTHCHECK OK" in capsys.readouterr().out
    assert (tmp_path / "data" / "bot.db").exists()


def test_healthcheck_rejects_placeholder_token(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("MANGA_BOT_TELEGRAM_BOT_TOKEN", "replace_with_telegram_bot_token")
    monkeypatch.setenv("MANGA_BOT_DATABASE_PATH", str(tmp_path / "bot.db"))
    monkeypatch.setenv("MANGA_BOT_INSTANCE_LOCK_PATH", str(tmp_path / "bot.lock"))
    from utils.healthcheck import main

    assert main() == 1
    assert "placeholder" in capsys.readouterr().err


def test_new_runtime_file_is_owner_only_on_posix(tmp_path):
    import stat
    from shared.file_security import create_private_file_if_missing

    path = tmp_path / "private" / "bot.db"
    create_private_file_if_missing(path)
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_instance_lock_is_owner_only_on_posix(tmp_path):
    import stat
    lock_path = tmp_path / "bot.lock"
    lock = SingleInstanceLock(lock_path)
    lock.acquire()
    lock.release()
    if os.name == "posix":
        assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600
