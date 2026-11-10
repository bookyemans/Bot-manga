# Stage 7 — Telegram Delivery & User Experience

## Changes

- Added `systems/delivery/telegram_api.py` as a shared Telegram API execution layer.
- Bounded concurrent Telegram API calls to two at a time to reduce outbound bursts on small hosts.
- Added bounded retry handling for Telegram `RetryAfter` responses and transient network/time-out failures. `BadRequest` and other permanent API errors are not retried.
- Added optional stream rewind callbacks so document uploads can safely retry from byte zero after a transient failure.
- Routed translated message sends, TXT/DOCX document sends, status-message edits/sends/deletes, and maintenance notifications through the shared delivery layer.
- Reduced the default message batch to two and increased the inter-batch delay to 0.5 seconds; both are configurable through `MANGA_BOT_TELEGRAM_SEND_BATCH_SIZE` and `MANGA_BOT_TELEGRAM_SEND_DELAY_SECONDS`.
- Added a plain-text fallback when Telegram rejects MarkdownV2 formatting, preserving the translated content instead of replacing it with a generic warning.
- Delivery jobs now report a failure when one or more translated messages could not be delivered, rather than silently marking the delivery as successful.

## Validation

- Python compilation: passed.
- Telegram API helper tests: 4 passed (RetryAfter, transient network retry, permanent error no-retry, bounded attempts).
- Full project test suite: 25 passed.

## Notes

- No live Telegram API request was made; actual bot token, chat permissions, Telegram-side limits, and network conditions were not exercised.
- The shared concurrency cap is intentionally conservative and fixed at two in this stage. Per-chat pacing can be tuned through the batch size and delay settings.
