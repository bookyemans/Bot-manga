"""Cross-platform advisory lock to prevent duplicate bot processes."""
from __future__ import annotations

import os
from pathlib import Path


class InstanceAlreadyRunning(RuntimeError):
    """Raised when another process already owns the instance lock."""


class SingleInstanceLock:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+b")
        if os.name == "posix":
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                self._file.close()
                self._file = None
                raise
        self._file.seek(0, os.SEEK_END)
        if self._file.tell() == 0:
            self._file.write(b"\0")
            self._file.flush()
        self._file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self._file.close()
            self._file = None
            raise InstanceAlreadyRunning(
                f"Another bot process appears to hold the lock: {self.path}"
            ) from exc

        self._file.seek(0)
        self._file.truncate()
        self._file.write(f"pid={os.getpid()}\n".encode("ascii"))
        self._file.flush()

    def release(self) -> None:
        if self._file is None:
            return
        try:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()
