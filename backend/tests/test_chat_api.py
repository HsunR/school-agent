"""Chat API test suite for SSE streaming endpoint."""

import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _async_gen(tokens: list[str]) -> AsyncGenerator[str, None]:
    """Helper: create an async generator yielding the given tokens."""
    for token in tokens:
        yield token


async def _error_gen(_messages: list) -> AsyncGenerator[str, None]:
    """Helper: async generator that raises on first iteration."""
    raise RuntimeError("Something went wrong")
    # fmt: off
    yield  # unreachable — makes this a generator function
    # fmt: on


def _mock_service(
    stream_func,  # noqa: ANN401
) -> MagicMock:
    """Create a mock ChatService whose ``stream_chat`` returns *stream_func*."""
    svc = MagicMock(spec=["stream_chat"])
    svc.stream_chat = stream_func
    return svc


# ---------------------------------------------------------------------------
# Basic SSE format tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_content_type(client: AsyncClient) -> None:
    """Test SSE endpoint returns text/event-stream content type."""
    mock = _mock_service(lambda _messages: _async_gen(["Hello", " world"]))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


@pytest.mark.asyncio
async def test_sse_stream_format(client: AsyncClient) -> None:
    """Test every SSE chunk is a valid ``data: <json>`` line pair."""
    mock = _mock_service(lambda _messages: _async_gen(["Hello", " world"]))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    for i, chunk in enumerate(chunks):
        assert chunk.startswith("data: "), f"Chunk {i} missing 'data: ' prefix"
        payload = json.loads(chunk.removeprefix("data: "))
        assert "token" in payload
        assert "done" in payload


@pytest.mark.asyncio
async def test_sse_ends_with_done_true(client: AsyncClient) -> None:
    """Test the final SSE chunk is ``{"token":"","done":true}``."""
    mock = _mock_service(lambda _messages: _async_gen(["Hello"]))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    last_payload = json.loads(chunks[-1].removeprefix("data: "))
    assert last_payload == {"token": "", "done": True}


# ---------------------------------------------------------------------------
# Token content tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_tokens_in_order(client: AsyncClient) -> None:
    """Test emitted tokens match the expected order from the service."""
    tokens = ["Token1", "Token2", "Token3"]
    mock = _mock_service(lambda _messages: _async_gen(tokens))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    # All chunks except the final "done" line carry a token
    token_chunks = chunks[:-1]
    assert len(token_chunks) == len(tokens)

    for i, chunk in enumerate(token_chunks):
        payload = json.loads(chunk.removeprefix("data: "))
        assert payload["token"] == tokens[i]
        assert payload["done"] is False


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_messages_returns_422(client: AsyncClient) -> None:
    """Test that an empty messages list returns 422."""
    response = await client.post(
        "/api/chat",
        json={"messages": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_oversize_message_returns_422(client: AsyncClient) -> None:
    """Test that a message with content over 1000 characters returns 422."""
    response = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "x" * 1001}]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_messages_field_returns_422(client: AsyncClient) -> None:
    """Test that omitting the messages field returns 422."""
    response = await client.post(
        "/api/chat",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_role_returns_422(client: AsyncClient) -> None:
    """Test that an invalid role returns 422."""
    response = await client.post(
        "/api/chat",
        json={"messages": [{"role": "admin", "content": "Hi"}]},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_handling_returns_sse_error_chunk(client: AsyncClient) -> None:
    """Test that a service exception is reported as an SSE error chunk."""
    mock = _mock_service(_error_gen)
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert response.status_code == 200
    chunks = [c for c in response.text.strip().split("\n\n") if c]
    assert len(chunks) >= 1
    payload = json.loads(chunks[-1].removeprefix("data: "))
    assert "error" in payload
    assert payload["done"] is True


# ---------------------------------------------------------------------------
# GET /api/chat — existing root stub (still present)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_root(client: AsyncClient) -> None:
    """Test the chat root GET endpoint still works."""
    response = await client.get("/api/chat")
    assert response.status_code == 200
    assert response.json() == {"message": "Chat API placeholder"}
