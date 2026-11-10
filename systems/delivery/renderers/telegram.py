# systems/delivery/renderers/telegram.py
from __future__ import annotations

import asyncio
import logging
from typing import List

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import BadRequest

from systems.translation_pipeline.models.page_job import JobState, PageJob
from systems.delivery.telegram_api import telegram_api_call

logger = logging.getLogger(__name__)

class TelegramRenderer:
    def __init__(self, batch_size: int = 2, batch_delay_seconds: float = 0.5) -> None:
        self.send_batch_size = max(1, min(3, int(batch_size)))
        self.batch_delay_seconds = max(0.1, float(batch_delay_seconds))

    async def render_messages(self, bot: Bot, job: PageJob, messages: List[str]) -> None:
        if not messages:
            job.state = JobState.FINISHED
            return

        job.state = JobState.SENDING
        failed = 0
        for i in range(0, len(messages), self.send_batch_size):
            batch = messages[i:i + self.send_batch_size]
            results = await asyncio.gather(
                *(self._safe_send_message(bot, job, raw_text) for raw_text in batch),
                return_exceptions=True,
            )
            failed += sum(isinstance(result, BaseException) for result in results)
            if i + self.send_batch_size < len(messages):
                await asyncio.sleep(self.batch_delay_seconds)

        job.state = JobState.FAILED if failed else JobState.FINISHED
        if failed:
            logger.error("JobID=%s | %s Telegram message(s) failed to send", job.job_id, failed)
            raise RuntimeError(f"Failed to deliver {failed} Telegram message(s)")

    async def _safe_send_message(self, bot: Bot, job: PageJob, text: str) -> None:
        try:
            await telegram_api_call(
                bot.send_message,
                chat_id=job.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
                reply_to_message_id=job.photo_message_id,
            )
        except BadRequest as exc:
            logger.warning("BadRequest sending formatted message for job %s: %s", job.job_id, exc)
            # Fallback to plain text, preserving the translated content.
            await telegram_api_call(
                bot.send_message,
                chat_id=job.chat_id,
                text=text,
                disable_web_page_preview=True,
                reply_to_message_id=job.photo_message_id,
            )
