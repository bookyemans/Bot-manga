"""Repeatable bounded-queue capacity benchmark (no network or external services).

Run from the project root: python tools/phase11_capacity_benchmark.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import platform
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from systems.job_orchestration.queue import AsyncSingleWorkerQueue
from systems.job_orchestration.worker import JobManager, JobSubmissionResult
from systems.translation_pipeline.models.page_job import PageJob


async def scenario(users: int, pages_per_user: int, capacity: int) -> dict:
    ai_queue = AsyncSingleWorkerQueue(max_size=capacity)
    manager = JobManager(ai_queue, AsyncSingleWorkerQueue(max_size=capacity))
    start = time.perf_counter()

    async def submit(user_id: int):
        jobs = [PageJob(user_id=user_id, chat_id=user_id,
                        image_file_id=f"{user_id}-{page}")
                for page in range(pages_per_user)]
        result = await manager.submit_jobs(jobs)
        return result, jobs

    submissions = await asyncio.gather(*(submit(uid) for uid in range(1, users + 1)))
    accepted = [(result, jobs) for result, jobs in submissions
                if result is JobSubmissionResult.SUCCESS]
    rejected = len(submissions) - len(accepted)
    registered = 0
    for _, jobs in accepted:
        for job in jobs:
            if await manager.get_job(job.job_id) is not None:
                registered += 1
    snapshot = ai_queue.snapshot()
    unique_ids = set()
    while await ai_queue.size():
        unique_ids.add(await ai_queue.dequeue())
        await ai_queue.task_done()
    await ai_queue.join()
    return {
        "users": users,
        "pages_per_user": pages_per_user,
        "capacity": capacity,
        "accepted_users": len(accepted),
        "rejected_users": rejected,
        "queued_at_peak": snapshot.size,
        "queue_full_at_peak": snapshot.full,
        "registered_accepted_jobs": registered,
        "unique_drained_jobs": len(unique_ids),
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
    }


async def main() -> None:
    logging.disable(logging.CRITICAL)
    tracemalloc.start()
    results = [
        await scenario(5, 5, 100),
        await scenario(10, 5, 100),
        await scenario(20, 5, 100),
        await scenario(20, 10, 100),
    ]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "tracemalloc_peak_bytes": peak,
        "scenarios": results,
        "scope": "Synthetic in-process queue/registry benchmark; excludes Telegram, Gemini, SQLite and image decoding.",
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
