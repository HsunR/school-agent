"""Chat API test suite for SSE streaming endpoint."""

import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


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


# ---------------------------------------------------------------------------
# Integration test with mocked ChatService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_mocked_service_sse_flow(
    client: AsyncClient,
    mock_chat_service: MagicMock,
) -> None:
    """Integration test: mock ChatService, verify SSE flow end-to-end.

    Uses the ``mock_chat_service`` fixture to replace the module-level
    ``chat_service`` singleton and checks that every SSE chunk is correctly
    formatted.
    """
    tokens = ["Hello", " ", "World"]  # fmt: skip
    # Replace stream_chat with a plain callable that returns the async
    # generator.  We cannot use AsyncMock for this because AsyncMock wraps
    # return values in a coroutine, which breaks ``async for``.
    mock_chat_service.stream_chat = lambda _msgs: _async_gen(tokens)  # noqa: E731

    with patch("app.api.chat.chat_service", mock_chat_service):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    assert len(chunks) == len(tokens) + 1  # token chunks + final done

    # Verify token chunks
    for i, chunk in enumerate(chunks[:-1]):
        payload = json.loads(chunk.removeprefix("data: "))
        assert payload["token"] == tokens[i]
        assert payload["done"] is False

    # Verify final done chunk
    last_payload = json.loads(chunks[-1].removeprefix("data: "))
    assert last_payload == {"token": "", "done": True}


@pytest.mark.asyncio
async def test_integration_mocked_service_error(
    client: AsyncClient,
    mock_chat_service: MagicMock,
) -> None:
    """Integration test: service exception yields SSE error chunk.

    Verifies that when ``stream_chat`` raises an exception, the endpoint
    returns 200 with an SSE error chunk containing the error message and
    ``done: true``.
    """
    async def _error_stream(_messages):  # noqa: ANN202
        raise RuntimeError("LLM failure")
        yield  # pragma: no cover — makes this an async generator

    mock_chat_service.stream_chat = _error_stream  # noqa: E731

    with patch("app.api.chat.chat_service", mock_chat_service):
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
