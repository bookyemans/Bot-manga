from __future__ import annotations
from typing import Any

class AccessRepository:
    def __init__(self, db: Any) -> None: self.db = db
    async def is_admin(self, uid: int): return await self.db.fetchone("SELECT 1 FROM users_access WHERE user_id = ? AND role = 'admin'", (uid,)) is not None
    async def is_authorized(self, uid: int): return await self.db.fetchone("SELECT 1 FROM users_access WHERE user_id = ?", (uid,)) is not None
    async def get_join_requests(self): return await self.db.fetchone("SELECT value FROM meta WHERE key = 'join_requests_open'")
    async def set_join_requests(self, value: str): return await self.db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('join_requests_open', ?)", (value,))
    async def add_user(self, uid: int): return await self.db.execute("INSERT OR IGNORE INTO users_access (user_id, role) VALUES (?, 'user')", (uid,))
    async def remove_user(self, uid: int): return await self.db.execute("DELETE FROM users_access WHERE user_id = ? AND role = 'user'", (uid,))
    async def add_admin(self, uid: int): return await self.db.execute("INSERT OR REPLACE INTO users_access (user_id, role) VALUES (?, 'admin')", (uid,))
    async def remove_admin(self, uid: int): return await self.db.execute("DELETE FROM users_access WHERE user_id = ? AND role = 'admin'", (uid,))
    async def get_admins(self): return await self.db.fetchall("SELECT user_id FROM users_access WHERE role = 'admin'")
    async def get_users(self): return await self.db.fetchall("SELECT user_id FROM users_access WHERE role = 'user'")
