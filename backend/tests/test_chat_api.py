"""Chat API test stubs."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_chat_root(client: AsyncClient) -> None:
    """Test the chat root endpoint returns expected placeholder."""
    response = await client.get("/api/chat")
    assert response.status_code == 200
    assert response.json() == {"message": "Chat API placeholder"}
