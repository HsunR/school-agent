"""Integration tests for the admin API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    """Test that the stats endpoint returns a list of category counts."""
    with patch("app.api.admin._get_chroma") as mock_get:
        mock_chroma = MagicMock()
        mock_chroma.stats.return_value = {"category": "student_manual", "total_count": 42}
        mock_get.return_value = mock_chroma
        resp = await client.get("/api/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_clear_category_returns_cleared(client: AsyncClient) -> None:
    """Test that clearing a specific category returns that category."""
    with patch("app.api.admin._get_chroma") as mock_get:
        mock_chroma = MagicMock()
        mock_get.return_value = mock_chroma
        resp = await client.delete("/api/admin/data?category=student_manual")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cleared"] == ["student_manual"]


@pytest.mark.asyncio
async def test_clear_missing_category_returns_422(client: AsyncClient) -> None:
    """Test that omitting category on DELETE returns 422."""
    resp = await client.delete("/api/admin/data")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_clear_invalid_category_returns_400(client: AsyncClient) -> None:
    """Test that clearing an invalid category returns 400."""
    resp = await client.delete("/api/admin/data?category=invalid")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_single_record_missing_category_returns_422(client: AsyncClient) -> None:
    """Test that deleting a record without category returns 422."""
    resp = await client.delete("/api/admin/data?id=somehash")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_single_record_invalid_category_returns_400(client: AsyncClient) -> None:
    """Test that deleting with invalid category returns 400."""
    resp = await client.delete("/api/admin/data?category=invalid&id=somehash")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_nonexistent_record_returns_zero(client: AsyncClient) -> None:
    """Test that deleting a non-existent ID returns deleted=0 (not an error)."""
    with patch("app.api.admin._get_chroma") as mock_get:
        mock_chroma = MagicMock()
        mock_chroma.delete_by_id.return_value = 0
        mock_get.return_value = mock_chroma
        resp = await client.delete(
            "/api/admin/data?category=student_manual&id=nonexistent_hash"
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 0


# ---------------------------------------------------------------------------
# Queue endpoint tests (mock QueueService)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_202_when_queue_accepts(client: AsyncClient) -> None:
    """Test that upload returns 202 Accepted when queue is free."""
    with patch("app.api.admin._get_queue_service") as mock_get:
        mock_svc = MagicMock()
        mock_svc.enqueue = AsyncMock()
        mock_get.return_value = mock_svc
        resp = await client.post(
            "/api/admin/upload",
            json={"content": "chunk1\nchunk2", "category": "student_manual", "delimiter": "\n"},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["queued"] is True
    assert data["queue_size"] == 1


@pytest.mark.asyncio
async def test_upload_returns_409_when_queue_busy(client: AsyncClient) -> None:
    """Test that upload returns 409 Conflict when queue is busy."""
    with patch("app.api.admin._get_queue_service") as mock_get:
        mock_svc = MagicMock()
        mock_svc.enqueue = AsyncMock(side_effect=RuntimeError("Queue is busy"))
        mock_get.return_value = mock_svc
        resp = await client.post(
            "/api/admin/upload",
            json={"content": "some content", "category": "student_manual"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_queue_status_endpoint(client: AsyncClient) -> None:
    """Test GET /api/admin/queue returns queue status."""
    with patch("app.api.admin._get_queue_service") as mock_get:
        mock_svc = MagicMock()
        mock_svc.get_status.return_value = {
            "busy": True,
            "pending": 1,
            "current_task": "doc.txt",
            "progress": 10,
            "total": 50,
        }
        mock_get.return_value = mock_svc
        resp = await client.get("/api/admin/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["busy"] is True
    assert data["pending"] == 1
    assert data["current_task"] == "doc.txt"


@pytest.mark.asyncio
async def test_queue_clear_endpoint(client: AsyncClient) -> None:
    """Test POST /api/admin/queue/clear calls clear and returns message."""
    with patch("app.api.admin._get_queue_service") as mock_get:
        mock_svc = MagicMock()
        mock_svc.clear = MagicMock()
        mock_get.return_value = mock_svc
        resp = await client.post("/api/admin/queue/clear")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    mock_svc.clear.assert_called_once()
