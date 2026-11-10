# Stage 4 — Gemini Engine Reliability & Security

## Implemented

- Replaced the stale/unsupported model fallback entries with current image-capable Gemini model IDs, in a configurable order.
- Added environment settings for model order, retry count, and retry delay.
- Implemented bounded retries for timeouts, network failures, and transient HTTP statuses (408, 429, 500, 502, 503, 504), with exponential backoff, jitter, and `Retry-After` support.
- Rotates to another API key after authentication/authorization failures (401/403) rather than wasting attempts across every model for a rejected key.
- Sends the Gemini API key in the documented `x-goog-api-key` header instead of the URL query string.
- Removed partial API-key values from logs and stopped returning upstream response bodies in user-facing exception messages.
- Added response-shape validation and retained bounded HTTP connection pooling and circuit-breaker behavior.

## Configuration

See `.env.example` for:

- `MANGA_BOT_GEMINI_MODELS`
- `MANGA_BOT_GEMINI_MAX_RETRIES`
- `MANGA_BOT_GEMINI_RETRY_DELAY_SECONDS`

The first model is attempted first. Only use model IDs enabled for the Google project and API key in deployment.

## Verification

- `python -m compileall -q .` — passed.
- `pytest -q` — 15 passed.
- Added tests for retry behavior, invalid-key rotation, circuit-breaker cooldown, model/retry configuration bounds, and API-key header placement.
- No live request was made to Google Gemini; model access, quota, billing, and key permissions must be confirmed with the deployment's own credentials.

## Operational note

Google's current Gemini API key guidance says standard API keys are being rejected from September 2026; deployments should use a current authorization key and verify it is active and restricted to the Gemini API. This project continues to accept keys through its existing user-key and environment-key flows; no existing database key values were modified.
