"""Admin API router for knowledge base management."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.settings import get_settings
from app.rag.chroma_manager import ChromaManager, ALL_COLLECTIONS
from app.rag.embeddings import EmbeddingClient
from app.schemas.admin import (
    ClearResponse,
    DataPreviewResponse,
    StatsResponse,
    UploadRequest,
    UploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Lazy-init singleton
_chroma: Optional[ChromaManager] = None


def _get_chroma() -> ChromaManager:
    global _chroma
    if _chroma is None:
        settings = get_settings()
        embedding = EmbeddingClient(settings)
        _chroma = ChromaManager(settings, embedding)
    return _chroma


@router.post("/upload", response_model=UploadResponse)
async def upload_data(request: UploadRequest) -> UploadResponse:
    """Upload text content, split by delimiter, dedup, and store."""
    chunks = request.content.split(request.delimiter)
    chunks = [c.strip() for c in chunks if c.strip()]
    if not chunks:
        raise HTTPException(status_code=400, detail="No valid chunks after splitting")

    chroma = _get_chroma()
    result = chroma.upload(request.category, chunks)
    return UploadResponse(
        inserted=result["inserted"],
        skipped=result["skipped"],
        total=len(chunks),
    )


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


@router.delete("/data", response_model=ClearResponse)
async def clear_data(
    category: Optional[str] = Query(default=None),
) -> ClearResponse:
    """Clear one or all knowledge base collections."""
    if category and category not in ALL_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    chroma = _get_chroma()
    chroma.clear(category)
    cleared = [category] if category else ALL_COLLECTIONS
    return ClearResponse(cleared=cleared)


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
