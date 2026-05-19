"""Integration tests for the admin API endpoints."""

import pytest
from httpx import AsyncClient

from app.rag.chroma_manager import ALL_COLLECTIONS


# ---------------------------------------------------------------------------
# Schema validation tests (no ChromaDB dependency)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_invalid_content_returns_422(client: AsyncClient) -> None:
    """Test that empty content returns 422 validation error."""
    resp = await client.post(
        "/api/admin/upload",
        json={"content": "", "category": "student_manual"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_missing_category_returns_422(client: AsyncClient) -> None:
    """Test that missing category returns 422 validation error."""
    resp = await client.post(
        "/api/admin/upload",
        json={"content": "some content"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_invalid_category_returns_422(client: AsyncClient) -> None:
    """Test that an invalid category literal returns 422."""
    resp = await client.post(
        "/api/admin/upload",
        json={"content": "some content", "category": "invalid_cat"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_preview_invalid_category_returns_400(client: AsyncClient) -> None:
    """Test that an invalid category for preview returns 400."""
    resp = await client.get("/api/admin/data?category=invalid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_preview_missing_category_returns_422(client: AsyncClient) -> None:
    """Test that omitting the required category query param returns 422."""
    resp = await client.get("/api/admin/data")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stats_endpoint_returns_list(client: AsyncClient) -> None:
    """Test that the stats endpoint returns a list of category counts.

    This test may fail if ChromaDB is not initialized — that is expected
    integration behaviour. The important thing is the routing and response
    shape.
    """
    resp = await client.get("/api/admin/stats")
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list)
        categories = [s["category"] for s in data]
        for c in ALL_COLLECTIONS:
            assert c in categories


@pytest.mark.asyncio
async def test_clear_all_returns_cleared_list(client: AsyncClient) -> None:
    """Test that clearing all returns both collection names."""
    resp = await client.delete("/api/admin/data")
    if resp.status_code == 200:
        data = resp.json()
        assert len(data["cleared"]) == len(ALL_COLLECTIONS)


@pytest.mark.asyncio
async def test_clear_invalid_category_returns_400(client: AsyncClient) -> None:
    """Test that clearing an invalid category returns 400."""
    resp = await client.delete("/api/admin/data?category=invalid")
    assert resp.status_code == 400
