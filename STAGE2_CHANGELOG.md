# Stage 2 — Performance & Resource Optimization

## Changes
- Added environment-driven limits for AI workers, delivery workers, thread-pool workers, Gemini HTTP connections, queue capacity, and image dimensions/pixel count.
- Set conservative defaults for small hosts: AI workers `1`, delivery workers `1`, thread pool `2`, Gemini connections `4`, and queue capacity `100` per queue.
- Updated `JobManager` to use configured worker counts instead of fixed pools of 4 AI + 2 delivery workers.
- Bounded the Gemini `aiohttp` connection pool instead of allowing up to 100 connections.
- Reworked image optimization to check dimensions before decoding, use reduced JPEG draft decoding when available, resize with `thumbnail`, apply EXIF orientation, and close temporary image objects.
- Added `.env.example` with the new resource settings and safe placeholders.
- Added image optimizer regression tests.

## Configuration variables
All variables use the `MANGA_BOT_` prefix. See `.env.example` for the complete list and defaults.

## Validation performed
- `python -m compileall -q .` — passed.
- `pytest -q tests/test_image_optimizer.py` — 4 passed.
- Settings defaults and validation smoke test — passed.
- Gemini connector-limit and JobManager worker-count smoke test — passed.

## Scope notes
- No external services or new runtime dependencies were added.
- SQLite and existing application flows were retained.
- The global single-active-user/session serialization and queue/session lifecycle defects found in Stage 1 were intentionally not changed; they belong to Stage 3 (queue/task orchestration).
- Live Telegram/Gemini integration and real 0.5-CPU/512-MB load tests were not run in this environment.
