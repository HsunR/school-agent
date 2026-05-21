"""Unit tests for QueueService."""

from unittest.mock import MagicMock

import pytest

from app.services.queue_service import QueueService, QueueTask


@pytest.fixture
def chroma_mock():
    m = MagicMock()
    m.upload = MagicMock(return_value={"inserted": 5, "skipped": 0})
    return m


@pytest.mark.asyncio
async def test_enqueue_when_idle_succeeds(chroma_mock):
    svc = QueueService(chroma_mock)
    task = QueueTask(id="t1", filename="test.txt", category="student_manual", chunks=["a", "b"])
    await svc.enqueue(task)
    assert svc._queue.qsize() == 1


@pytest.mark.asyncio
async def test_enqueue_when_busy_raises(chroma_mock):
    svc = QueueService(chroma_mock)
    task1 = QueueTask(id="t1", filename="a.txt", category="student_manual", chunks=["x"])
    task2 = QueueTask(id="t2", filename="b.txt", category="student_manual", chunks=["y"])
    await svc.enqueue(task1)
    svc._busy = True
    with pytest.raises(RuntimeError, match="Queue is busy"):
        await svc.enqueue(task2)


@pytest.mark.asyncio
async def test_enqueue_when_pending_raises(chroma_mock):
    svc = QueueService(chroma_mock)
    task1 = QueueTask(id="t1", filename="a.txt", category="student_manual", chunks=["x"])
    task2 = QueueTask(id="t2", filename="b.txt", category="student_manual", chunks=["y"])
    await svc.enqueue(task1)
    with pytest.raises(RuntimeError, match="Queue is busy"):
        await svc.enqueue(task2)


@pytest.mark.asyncio
async def test_get_status_idle(chroma_mock):
    svc = QueueService(chroma_mock)
    status = svc.get_status()
    assert status["busy"] is False
    assert status["pending"] == 0
    assert status["current_task"] is None


@pytest.mark.asyncio
async def test_get_status_after_enqueue(chroma_mock):
    svc = QueueService(chroma_mock)
    task = QueueTask(id="t1", filename="doc.txt", category="student_manual", chunks=["a", "b"])
    await svc.enqueue(task)
    status = svc.get_status()
    assert status["busy"] is False
    assert status["pending"] == 1


@pytest.mark.asyncio
async def test_clear_drains_queue(chroma_mock):
    svc = QueueService(chroma_mock)
    task = QueueTask(id="t1", filename="a.txt", category="student_manual", chunks=["x"])
    await svc.enqueue(task)
    svc.clear()
    await svc._worker_loop()
    assert svc._queue.empty()
    assert svc._cancel_flag is False
    status = svc.get_status()
    assert status["busy"] is False


@pytest.mark.asyncio
async def test_clear_when_idle_noop(chroma_mock):
    svc = QueueService(chroma_mock)
    # Clear when idle
    svc.clear()
    # Should still be able to enqueue
    task = QueueTask(id="t1", filename="test.txt", category="student_manual", chunks=["a", "b"])
    await svc.enqueue(task)
    await svc._worker_loop()
    assert chroma_mock.upload.called
    status = svc.get_status()
    assert status["busy"] is False


@pytest.mark.asyncio
async def test_worker_processes_task(chroma_mock):
    svc = QueueService(chroma_mock)
    task = QueueTask(id="t1", filename="doc.txt", category="student_manual", chunks=["chunk1", "chunk2"])
    await svc.enqueue(task)
    await svc._worker_loop()
    assert chroma_mock.upload.call_count == 1
    status = svc.get_status()
    assert status["busy"] is False
    assert status["pending"] == 0


@pytest.mark.asyncio
async def test_worker_updates_progress(chroma_mock):
    svc = QueueService(chroma_mock)
    results = []

    def slow_upload(cat, chunks):
        results.append(len(chunks))
        return {"inserted": len(chunks), "skipped": 0}

    chroma_mock.upload = MagicMock(side_effect=slow_upload)
    chunks = [f"chunk{i}" for i in range(100)]
    task = QueueTask(id="t1", filename="big.txt", category="student_manual", chunks=chunks)
    await svc.enqueue(task)
    await svc._worker_loop()
    assert chroma_mock.upload.call_count == 2
    assert results == [50, 50]
