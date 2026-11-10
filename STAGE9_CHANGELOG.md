# Stage 9 — Load and Stability Testing

## Scope

- Added reproducible in-process queue stress harness: `tools/stage9_stress.py`.
- Added a representative Pillow image benchmark: `tools/stage9_image_benchmark.py`.
- Added automated stress tests for 20 concurrent submitters and waiting-user promotion.
- Reduced peak image-processing memory on the common RGB/no-EXIF path by avoiding redundant full-resolution copies. EXIF rotations and transparency handling remain supported.

## Validation performed

- `pytest -q`: 31 passed.
- Queue scenarios with 5, 10, and 20 concurrent submitters (5 jobs each): 25, 50, and 100 jobs enqueued and drained; no duplicate IDs.
- Queue saturation scenario (20 submitters × 10 jobs, capacity 100): 10 complete batches accepted and 10 rejected atomically; exactly 100 jobs remained queued, with no partial batch insertion.
- 19 waiting users were promoted exactly once in FIFO order when priorities were equal.
- Representative 3000×3000 RGB image optimization: output resized to 1280px maximum side.

## Image benchmark observation

On the same execution environment and input image, before the RGB-copy optimization the process peak RSS was about 223,608 KiB and elapsed time about 0.687 s. After the optimization, peak RSS was about 153,312 KiB and elapsed time about 0.368 s. This is an observed local comparison, not a guaranteed production figure.

## Important limitations

- These are synthetic local tests, not a live Telegram/Gemini integration test.
- The test machine is not the target 0.5 CPU / 512 MB host; its RSS measurements cannot certify the production memory budget.
- External API rate limits, provider latency, network interruptions, and real hosting throttling remain to be tested on the destination host.
