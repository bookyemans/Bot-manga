import pytest
from shared.repositories.access import AccessRepository
from shared.repositories.api_keys import APIKeyRepository
from shared.repositories.settings import SettingsRepository

class FakeDB:
    def __init__(self): self.calls = []
    async def execute(self, query, params=()): self.calls.append((query, params)); return 1
    async def fetchone(self, query, params=()): self.calls.append((query, params)); return (1,)
    async def fetchall(self, query, params=()): self.calls.append((query, params)); return [(1,)]

@pytest.mark.asyncio
async def test_settings_repository_uses_whitelisted_column_and_bound_values():
    db = FakeDB(); repo = SettingsRepository(db)
    await repo.set(7, "persona", "Nabil'")
    query, params = db.calls[0]
    assert "persona" in query and params == (7, "Nabil'")
    with pytest.raises(ValueError): await repo.set(7, "persona = 'x' --", "bad")

@pytest.mark.asyncio
async def test_access_repository_preserves_parameterized_access_queries():
    db = FakeDB(); repo = AccessRepository(db)
    assert await repo.is_admin(12) is True
    assert db.calls[0][1] == (12,)
    await repo.add_user(12)
    assert db.calls[1][1] == (12,)

@pytest.mark.asyncio
async def test_api_key_repository_parameterizes_key_values():
    db = FakeDB(); repo = APIKeyRepository(db)
    await repo.add_public("key-value")
    assert db.calls[0][1] == ("key-value",)
