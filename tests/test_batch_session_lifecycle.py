import pytest

from systems.delivery.batch import BatchManager


@pytest.mark.asyncio
async def test_clear_session_removes_all_session_owned_state():
    manager = BatchManager()
    user_id = 123
    await manager.start_session(user_id, "persona", "grouped")
    await manager.set_pending_compile(user_id)
    await manager.set_finalizing(user_id, True)
    await manager.set_session_note(user_id, "note")
    await manager.add_session_photo_id(user_id, 77)
    await manager.add_transient_message(user_id, 88)
    await manager.add_pending_file(user_id, "file", "page.jpg", 77)
    await manager.set_waiting_message_id(user_id, 99)
    await manager.clear_session(user_id)

    assert not await manager.is_session_active(user_id)
    assert not await manager.is_pending_compile(user_id)
    assert not await manager.is_finalizing(user_id)
    assert await manager.get_session_persona(user_id) is None
    assert await manager.get_session_mode(user_id) is None
    assert await manager.get_session_note(user_id) == ""
    assert await manager.get_session_photo_ids(user_id) == []
    assert await manager.get_transient_messages(user_id) == []
    assert await manager.get_pending_files(user_id) == []
    assert await manager.get_waiting_message_id(user_id) is None


@pytest.mark.asyncio
async def test_start_session_does_not_reset_existing_session_data():
    manager = BatchManager()
    user_id = 456
    await manager.start_session(user_id, "first", "grouped")
    await manager.set_session_note(user_id, "preserve")
    await manager.start_session(user_id, "second", "individual")

    assert await manager.get_session_persona(user_id) == "first"
    assert await manager.get_session_mode(user_id) == "grouped"
    assert await manager.get_session_note(user_id) == "preserve"
