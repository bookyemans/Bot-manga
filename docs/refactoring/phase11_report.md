# Phase 11 — Performance and Capacity Validation

## Scope

This phase adds repeatable, local capacity/performance checks and a regression test for bounded-queue saturation. It does not change production queue behavior, database schema, dependencies, Telegram handlers, or translation logic.

## Changes

- Added `tools/phase11_capacity_benchmark.py` to measure bounded queue admission, registry consistency, unique draining, and elapsed time for representative concurrent-user scenarios.
- Added a regression test to `tests/test_stage9_stress.py` proving that an oversized batch is rejected atomically and rejected jobs are not retained in the in-memory registry.

## Verification

- Baseline before phase changes: **58 passed** (`python -m pytest -q`).
- Final suite: **59 passed** (`python -m pytest -q`, 3.58 seconds).
- `python -m compileall -q .`: completed successfully.
- Capacity benchmark: `python tools/phase11_capacity_benchmark.py` completed successfully.

### Capacity benchmark results

Environment: Python 3.13.5, Linux x86_64. Queue capacity: 100.

| Concurrent users | Jobs/user | Accepted users | Rejected users | Peak queued | Unique drained | Elapsed |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 5 | 5 | 0 | 25 | 25 | 1.674 ms |
| 10 | 5 | 10 | 0 | 50 | 50 | 2.253 ms |
| 20 | 5 | 20 | 0 | 100 | 100 | 4.458 ms |
| 20 | 10 | 10 | 10 | 100 | 100 | 6.546 ms |

The benchmark reported a `tracemalloc` peak of 295,574 bytes for its synthetic queue/registry workload. All accepted jobs were registered and drained uniquely in these runs. Under saturation, complete user batches were rejected rather than partially queued.

### Image optimization spot measurement

`python tools/stage9_image_benchmark.py` completed for a synthetic 3000×3000 PNG:
- Input: 33,250 bytes
- Output: 9,886 bytes
- Elapsed: 0.2406 seconds
- Process peak RSS: 153,336 KiB

This is a single local spot measurement, not a controlled before/after comparison. RSS includes Python and imported libraries.

## Limits and non-claims

- These are synthetic, in-process checks; no Telegram or Gemini network traffic was generated.
- The queue benchmark does not execute the full translation pipeline and does not include image decode, SQLite, or network buffers.
- Measurements were not taken on the target 0.5 CPU / 512 MB host. The RSS number is from this development environment and must not be interpreted as target-host consumption.
- No sustained soak test, multi-process test, or production traffic test was performed.
- Queues and the job registry remain in-memory; this phase does not add persistence or crash recovery.

## Compatibility

No production runtime semantics or external interfaces were intentionally changed. No new runtime or development dependencies were added.
