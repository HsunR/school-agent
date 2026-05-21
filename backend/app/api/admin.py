"""Admin API router for knowledge base management."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.settings import get_settings
from app.rag.chroma_manager import ChromaManager, ALL_COLLECTIONS
from app.rag.embeddings import EmbeddingClient
from app.schemas.admin import (
    ClearResponse,
    DataPreviewResponse,
    DeleteResponse,
    QueueClearResponse,
    QueueStatusResponse,
    StatsResponse,
    UploadRequest,
)
from app.services.queue_service import QueueService, QueueTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Lazy-init singletons
_chroma: Optional[ChromaManager] = None
_queue_service: Optional[QueueService] = None


def _get_chroma() -> ChromaManager:
    global _chroma
    if _chroma is None:
        settings = get_settings()
        embedding = EmbeddingClient(settings)
        _chroma = ChromaManager(settings, embedding)
    return _chroma


def _get_queue_service() -> QueueService:
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService(_get_chroma())
    return _queue_service


@router.post("/upload", status_code=202)
async def upload_data(request: UploadRequest) -> dict:
    """Upload text content — split by delimiter and enqueue for async processing."""
    chunks = request.content.split(request.delimiter)
    chunks = [c.strip() for c in chunks if c.strip()]
    if not chunks:
        raise HTTPException(status_code=400, detail="No valid chunks after splitting")

    queue = _get_queue_service()
    task = QueueTask(
        id=str(uuid.uuid4()),
        filename=f"{request.category[:20]}_{uuid.uuid4().hex[:8]}",
        category=request.category,
        chunks=chunks,
    )
    try:
        await queue.enqueue(task)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"queued": True, "queue_size": 1}


@router.get("/data", response_model=DataPreviewResponse)
async def preview_data(
    category: str = Query(...),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> DataPreviewResponse:
    """Preview stored chunks with pagination."""
    if category not in ALL_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    chroma = _get_chroma()
    result = chroma.get_data(category, page=page, size=size)
    return DataPreviewResponse(
        ids=result["ids"],
        documents=result["documents"],
        metadatas=result["metadatas"],
        total=result["total"],
        page=page,
        size=size,
    )


@router.delete("/data", response_model=ClearResponse | DeleteResponse)
async def delete_data(
    category: str = Query(...),
    id: Optional[str] = Query(default=None),
) -> ClearResponse | DeleteResponse:
    """Delete specific document(s) from a knowledge base collection.

    * If ``id`` is provided — delete that single document.
    * If ``id`` is omitted — delete all documents in the category.
    """
    if category not in ALL_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    chroma = _get_chroma()
    if id is not None:
        count = chroma.delete_by_id(category, [id])
        return DeleteResponse(deleted=count)
    else:
        chroma.clear(category)
        return ClearResponse(cleared=[category])


@router.get("/stats", response_model=list[StatsResponse])
async def get_stats() -> list[StatsResponse]:
    """Get statistics for all collections."""
    chroma = _get_chroma()
    results = []
    for cat in ALL_COLLECTIONS:
        try:
            s = chroma.stats(cat)
            results.append(StatsResponse(
                category=s["category"], total_count=s["total_count"]
            ))
        except Exception:
            results.append(StatsResponse(category=cat, total_count=0))
    return results


@router.get("/queue", response_model=QueueStatusResponse)
async def get_queue_status() -> QueueStatusResponse:
    """Get current queue status (busy, pending, current task, progress)."""
    queue = _get_queue_service()
    status = queue.get_status()
    return QueueStatusResponse(**status)


@router.post("/queue/clear", response_model=QueueClearResponse)
async def clear_queue() -> QueueClearResponse:
    """Clear all pending tasks after current task completes."""
    queue = _get_queue_service()
    queue.clear()
    return QueueClearResponse(message="Queue cleared. Current task will finish before queue is emptied.")
