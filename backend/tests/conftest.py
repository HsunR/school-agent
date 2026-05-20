"""Shared pytest fixtures for backend tests.

Fixtures provided:
    - ``settings``: Settings instance with mock env vars (no real .env dependency).
    - ``mock_chat_service``: Mock ChatService with an AsyncMock ``stream_chat``.
    - ``client``: Async HTTP client backed by FastAPI's ASGITransport.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Return a ``Settings`` instance isolated from .env / real env vars.

    Uses explicit keyword arguments so tests never accidentally read from the
    environment or a ``.env`` file.
    """
    return Settings(
        deepseek_api_key="test-key-placeholder",
        llm_model="test-model",
        llm_base_url="https://test.api.example.com/v1",
        llm_chat_model="test-chat-model",
        llm_chat_base_url="https://test.api.example.com/v1",
        llm_chat_api_key="test-chat-key",
        llm_routing_model="test-routing-model",
        llm_routing_base_url="https://test.api.example.com/v1",
        llm_routing_api_key="test-routing-key",
        llm_embedding_model="test-embedding-model",
        llm_embedding_base_url="https://test.api.example.com/v1",
        llm_embedding_api_key="test-embedding-key",
        chroma_persist_dir="./test_chroma_db",
        rag_top_k_manual=3,
        rag_top_k_forum=3,
        max_input_length=1000,
        llm_timeout=30,
        app_name="Test App",
    )


@pytest.fixture
def mock_chat_service() -> MagicMock:
    """Return a ``MagicMock`` ChatService with an ``AsyncMock`` stream_chat.

    Usage::

        def test_foo(mock_chat_service):
            mock_chat_service.stream_chat.return_value = async_gen(...)
            mock_chat_service.stream_chat.side_effect = ...

    The ``return_value`` should be an async iterable (e.g. an async generator
    function) that yields strings.
    """
    service = MagicMock()
    service.stream_chat = AsyncMock()
    return service


@pytest.fixture
async def client() -> AsyncClient:
    """Return an ``AsyncClient`` wired to the FastAPI app via ASGITransport.

    All requests are sent directly to the ASGI interface — no server process
    is needed.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
