# systems/ai_engine/gemini.py
from __future__ import annotations

import asyncio
import base64
import logging
import random
import time
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

import aiohttp

try:
    import orjson
    USE_ORJSON = True
except ImportError:
    import json
    USE_ORJSON = False

from systems.ai_engine.base import BaseAIProvider
from systems.ai_engine.exceptions import ServiceUnavailableError, AIProcessingError

logger = logging.getLogger(__name__)

class _GeminiHTTPError(RuntimeError):
    def __init__(self, status: int, message: str, retry_after: Optional[float] = None) -> None:
        # Upstream error bodies can echo request metadata or sensitive values. Keep
        # only the HTTP status in the exception message and diagnostics.
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retry_after = retry_after


class GeminiProvider(BaseAIProvider):
    """Gemini REST provider with bounded retries, key rotation and circuit breaker."""

    # Stable, image-capable model IDs confirmed against Google's model catalogue.
    # User-configurable order allows operators to control cost/latency trade-offs.
    FALLBACK_MODELS: List[str] = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]
    RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}
    INVALID_KEY_STATUSES = {401, 403}

    def __init__(
        self,
        timeout: float = 45.0,
        cb_threshold: int = 5,
        cb_cooldown: int = 60,
        connector_limit: int = 4,
        models: Optional[Sequence[str]] = None,
        max_retries: int = 2,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._connector_limit = max(1, int(connector_limit))
        self._session: Optional[aiohttp.ClientSession] = None
        self.models = [m.strip() for m in (models or self.FALLBACK_MODELS) if m and m.strip()]
        if not self.models:
            raise ValueError("At least one Gemini model must be configured")
        self.max_retries = max(1, min(int(max_retries), 3))
        self.retry_delay_seconds = max(0.1, min(float(retry_delay_seconds), 15.0))
        self._cb_threshold = max(1, int(cb_threshold))
        self._cb_cooldown = max(1, int(cb_cooldown))
        self._cb_failures = 0
        self._cb_open_until = 0.0
        self._cb_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self._connector_limit,
                limit_per_host=self._connector_limit,
                keepalive_timeout=30,
                force_close=False,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(timeout=self._timeout, connector=connector)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _check_circuit(self) -> None:
        async with self._cb_lock:
            now = time.monotonic()
            if self._cb_failures >= self._cb_threshold and now < self._cb_open_until:
                remaining = max(1, int(self._cb_open_until - now))
                raise ServiceUnavailableError(
                    f"Gemini service circuit is open; retry in about {remaining}s."
                )
            # After cooldown, allow a probe request. The regular worker limit
            # keeps probes bounded on the target low-resource host.

    async def _record_success(self) -> None:
        async with self._cb_lock:
            if self._cb_failures:
                logger.info("Gemini circuit breaker closed after a successful request")
            self._cb_failures = 0
            self._cb_open_until = 0.0

    async def _record_failure(self) -> None:
        async with self._cb_lock:
            self._cb_failures += 1
            if self._cb_failures >= self._cb_threshold:
                self._cb_open_until = time.monotonic() + self._cb_cooldown
                logger.warning("Gemini circuit breaker opened for %ss", self._cb_cooldown)

    async def _sleep_before_retry(self, attempt: int, retry_after: Optional[float] = None) -> None:
        # Exponential backoff with small jitter; honor server Retry-After when present.
        delay = min(self.retry_delay_seconds * (2 ** (attempt - 1)), 8.0)
        if retry_after is not None:
            delay = max(delay, min(max(0.0, retry_after), 15.0))
        await asyncio.sleep(delay + random.uniform(0.0, min(0.25, delay / 4)))

    async def extract_raw_json(
        self,
        image_bytes: bytes,
        job_id: UUID,
        prompt_text: str,
        api_keys: List[str],
    ) -> Dict[str, Any]:
        await self._check_circuit()
        clean_keys = list(dict.fromkeys(k.strip() for k in api_keys if isinstance(k, str) and k.strip()))
        if not clean_keys:
            await self._record_failure()
            raise AIProcessingError(f"JobID={job_id} | No API keys provided.")

        # Base64 expands image data by ~33%; retain a single encoded copy per request.
        b64_image = (await asyncio.to_thread(base64.b64encode, image_bytes)).decode("ascii")
        payload = self._build_payload(b64_image, prompt_text)
        session = await self._get_session()
        last_exception: Optional[Exception] = None

        for key_idx, api_key in enumerate(clean_keys, start=1):
            key_rejected = False
            for model_name in self.models:
                for attempt in range(1, self.max_retries + 1):
                    try:
                        logger.info(
                            "JobID=%s | Gemini key slot %s/%s | model=%s | attempt=%s/%s",
                            job_id, key_idx, len(clean_keys), model_name, attempt, self.max_retries,
                        )
                        result = await self._call_model(session, model_name, payload, job_id, api_key)
                        await self._record_success()
                        logger.info("JobID=%s | Gemini request succeeded with model=%s", job_id, model_name)
                        return result
                    except _GeminiHTTPError as exc:
                        last_exception = exc
                        if exc.status in self.INVALID_KEY_STATUSES:
                            logger.warning("JobID=%s | Gemini rejected key slot %s (HTTP %s)", job_id, key_idx, exc.status)
                            key_rejected = True
                            break
                        if exc.status in self.RETRYABLE_STATUSES and attempt < self.max_retries:
                            logger.warning("JobID=%s | transient Gemini HTTP %s; retrying", job_id, exc.status)
                            await self._sleep_before_retry(attempt, exc.retry_after)
                            continue
                        logger.warning("JobID=%s | model %s returned HTTP %s", job_id, model_name, exc.status)
                        break
                    except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
                        last_exception = exc
                        if attempt < self.max_retries:
                            logger.warning("JobID=%s | Gemini network/timeout error; retrying", job_id)
                            await self._sleep_before_retry(attempt)
                            continue
                        logger.warning("JobID=%s | Gemini network request failed after retries", job_id)
                        break
                    except (ValueError, TypeError) as exc:
                        last_exception = exc
                        logger.warning("JobID=%s | invalid Gemini response from model %s: %s", job_id, model_name, str(exc)[:200])
                        break
                    except Exception as exc:
                        last_exception = exc
                        logger.exception("JobID=%s | unexpected Gemini provider error", job_id)
                        break
                if key_rejected:
                    break

        await self._record_failure()
        # Do not include API keys or full upstream response bodies in user-facing errors.
        reason = type(last_exception).__name__ if last_exception else "unknown error"
        raise AIProcessingError(
            f"All configured Gemini keys/models failed for JobID={job_id}. Last failure type: {reason}."
        )

    def _build_payload(self, b64_image: str, prompt_text: str) -> Dict[str, Any]:
        return {
            "contents": [{
                "parts": [
                    {"text": "Extract all text elements in Arabic reading order (Top-to-Bottom, Right-to-Left)."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}},
                ]
            }],
            "system_instruction": {"parts": [{"text": prompt_text}]},
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1},
        }

    async def _call_model(
        self,
        session: aiohttp.ClientSession,
        model_name: str,
        payload: Dict[str, Any],
        job_id: UUID,
        api_key: str,
    ) -> Dict[str, Any]:
        # Use the documented API-key header so credentials do not appear in URLs/logs.
        url = f"{self._base_url}/{model_name}:generateContent"
        async with session.post(url, json=payload, headers={"x-goog-api-key": api_key}) as response:
            if response.status != 200:
                retry_after = None
                try:
                    retry_after = float(response.headers.get("Retry-After", ""))
                except (TypeError, ValueError):
                    pass
                error_text = await response.text()
                # Avoid propagating response bodies that may contain sensitive data.
                raise _GeminiHTTPError(response.status, error_text, retry_after)
            data = await response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            prompt_feedback = data.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason", "unknown")
            raise ValueError(f"Gemini returned no candidates (block reason: {block_reason})")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts or not isinstance(parts[0].get("text"), str):
            raise ValueError("Gemini response did not contain text output")
        raw_text = parts[0]["text"]
        try:
            parsed = orjson.loads(raw_text) if USE_ORJSON else json.loads(raw_text)
        except Exception as exc:
            raise ValueError("Gemini returned malformed JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response JSON must be an object")
        return parsed
