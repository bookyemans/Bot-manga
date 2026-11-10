"""Deterministic local stress checks for Void Translator's bounded job queues.

This exercises orchestration in-process without calling Telegram or Gemini.
Run: python tools/stage9_stress.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import resource
import time
import tracemalloc
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from systems.job_orchestration.queue import AsyncSingleWorkerQueue
from systems.job_orchestration.worker import JobManager, JobSubmissionResult
from systems.translation_pipeline.models.page_job import PageJob


async def run_scenario(users: int, jobs_per_user: int, capacity: int = 100) -> dict:
    ai = AsyncSingleWorkerQueue(max_size=capacity)
    delivery = AsyncSingleWorkerQueue(max_size=capacity)
    manager = JobManager(ai, delivery)
    start = time.perf_counter()

    async def submit(user_id: int):
        jobs = [
            PageJob(user_id=user_id, chat_id=user_id, image_file_id=f"u{user_id}-p{i}")
            for i in range(jobs_per_user)
        ]
        return await manager.submit_jobs(jobs), jobs

    results = await asyncio.gather(*(submit(uid) for uid in range(1, users + 1)))
    accepted = [(result, jobs) for result, jobs in results if result is JobSubmissionResult.SUCCESS]
    rejected = users - len(accepted)
    queue_size = await ai.size()

    # Verify all accepted jobs are represented once and can be drained.
    drained: list[UUID] = []
    while await ai.size():
        drained.append(await ai.dequeue())
        await ai.task_done()
    registry_count = 0
    for _, jobs in accepted:
        for job in jobs:
            if await manager.get_job(job.job_id):
                registry_count += 1
    elapsed = time.perf_counter() - start
    return {
        "users": users,
        "jobs_per_user": jobs_per_user,
        "capacity": capacity,
        "accepted_users": len(accepted),
        "rejected_users": rejected,
        "queued_jobs_before_drain": queue_size,
        "drained_jobs": len(drained),
        "unique_drained_jobs": len(set(drained)),
        "registered_accepted_jobs": registry_count,
        "elapsed_ms": round(elapsed * 1000, 3),
    }


async def main() -> None:
    logging.disable(logging.CRITICAL)
    tracemalloc.start()
    results = [
        await run_scenario(users, jobs_per_user=5)
        for users in (5, 10, 20)
    ]
    results.append(await run_scenario(20, jobs_per_user=10))
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({
        "scenarios": results,
        "python_tracemalloc_peak_bytes": peak_bytes,
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "notes": "Synthetic in-process orchestration only; no Telegram/Gemini network calls.",
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
