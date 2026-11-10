"""Small filesystem permission helpers for runtime secrets and state files."""
from __future__ import annotations

import os
from pathlib import Path


def create_private_file_if_missing(path: str | Path) -> None:
    """Create a file as owner-only on POSIX without changing existing modes."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "posix":
        target.touch(exist_ok=True)
        return
    try:
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return
    else:
        os.close(fd)
