from __future__ import annotations
from typing import Any

class APIKeyRepository:
    def __init__(self, db: Any) -> None: self.db = db
    async def public_keys(self): return await self.db.fetchall("SELECT key_value FROM api_keys WHERE user_id IS NULL")
    async def add_public(self, key: str): return await self.db.execute("INSERT OR IGNORE INTO api_keys (key_value, user_id) VALUES (?, NULL)", (key,))
    async def remove_public(self, key: str): return await self.db.execute("DELETE FROM api_keys WHERE key_value = ? AND user_id IS NULL", (key,))
    async def set_user(self, uid: int, key: str): return await self.db.execute("INSERT OR REPLACE INTO api_keys (key_value, user_id) VALUES (?, ?)", (key, uid))
    async def remove_user(self, uid: int): return await self.db.execute("DELETE FROM api_keys WHERE user_id = ?", (uid,))
    async def user_key(self, uid: int): return await self.db.fetchone("SELECT key_value FROM api_keys WHERE user_id = ?", (uid,))
