"""Local deployment health check; does not contact Telegram or Gemini."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from config.settings import Settings


def main() -> int:
    try:
        settings = Settings()
        token = settings.telegram_bot_token.strip()
        if not token or token.lower().startswith(("replace_", "your_", "put_")):
            raise ValueError("MANGA_BOT_TELEGRAM_BOT_TOKEN is missing or still a placeholder")

        database_path = Path(settings.database_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(database_path), timeout=settings.db_busy_timeout_ms / 1000) as db:
            result = db.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError(f"SQLite quick_check failed: {result!r}")

        lock_path = Path(settings.instance_lock_path)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not lock_path.parent.is_dir():
            raise RuntimeError("Instance lock directory is unavailable")

        print("HEALTHCHECK OK: configuration and SQLite storage are accessible.")
        return 0
    except Exception as exc:
        # Avoid dumping settings or credentials in health-check output.
        print(f"HEALTHCHECK FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
