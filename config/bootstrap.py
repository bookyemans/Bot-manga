"""Application bootstrap helpers.

This module is intentionally small: it owns configuration loading and startup
validation without constructing application services or importing Telegram.
"""
from __future__ import annotations

import logging

from config.settings import Settings


def load_settings(*, env_file: str | None = ".env") -> Settings:
    """Load one settings snapshot for the current application process."""
    return Settings(_env_file=env_file)


def validate_startup_settings(settings: Settings) -> None:
    """Fail early for missing or placeholder credentials."""
    token = settings.telegram_bot_token.strip()
    if not token or token.lower().startswith("replace_"):
        raise RuntimeError(
            "Set MANGA_BOT_TELEGRAM_BOT_TOKEN in the environment before starting."
        )


def configure_logging(settings: Settings) -> None:
    """Configure process-wide logging once, at the executable boundary."""
    level_name = settings.log_level.strip().upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"Invalid MANGA_BOT_LOG_LEVEL: {settings.log_level!r}")
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
