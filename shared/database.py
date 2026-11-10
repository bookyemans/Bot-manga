from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Sequence, Any

import aiosqlite

from shared.file_security import create_private_file_if_missing

logger = logging.getLogger(__name__)


class Database:
    """Single-connection async SQLite wrapper with serialized access.

    All reads and writes share one lock because a single SQLite connection has
    connection-wide transaction state. This prevents a reader from observing
    another coroutine's uncommitted write on the same connection.
    """

    def __init__(
        self,
        db_path: str = "manga_bot.db",
        *,
        busy_timeout_ms: int = 5000,
        cache_size_kib: int = 2048,
        wal_autocheckpoint_pages: int = 1000,
    ) -> None:
        self.db_path = db_path
        self.busy_timeout_ms = max(100, int(busy_timeout_ms))
        self.cache_size_kib = max(256, int(cache_size_kib))
        self.wal_autocheckpoint_pages = max(100, int(wal_autocheckpoint_pages))
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._conn is not None:
            return
        # Create new database files with owner-only permissions on POSIX.
        # Existing database permissions are deliberately left untouched.
        if self.db_path != ":memory:":
            create_private_file_if_missing(self.db_path)
        self._conn = await aiosqlite.connect(
            self.db_path,
            timeout=self.busy_timeout_ms / 1000,
        )
        try:
            async with self._lock:
                await self._conn.execute("PRAGMA journal_mode=WAL")
                await self._conn.execute("PRAGMA synchronous=NORMAL")
                await self._conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
                await self._conn.execute(f"PRAGMA cache_size=-{self.cache_size_kib}")
                await self._conn.execute("PRAGMA temp_store=MEMORY")
                await self._conn.execute(
                    f"PRAGMA wal_autocheckpoint={self.wal_autocheckpoint_pages}"
                )
                await self.init_db()
            logger.info("SQLite connected (WAL, NORMAL, bounded cache, busy timeout).")
        except Exception:
            await self._conn.close()
            self._conn = None
            raise

    async def close(self) -> None:
        async with self._lock:
            if self._conn is not None:
                try:
                    await self._conn.execute("PRAGMA optimize")
                    await self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                except aiosqlite.Error:
                    logger.debug("SQLite maintenance during close was skipped.", exc_info=True)
                await self._conn.close()
                self._conn = None
                logger.info("Database connection closed.")

    def _require_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected; call connect() first.")
        return self._conn

    async def init_db(self) -> None:
        conn = self._require_connection()
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users_access (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                persona TEXT,
                mode TEXT,
                output_method TEXT,
                file_format TEXT
            )
        """)

        # Idempotent additive migrations; existing user settings are preserved.
        columns_cursor = await conn.execute("PRAGMA table_info(settings)")
        columns = {row[1] for row in await columns_cursor.fetchall()}
        for column in ("session_mode", "use_glossary"):
            if column not in columns:
                await conn.execute(f"ALTER TABLE settings ADD COLUMN {column} TEXT")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_value TEXT PRIMARY KEY,
                user_id INTEGER
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_access_role ON users_access(role)"
        )
        await conn.commit()
        await conn.execute("PRAGMA optimize")

    async def execute(self, query: str, params: Sequence[Any] = ()) -> int:
        """Execute one write, commit it, and return affected row count."""
        async with self._lock:
            conn = self._require_connection()
            try:
                cursor = await conn.execute(query, params)
                rowcount = cursor.rowcount
                await cursor.close()
                await conn.commit()
                return rowcount
            except Exception:
                await conn.rollback()
                raise

    async def executemany(
        self, query: str, parameters: Iterable[Sequence[Any]]
    ) -> int:
        """Execute a batch as one transaction to reduce commits and lock time."""
        async with self._lock:
            conn = self._require_connection()
            try:
                cursor = await conn.executemany(query, parameters)
                rowcount = cursor.rowcount
                await cursor.close()
                await conn.commit()
                return rowcount
            except Exception:
                await conn.rollback()
                raise

    async def fetchone(self, query: str, params: Sequence[Any] = ()):
        async with self._lock:
            conn = self._require_connection()
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def fetchall(self, query: str, params: Sequence[Any] = ()):
        async with self._lock:
            conn = self._require_connection()
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchall()
