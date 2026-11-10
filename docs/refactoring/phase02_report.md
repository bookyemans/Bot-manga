# Phase 02 — Core Contracts and Dependency Access

## Scope
Introduce lightweight structural contracts and a single typed accessor for the application-scoped service container. Preserve the existing modular-monolith composition root and avoid adding a DI framework or runtime dependency.

## Changes
- Added `shared/contracts.py` with runtime-checkable Protocol contracts for database lifecycle, event bus, AI provider, job lifecycle, delivery, and error notification.
- Added `shared/dependencies.py` with `get_container(bot_data)`, a single checked access path that raises an actionable `RuntimeError` before initialization or when the stored object has the wrong type.
- Updated access-control and delivery middleware to use the checked dependency accessor instead of unchecked dictionary indexing.
- Kept `ServiceContainer` as the concrete application composition object; no service construction order or runtime lifecycle was changed.
- Added tests for successful container retrieval, missing initialization, and invalid container values.

## Validation
- `python -m compileall -q shared systems main.py tests` — passed.
- `python -m pytest -q tests/test_dependency_contracts.py tests/test_release_config.py tests/test_job_orchestration.py` — 14 passed.
- `python -m pytest -q` — 39 passed in 3.38 seconds.

## Compatibility and safety
- No database schema or stored data changes.
- No new runtime dependencies.
- No external services, Redis, Celery, or microservices introduced.
- Existing `bot_data["container"]` storage key and concrete `ServiceContainer` shape retained.
- No source modules were deleted or moved.
- Live Telegram/Gemini integration and target-host resource tests were not run.

## Gate
Phase 02 implementation and automated test gate passed. Await explicit approval before Phase 03.
