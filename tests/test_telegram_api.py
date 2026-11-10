import asyncio

import pytest

from systems.delivery.telegram_api import telegram_api_call


class RetryAfter(Exception):
    def __init__(self, seconds):
        self.retry_after = seconds


class NetworkError(Exception):
    pass


class BadRequest(Exception):
    pass


@pytest.mark.asyncio
async def test_retry_after_is_honored_and_file_rewound(monkeypatch):
    sleeps = []
    monkeypatch.setattr(asyncio, "sleep", lambda delay: _record_sleep(sleeps, delay))
    calls = 0
    rewinds = []

    async def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RetryAfter(0.25)
        return "ok"

    result = await telegram_api_call(operation, retry_prepare=lambda: rewinds.append(0))
    assert result == "ok"
    assert calls == 2
    assert rewinds == [0]
    assert sleeps == [0.25]


async def _record_sleep(sleeps, delay):
    sleeps.append(delay)


@pytest.mark.asyncio
async def test_transient_network_error_retries(monkeypatch):
    sleeps = []
    monkeypatch.setattr(asyncio, "sleep", lambda delay: _record_sleep(sleeps, delay))
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise NetworkError("temporary")
        return 7

    assert await telegram_api_call(operation) == 7
    assert calls == 2
    assert sleeps == [1]


@pytest.mark.asyncio
async def test_bad_request_is_not_retried():
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        raise BadRequest("invalid payload")

    with pytest.raises(BadRequest):
        await telegram_api_call(operation)
    assert calls == 1


@pytest.mark.asyncio
async def test_retries_are_bounded():
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        raise NetworkError("still down")

    with pytest.raises(NetworkError):
        await telegram_api_call(operation)
    assert calls == 3
