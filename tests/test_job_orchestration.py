import asyncio
import pytest

from systems.job_orchestration.queue import AsyncSingleWorkerQueue
from systems.job_orchestration.worker import JobManager, JobSubmissionResult
from systems.translation_pipeline.models.page_job import PageJob


@pytest.mark.asyncio
async def test_submit_jobs_is_all_or_nothing_when_queue_is_full():
    ai_queue = AsyncSingleWorkerQueue(max_size=2)
    delivery_queue = AsyncSingleWorkerQueue(max_size=2)
    manager = JobManager(ai_queue, delivery_queue)
    jobs = [PageJob(user_id=10, chat_id=10, image_file_id=f"file-{i}") for i in range(3)]

    result = await manager.submit_jobs(jobs)

    assert result is JobSubmissionResult.QUEUE_FULL
    assert await ai_queue.size() == 0
    registered = [await manager.get_job(job.job_id) for job in jobs]
    assert registered == [None, None, None]


@pytest.mark.asyncio
async def test_submit_jobs_registers_and_enqueues_complete_batch():
    ai_queue = AsyncSingleWorkerQueue(max_size=3)
    delivery_queue = AsyncSingleWorkerQueue(max_size=2)
    manager = JobManager(ai_queue, delivery_queue)
    jobs = [PageJob(user_id=10, chat_id=10, image_file_id=f"file-{i}") for i in range(3)]

    result = await manager.submit_jobs(jobs)

    assert result is JobSubmissionResult.SUCCESS
    assert await ai_queue.size() == 3
    registered = [await manager.get_job(job.job_id) for job in jobs]
    assert registered == jobs


@pytest.mark.asyncio
async def test_release_active_user_does_not_release_another_users_slot():
    manager = JobManager(AsyncSingleWorkerQueue(), AsyncSingleWorkerQueue())
    assert await manager.request_processing(10, 100, 1) is True
    assert await manager.request_processing(20, 200, 1) is False

    assert await manager.release_active_user(999) is None
    assert await manager.get_active_user() == 10

    next_user = await manager.release_active_user(10)
    assert next_user == (20, 200)
    assert await manager.get_active_user() == 20


@pytest.mark.asyncio
async def test_waiting_user_is_not_added_twice():
    manager = JobManager(AsyncSingleWorkerQueue(), AsyncSingleWorkerQueue())
    await manager.request_processing(10, 100, 1)

    assert await manager.request_processing(20, 200, 1) is False
    assert await manager.request_processing(20, 200, 5) is False
    assert len(manager._waiting_queue) == 1

@pytest.mark.asyncio
async def test_pending_file_removal_preserves_files_added_after_snapshot():
    from systems.delivery.batch import BatchManager

    batch = BatchManager()
    await batch.start_session(10, "Default Translator", "grouped")
    first = ("f1", "one.png", 1)
    second = ("f2", "two.png", 2)
    third = ("f3", "three.png", 3)
    await batch.add_pending_file(10, *first)
    await batch.add_pending_file(10, *second)

    snapshot = await batch.get_pending_files(10)
    await batch.add_pending_file(10, *third)
    await batch.remove_pending_files(10, snapshot)

    assert await batch.get_pending_files(10) == [third]
    assert await batch.get_received_count(10) == 3


@pytest.mark.asyncio
async def test_failed_job_count_is_initialized_and_reset_with_session():
    from systems.delivery.batch import BatchManager

    batch = BatchManager()
    await batch.start_session(10, "Default Translator", "grouped")
    assert await batch.get_failed_count(10) == 0
    assert await batch.increment_failed_count(10) == 1
    await batch.clear_session(10)
    assert await batch.get_failed_count(10) == 0


def test_queue_rejects_unbounded_or_invalid_capacity():
    import pytest

    for value in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            AsyncSingleWorkerQueue(max_size=value)


@pytest.mark.asyncio
async def test_queue_snapshot_reports_bounded_capacity():
    from uuid import uuid4

    queue = AsyncSingleWorkerQueue(max_size=2)
    before = queue.snapshot()
    assert (before.size, before.capacity, before.available, before.full) == (0, 2, 2, False)

    await queue.enqueue(uuid4())
    after = queue.snapshot()
    assert (after.size, after.capacity, after.available, after.full) == (1, 2, 1, False)


@pytest.mark.asyncio
async def test_queue_join_waits_for_task_acknowledgement():
    from uuid import uuid4

    queue = AsyncSingleWorkerQueue(max_size=1)
    await queue.enqueue(uuid4())
    job_id = await queue.dequeue()
    waiter = asyncio.create_task(queue.join())
    await asyncio.sleep(0)
    assert not waiter.done()
    await queue.task_done()
    await asyncio.wait_for(waiter, timeout=0.2)
