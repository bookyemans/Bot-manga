# systems/delivery/utils.py
from __future__ import annotations

import asyncio
import logging
from telegram.constants import ParseMode
from telegram.error import BadRequest

from systems.translation_pipeline.models.page_job import PageJob
from systems.delivery.telegram_api import telegram_api_call

logger = logging.getLogger(__name__)


async def safe_edit_or_send(bot, job: PageJob, text: str) -> None:
    if job.status_message_id:
        try:
            await telegram_api_call(
                bot.edit_message_text,
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        except Exception as exc:
            logger.debug("Could not edit status message for job %s: %s", job.job_id, exc)

    try:
        msg = await telegram_api_call(
            bot.send_message,
            chat_id=job.chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        job.status_message_id = msg.message_id
    except Exception:
        logger.exception("Could not send status message for job %s", job.job_id)


async def safe_delete_message(bot, job: PageJob) -> None:
    if not job.status_message_id:
        return
    try:
        await telegram_api_call(
            bot.delete_message,
            chat_id=job.chat_id,
            message_id=job.status_message_id,
        )
    except BadRequest as exc:
        # The message may already have been deleted or become inaccessible.
        logger.debug("Could not delete status message for job %s: %s", job.job_id, exc)
    except Exception:
        logger.exception("Could not delete status message for job %s", job.job_id)
