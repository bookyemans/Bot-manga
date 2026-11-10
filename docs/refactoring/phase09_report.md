# Phase 09 — Telegram UI routing separation

## Scope
Extract Telegram handler and middleware registration from `main.py` into a dedicated UI registration module. This is a structural change only; it does not introduce microservices or new runtime dependencies.

## Changes
- Added `systems/delivery/ui/registration.py` with the existing middleware, command, callback-query, and message handler registration.
- Reduced `main.py` to call `register_handlers(app)` after application construction and settings injection.
- Kept middleware groups `-3`, `-2`, and `-1` in their original order.
- Kept command, callback, and message routes in their original relative order and retained their existing callbacks and filters.
- Added AST-based tests to guard separation and routing registration shape.

## Validation
- Baseline before changes: **53 passed** (`python -m pytest -q`).
- After changes: **55 passed** (`python -m pytest -q`).
- `python -m compileall -q main.py systems/delivery/ui tests/test_telegram_registration.py`: passed.

## Limitations
- `python-telegram-bot` is not installed in this execution environment, so an actual runtime import/startup of the Telegram application could not be performed. The registration tests are AST-based and verify structure, not PTB runtime dispatch behavior.
- No live Telegram bot, webhook, or polling integration test was run.
- No business logic, database schema, or external dependencies were changed.
