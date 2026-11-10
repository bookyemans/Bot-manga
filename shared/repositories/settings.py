from __future__ import annotations
from typing import Any

class SettingsRepository:
    FIELDS = {"persona", "mode", "output_method", "file_format", "session_mode", "use_glossary"}
    def __init__(self, db: Any) -> None: self.db = db
    async def get(self, uid: int):
        return await self.db.fetchone("SELECT persona, mode, output_method, file_format, session_mode, use_glossary FROM settings WHERE user_id = ?", (uid,))
    async def set(self, uid: int, field: str, value: str) -> None:
        if field not in self.FIELDS: raise ValueError(f"Unsupported settings field: {field}")
        await self.db.execute(f"INSERT INTO settings (user_id, {field}) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET {field} = excluded.{field}", (uid, value))
