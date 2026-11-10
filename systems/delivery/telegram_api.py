"""Bounded, retry-aware Telegram API calls used by the delivery pipeline.

This module deliberately has no PTB imports so its retry policy can be unit-tested
without a live Telegram client.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# A small global cap prevents concurrent delivery workers from creating bursts.
_TELEGRAM_SEMAPHORE = asyncio.Semaphore(2)
_MAX_ATTEMPTS = 3


def _retry_after_seconds(error: BaseException) -> Optional[float]:
    value = getattr(error, "retry_after", None)
    if isinstance(value, timedelta):
        return max(0.0, value.total_seconds())
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    return None


def _is_transient_network_error(error: BaseException) -> bool:
    # PTB's NetworkError and TimedOut are intentionally detected by class name
    # to keep this module independently testable and avoid coupling to PTB internals.
    return type(error).__name__ in {"NetworkError", "TimedOut", "ConnectTimeout", "ReadTimeout"}


async def telegram_api_call(
    operation: Callable[..., Awaitable[Any]],
    *args: Any,
    retry_prepare: Optional[Callable[[], Any]] = None,
    **kwargs: Any,
) -> Any:
    """Run a Telegram API operation with bounded concurrency and safe retries.

    RetryAfter is always honored. Only transient transport failures are retried;
    BadRequest/forbidden/invalid payload errors are returned to the caller.
    """
    async with _TELEGRAM_SEMAPHORE:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as exc:
                retry_after = _retry_after_seconds(exc)
                transient = _is_transient_network_error(exc)
                if retry_after is None and not transient:
                    raise
                if attempt >= _MAX_ATTEMPTS:
                    raise
                if retry_prepare is not None:
                    retry_prepare()
                delay = retry_after if retry_after is not None else min(2 ** (attempt - 1), 4)
                logger.warning(
                    "Telegram request transient failure (%s), retry %s/%s after %.2fs",
                    type(exc).__name__, attempt, _MAX_ATTEMPTS - 1, delay,
                )
                await asyncio.sleep(delay)
    raise RuntimeError("Telegram API retry loop exited unexpectedly")
