"""Shared, resource-safe Telegram document delivery helper."""
from __future__ import annotations

import asyncio
from typing import BinaryIO

from telegram import Bot, InputFile

from systems.delivery.telegram_api import telegram_api_call


async def send_generated_document(
    bot: Bot,
    *,
    chat_id: int,
    file_io: BinaryIO,
    filename: str,
    reply_to_message_id: int | None = None,
    timeout: float = 60.0,
) -> None:
    """Send a generated in-memory document and always release its buffer."""
    try:
        await asyncio.wait_for(
            telegram_api_call(
                bot.send_document,
                chat_id=chat_id,
                document=InputFile(file_io, filename=filename),
                reply_to_message_id=reply_to_message_id,
                retry_prepare=lambda: file_io.seek(0),
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        raise RuntimeError("Telegram document send timed out.") from exc
    finally:
        file_io.close()
