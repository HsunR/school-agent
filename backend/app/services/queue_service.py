"""In-memory async task queue for admin file upload processing."""

import asyncio
import logging
from typing import NamedTuple, TypedDict

from app.rag.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)

UPLOAD_BATCH_SIZE = 50


class QueueTask(NamedTuple):
    id: str
    filename: str
    category: str
    chunks: list[str]


class QueueStatus(TypedDict):
    busy: bool
    pending: int
    current_task: str | None
    progress: int
    total: int


class QueueService:
    """Manages an in-memory async queue for file upload processing.

    Enforces single-task concurrency: only one task can be processed at a time
    and at most one task can wait in the queue. New enqueue attempts while
    busy or non-empty raise ``RuntimeError``.
    """

    def __init__(self, chroma_manager: ChromaManager) -> None:
        self._chroma = chroma_manager
        self._queue: asyncio.Queue[QueueTask] = asyncio.Queue()
        self._busy = False
        self._lock = asyncio.Lock()
        self._cancel_flag = False
        self._current_task: QueueTask | None = None
        self._chunk_progress = 0
        self._chunk_total = 0
        self._worker_task: asyncio.Task | None = None

    async def enqueue(self, task: QueueTask) -> None:
        """Add a task to the queue. Raises ``RuntimeError`` if busy or non-empty."""
        async with self._lock:
            if self._busy or not self._queue.empty():
                raise RuntimeError("Queue is busy, please wait for current task to complete")
            await self._queue.put(task)
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task '%s' enqueued (%d chunks)", task.filename, len(task.chunks))

    async def _worker_loop(self) -> None:
        """Background loop: process tasks one at a time until cancelled or empty."""
        while not self._cancel_flag:
            try:
                self._current_task = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            self._busy = True
            self._chunk_progress = 0
            self._chunk_total = len(self._current_task.chunks)
            try:
                await self._process_task(self._current_task)
            except (Exception, asyncio.CancelledError):
                logger.exception("Task '%s' failed", self._current_task.filename)
            finally:
                self._current_task = None
                self._busy = False
                self._chunk_progress = 0
                self._chunk_total = 0

        if self._cancel_flag:
            self._drain_and_reset()

    async def _process_task(self, task: QueueTask) -> None:
        """Process a single task by uploading chunks in batches."""
        chunks = task.chunks
        for i in range(0, len(chunks), UPLOAD_BATCH_SIZE):
            batch = chunks[i : i + UPLOAD_BATCH_SIZE]
            await asyncio.to_thread(self._chroma.upload, task.category, batch)
            self._chunk_progress += len(batch)
            logger.debug(
                "Task '%s' progress: %d/%d chunks",
                task.filename, self._chunk_progress, self._chunk_total,
            )

    def _drain_and_reset(self) -> None:
        """Drain all remaining tasks from queue and reset cancel flag."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        self._cancel_flag = False
        if count:
            logger.info("Drained %d pending tasks from queue", count)

    def get_status(self) -> QueueStatus:
        """Return current queue status."""
        return {
            "busy": self._busy,
            "pending": self._queue.qsize(),
            "current_task": self._current_task.filename if self._current_task else None,
            "progress": self._chunk_progress,
            "total": self._chunk_total,
        }

    def clear(self) -> None:
        """Signal worker to drain queue after current task finishes."""
        if self._worker_task is None or self._worker_task.done():
            self._cancel_flag = False
            return
        self._cancel_flag = True
        logger.info("Queue clear requested")
