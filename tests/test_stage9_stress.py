import pytest

from systems.job_orchestration.queue import AsyncSingleWorkerQueue
from systems.job_orchestration.worker import JobManager


@pytest.mark.asyncio
async def test_twenty_concurrent_users_fit_bounded_queue_without_duplicates():
    ai = AsyncSingleWorkerQueue(max_size=100)
    manager = JobManager(ai, AsyncSingleWorkerQueue(max_size=100))

    results = await asyncio_gather_submissions(manager)

    assert results == [True] * 20
    assert await ai.size() == 100
    seen = set()
    for _ in range(100):
        job_id = await ai.dequeue()
        assert job_id not in seen
        seen.add(job_id)
        await ai.task_done()
    assert len(seen) == 100


async def asyncio_gather_submissions(manager):
    import asyncio
    from systems.translation_pipeline.models.page_job import PageJob
    from systems.job_orchestration.worker import JobSubmissionResult

    async def submit(user_id):
        jobs = [PageJob(user_id=user_id, chat_id=user_id, image_file_id=f"{user_id}-{i}") for i in range(5)]
        return await manager.submit_jobs(jobs) is JobSubmissionResult.SUCCESS

    return await asyncio.gather(*(submit(user_id) for user_id in range(1, 21)))


@pytest.mark.asyncio
async def test_waiting_users_are_promoted_once_in_fifo_order_for_equal_priority():
    manager = JobManager(AsyncSingleWorkerQueue(), AsyncSingleWorkerQueue())
    assert await manager.request_processing(1, 101, 1)
    for user_id in range(2, 21):
        assert not await manager.request_processing(user_id, user_id + 100, 1)

    promoted = []
    for _ in range(19):
        next_user = await manager.release_active_user()
        assert next_user is not None
        promoted.append(next_user[0])

    assert promoted == list(range(2, 21))
    assert await manager.get_active_user() == 20


@pytest.mark.asyncio
async def test_capacity_saturation_rejects_whole_batches_without_registry_leaks():
    from systems.job_orchestration.worker import JobSubmissionResult
    from systems.translation_pipeline.models.page_job import PageJob

    ai = AsyncSingleWorkerQueue(max_size=10)
    manager = JobManager(ai, AsyncSingleWorkerQueue(max_size=10))

    accepted = [PageJob(user_id=1, chat_id=1, image_file_id=f"a-{i}") for i in range(5)]
    rejected = [PageJob(user_id=2, chat_id=2, image_file_id=f"b-{i}") for i in range(6)]

    assert await manager.submit_jobs(accepted) is JobSubmissionResult.SUCCESS
    assert await manager.submit_jobs(rejected) is JobSubmissionResult.QUEUE_FULL
    assert ai.snapshot().size == 5
    assert ai.snapshot().available == 5
    for job in rejected:
        assert await manager.get_job(job.job_id) is None
    for job in accepted:
        assert await manager.get_job(job.job_id) is not None
