from io import BytesIO
import importlib
import sys
import types

import pytest


class FakeBot:
    async def send_document(self, **kwargs):
        return object()


class FakeInputFile:
    def __init__(self, obj, filename=None):
        self.obj = obj
        self.filename = filename


telegram_stub = types.ModuleType("telegram")
telegram_stub.Bot = FakeBot
telegram_stub.InputFile = FakeInputFile
sys.modules.setdefault("telegram", telegram_stub)

document_sender = importlib.import_module("systems.delivery.senders.document_sender")


@pytest.mark.asyncio
async def test_send_generated_document_closes_buffer(monkeypatch):
    calls = []

    async def fake_api_call(operation, **kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(document_sender, "telegram_api_call", fake_api_call)
    stream = BytesIO(b"document")

    await document_sender.send_generated_document(
        FakeBot(), chat_id=123, file_io=stream, filename="result.txt", reply_to_message_id=9
    )

    assert stream.closed
    assert calls[0]["chat_id"] == 123
    assert calls[0]["reply_to_message_id"] == 9
    assert calls[0]["document"].filename == "result.txt"


@pytest.mark.asyncio
async def test_send_generated_document_closes_buffer_on_failure(monkeypatch):
    async def failing_api_call(operation, **kwargs):
        raise ValueError("send failed")

    monkeypatch.setattr(document_sender, "telegram_api_call", failing_api_call)
    stream = BytesIO(b"document")

    with pytest.raises(ValueError, match="send failed"):
        await document_sender.send_generated_document(
            FakeBot(), chat_id=123, file_io=stream, filename="result.docx"
        )

    assert stream.closed
