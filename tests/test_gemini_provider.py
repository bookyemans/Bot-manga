from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from systems.ai_engine.gemini import GeminiProvider, _GeminiHTTPError
from systems.ai_engine.exceptions import ServiceUnavailableError


@pytest.mark.asyncio
async def test_retry_count_is_configurable_and_bounded(monkeypatch):
    provider = GeminiProvider(models=["gemini-test"], max_retries=2, retry_delay_seconds=0.1)
    calls = 0

    async def fail_then_succeed(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _GeminiHTTPError(503, "temporarily unavailable")
        return {"ok": True}

    async def no_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr(provider, "_get_session", _fake_session)
    monkeypatch.setattr(provider, "_call_model", fail_then_succeed)
    monkeypatch.setattr(provider, "_sleep_before_retry", no_sleep)
    result = await provider.extract_raw_json(b"image", uuid4(), "prompt", ["secret-key"])
    assert result == {"ok": True}
    assert calls == 2


async def _fake_session():
    return object()


@pytest.mark.asyncio
async def test_invalid_key_skips_remaining_models_and_tries_next_key(monkeypatch):
    provider = GeminiProvider(models=["model-a", "model-b"], max_retries=1)
    seen = []

    async def fake_call(session, model, payload, job_id, key):
        seen.append((model, key))
        if key == "bad-key":
            raise _GeminiHTTPError(403, "key rejected")
        return {"translated": True}

    monkeypatch.setattr(provider, "_get_session", _fake_session)
    monkeypatch.setattr(provider, "_call_model", fake_call)
    result = await provider.extract_raw_json(b"image", uuid4(), "prompt", ["bad-key", "good-key"])
    assert result == {"translated": True}
    assert seen == [("model-a", "bad-key"), ("model-a", "good-key")]


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_during_cooldown():
    provider = GeminiProvider(cb_threshold=1, cb_cooldown=30)
    await provider._record_failure()
    with pytest.raises(ServiceUnavailableError):
        await provider._check_circuit()


def test_model_list_and_retry_limits_are_sanitized():
    provider = GeminiProvider(models=[" model-a ", "", "model-b"], max_retries=99)
    assert provider.models == ["model-a", "model-b"]
    assert provider.max_retries == 3

@pytest.mark.asyncio
async def test_api_key_is_sent_in_header_not_url():
    provider = GeminiProvider(models=["model-a"])
    captured = {}

    class FakeResponse:
        status = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}

    class FakeSession:
        def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return FakeResponse()

    result = await provider._call_model(FakeSession(), "model-a", {}, uuid4(), "sensitive-key")
    assert result == {"ok": True}
    assert "sensitive-key" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "sensitive-key"


def test_upstream_error_message_does_not_retain_response_body():
    error = _GeminiHTTPError(403, "sensitive-provider-detail secret-value")
    assert str(error) == "HTTP 403"
    assert "secret-value" not in str(error)
