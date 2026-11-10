# Stage 3 — Queue & Task Orchestration

## Changes

- Added atomic multi-job submission: a session batch is either registered and enqueued as a whole chunk, or not enqueued at all.
- Preserved pending Telegram file IDs until their corresponding jobs have actually entered the AI queue. A queue-capacity race can no longer silently discard the remainder of a batch.
- Added bounded batch refill. Sessions larger than the configured queue capacity are submitted in chunks as workers complete jobs, keeping memory bounded without requiring users to manually split large sessions.
- Added per-user flush locks to prevent two completion callbacks from submitting the same pending files twice.
- Counted received files at intake time and tracked failed jobs separately, so progress accounting includes files still waiting for queue capacity and failures do not leave finalization permanently pending.
- Added terminal-job callbacks to refill the queue after success or failure and to complete sessions when all jobs have reached a terminal state.
- Made active-user release owner-aware. A stale cancellation/finalizer can no longer release another user's processing reservation.
- Updated cancellation and queue-full paths to preserve pending files and advance the waiting room safely.
- Replaced the stale hard-coded “5 workers” waiting-room message with wording that reflects bounded batch processing.

## Validation

- `python -m compileall -q .` — passed.
- `pytest -q` — 10 passed.
- Added tests for atomic submission, active-user ownership, duplicate waiting-room entries, pending-file preservation, and failed-job counters.

## Known limitations

- Queues, active jobs, and session state are still in memory. A process or host restart can lose in-flight work; durable recovery is a separate deployment/persistence task.
- This environment does not contain the Telegram runtime dependencies and does not have live Telegram/Gemini credentials, so live integration and host-level load tests were not run.
- Ruff is not installed in this environment; lint checks were not run.
