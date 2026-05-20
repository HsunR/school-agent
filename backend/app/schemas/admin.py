"""Admin-related Pydantic schemas for knowledge base management."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Category = Literal["student_manual", "school_forum"]


class UploadRequest(BaseModel):
    """Request payload for uploading knowledge base content."""

    content: str = Field(..., min_length=1)
    category: Category
    delimiter: str = Field(default="*****SPILIT_BY_HUSNR*****", min_length=1)


class UploadResponse(BaseModel):
    """Response after an upload operation."""

    inserted: int
    skipped: int
    total: int


class DataPreviewResponse(BaseModel):
    """Paginated chunk data from a collection."""

    ids: list[str]
    documents: list[str]
    metadatas: list[dict[str, Any]]
    total: int
    page: int
    size: int


class StatsResponse(BaseModel):
    """Statistics for a single collection."""

    category: str
    total_count: int


class DeleteResponse(BaseModel):
    """Response after deleting specific documents."""

    deleted: int

class ClearResponse(BaseModel):
    """Response after clearing a collection."""

    cleared: list[str]
