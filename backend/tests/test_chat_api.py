"""Chat API test suite for SSE streaming endpoint."""

import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


async def _event_gen(events: list[dict]) -> AsyncGenerator[str, None]:
    """Helper: async generator yielding pre-serialized JSON event strings."""
    for event in events:
        yield json.dumps(event, ensure_ascii=False)


async def _error_gen(*_) -> AsyncGenerator[str, None]:
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
    events = [
        {"type": "token", "token": "Hello"},
        {"type": "token", "token": "", "done": True},
    ]
    mock = _mock_service(lambda *_: _event_gen(events))
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
    events = [
        {"type": "token", "token": "Hello"},
        {"type": "token", "token": "", "done": True},
    ]
    mock = _mock_service(lambda *_: _event_gen(events))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    for i, chunk in enumerate(chunks):
        assert chunk.startswith("data: "), f"Chunk {i} missing 'data: ' prefix"
        payload = json.loads(chunk.removeprefix("data: "))
        assert "type" in payload


@pytest.mark.asyncio
async def test_sse_ends_with_done_true(client: AsyncClient) -> None:
    """Test the final SSE chunk has ``"done":true``."""
    events = [
        {"type": "token", "token": "Hello"},
        {"type": "token", "token": "", "done": True},
    ]
    mock = _mock_service(lambda *_: _event_gen(events))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    last_payload = json.loads(chunks[-1].removeprefix("data: "))
    assert last_payload.get("done") is True


# ---------------------------------------------------------------------------
# Token content tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_tokens_in_order(client: AsyncClient) -> None:
    """Test emitted tokens match the expected order from the service."""
    events = [
        {"type": "token", "token": "Token1"},
        {"type": "token", "token": "Token2"},
        {"type": "token", "token": "Token3"},
        {"type": "token", "token": "", "done": True},
    ]
    mock = _mock_service(lambda *_: _event_gen(events))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    token_chunks = [c for c in chunks if json.loads(c.removeprefix("data: ")).get("type") == "token" and not json.loads(c.removeprefix("data: ")).get("done")]
    assert len(token_chunks) == 3

    for i, chunk in enumerate(token_chunks):
        payload = json.loads(chunk.removeprefix("data: "))
        assert payload["token"] == f"Token{i + 1}"


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
async def test_oversize_message_accepted(client: AsyncClient) -> None:
    """Test that a message with content over 1000 characters is accepted."""
    events = [
        {"type": "token", "token": "Hello"},
        {"type": "token", "token": "", "done": True},
    ]
    mock = _mock_service(lambda *_: _event_gen(events))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "x" * 1001}]},
        )
    assert response.status_code == 200


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
    """Integration test: mock ChatService, verify SSE flow end-to-end."""
    events = [
        {"type": "status", "node": "routing", "label": "Analyzing..."},
        {"type": "token", "token": "Hello"},
        {"type": "token", "token": " "},
        {"type": "token", "token": "World"},
        {"type": "token", "token": "", "done": True},
    ]
    mock_chat_service.stream_chat = lambda *_: _event_gen(events)  # noqa: E731

    with patch("app.api.chat.chat_service", mock_chat_service):
        response = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    chunks = [c for c in response.text.strip().split("\n\n") if c]
    assert len(chunks) == len(events)

    payloads = [json.loads(c.removeprefix("data: ")) for c in chunks]
    assert payloads[0]["type"] == "status"
    assert payloads[-1]["done"] is True
    token_text = "".join(p["token"] for p in payloads if p.get("type") == "token" and not p.get("done"))
    assert token_text == "Hello World"


@pytest.mark.asyncio
async def test_integration_mocked_service_error(
    client: AsyncClient,
    mock_chat_service: MagicMock,
) -> None:
    """Integration test: service exception yields SSE error chunk."""
    async def _error_stream(*_):  # noqa: ANN202
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
