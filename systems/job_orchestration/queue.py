# systems/job_orchestration/queue.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from shared.logger import job_logger


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    """Small immutable view of queue pressure for health checks and logs."""

    size: int
    capacity: int
    available: int
    full: bool


class AsyncSingleWorkerQueue:
    """
    An asynchronous FIFO queue implementation.
    Designed to hold only Job IDs (UUIDs) to maintain a stateless architecture.
    """
    def __init__(self, max_size: int = 100) -> None:
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 1:
            raise ValueError("max_size must be a positive integer; unbounded queues are disabled")
        self._queue: asyncio.Queue[UUID] = asyncio.Queue(maxsize=max_size)
        self._max_size = max_size

    async def enqueue(self, job_id: UUID) -> None:
        await self._queue.put(job_id)
        job_logger._logger.info(f"JobID={job_id} | Event=ENQUEUED | QueueSize={self._queue.qsize()}")

    def enqueue_nowait(self, job_id: UUID) -> None:
        self._queue.put_nowait(job_id)
        job_logger._logger.info(f"JobID={job_id} | Event=ENQUEUED | QueueSize={self._queue.qsize()}")

    def enqueue_many_nowait(self, job_ids: list[UUID]) -> None:
        """Enqueue a group atomically from the event loop's point of view.

        There is no await between the capacity check and put_nowait calls in
        the caller, so consumers cannot interleave and create a partial batch.
        """
        if len(job_ids) > self._queue.maxsize - self._queue.qsize():
            raise asyncio.QueueFull
        for job_id in job_ids:
            self._queue.put_nowait(job_id)
        if job_ids:
            job_logger._logger.info(
                "Batch enqueued | Count=%s | QueueSize=%s",
                len(job_ids), self._queue.qsize(),
            )

    @property
    def capacity(self) -> int:
        return self._max_size

    async def dequeue(self) -> UUID:
        return await self._queue.get()

    async def task_done(self) -> None:
        self._queue.task_done()

    async def size(self) -> int:
        return self._queue.qsize()

    def is_full(self) -> bool:
        return self._queue.full()

    def snapshot(self) -> QueueSnapshot:
        current = self._queue.qsize()
        return QueueSnapshot(
            size=current,
            capacity=self._max_size,
            available=max(0, self._max_size - current),
            full=current >= self._max_size,
        )

    async def join(self) -> None:
        """Wait until every enqueued item has been acknowledged by a worker."""
        await self._queue.join()