# config/settings.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration loaded at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MANGA_BOT_",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str
    database_path: str = "manga_bot.db"
    instance_lock_path: str = ".runtime/void_translator.lock"

    # AI Engine
    ai_provider: str = "gemini"
    ai_api_key: str = ""
    ai_timeout_seconds: float = 60.0
    # Gemini model order is configurable; comma-separated stable model IDs.
    gemini_models: str = "gemini-3.5-flash-lite,gemini-3.8-flash"
    gemini_max_retries: int = Field(default=2, ge=1, le=3)
    gemini_retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=15.0)

    # Queue & Job Manager
    # Conservative defaults for small hosts (0.5 CPU / 512 MB RAM).
    queue_max_size: int = Field(default=100, ge=10, le=1000)
    ai_worker_count: int = Field(default=1, ge=1, le=4)
    delivery_worker_count: int = Field(default=1, ge=1, le=4)
    thread_pool_workers: int = Field(default=2, ge=1, le=4)
    ai_http_connection_limit: int = Field(default=4, ge=1, le=20)
    image_max_side: int = Field(default=1280, ge=256, le=4096)
    image_max_pixels: int = Field(default=10_000_000, ge=1_000_000, le=50_000_000)
    image_max_download_bytes: int = Field(default=10_000_000, ge=1_000_000, le=20_000_000)
    post_job_delay_seconds: int = 0
    max_running_jobs: int = 1  # Deprecated compatibility setting; worker counts control concurrency.

    # SQLite: small bounded cache suitable for low-memory hosts.
    db_busy_timeout_ms: int = Field(default=5000, ge=100, le=30000)
    db_cache_size_kib: int = Field(default=2048, ge=256, le=16384)
    db_wal_autocheckpoint_pages: int = Field(default=1000, ge=100, le=10000)

    # Circuit Breaker (High Availability)
    cb_failure_threshold: int = 5
    cb_cooldown_seconds: int = 60

    # Telegram rendering limits
    telegram_text_limit: int = Field(default=4096, ge=512, le=4096)
    telegram_send_batch_size: int = Field(default=2, ge=1, le=3)
    telegram_send_delay_seconds: float = Field(default=0.5, ge=0.1, le=5.0)

    # Pagination
    message_max_length: int = 3500

    # Logging
    log_level: str = "INFO"

    # Super Admins (Hardcoded & Immutable)
    super_admin_ids: str = "7203463194,7369573507,7757349253"