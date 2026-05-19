"""Tests for the RAG-enabled ChatService."""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import ChatMessage
from app.services.chat_service import ChatService


@pytest.fixture
def _mock_deps():
    """Patch ChatOpenAI and EmbeddingClient so ChatService.__init__ works."""
    with (
        patch("app.services.chat_service.ChatOpenAI") as mock_chat,
        patch("app.services.chat_service.EmbeddingClient"),
    ):
        yield mock_chat


@pytest.mark.asyncio
async def test_stream_chat_yields_tokens(settings, _mock_deps):
    """ChatService.stream_chat yields token strings when no RAG context."""
    service = ChatService(settings)

    # Mock the graph to return empty context (no RAG needed)
    service.graph = MagicMock()
    service.graph.invoke.return_value = {
        "manual_chunks": [],
        "forum_chunks": [],
    }

    # Replace chat_llm with a MagicMock to avoid Pydantic __setattr__
    service.chat_llm = MagicMock()

    async def mock_astream(_):
        for token in ["Hello", " ", "world"]:
            chunk = MagicMock()
            chunk.content = token
            yield chunk

    service.chat_llm.astream = mock_astream

    messages = [ChatMessage(role="user", content="Say hi")]
    tokens = [t async for t in service.stream_chat(messages)]
    assert tokens == ["Hello", " ", "world"]


@pytest.mark.asyncio
async def test_stream_chat_with_rag_context(settings, _mock_deps):
    """When RAG context is retrieved, it's included in the LLM call."""
    service = ChatService(settings)

    # Mock graph to return context
    service.graph = MagicMock()
    service.graph.invoke.return_value = {
        "manual_chunks": ["Dorm rules: quiet hours 10pm"],
        "forum_chunks": [],
    }

    # Replace chat_llm with a MagicMock to avoid Pydantic __setattr__
    service.chat_llm = MagicMock()

    captured_messages = []

    async def mock_astream(msgs):
        nonlocal captured_messages
        captured_messages = msgs
        chunk = MagicMock()
        chunk.content = "test"
        yield chunk

    service.chat_llm.astream = mock_astream

    messages = [ChatMessage(role="user", content="Dorm rules?")]
    async for _ in service.stream_chat(messages):
        pass

    # Verify a system message was prepended with context
    system_msgs = [m for m in captured_messages if m.type == "system"]
    assert len(system_msgs) == 1
    assert "Dorm rules" in system_msgs[0].content


@pytest.mark.asyncio
async def test_stream_chat_graph_fallback(settings, _mock_deps):
    """When the graph fails, streaming falls back to direct chat without context."""
    service = ChatService(settings)

    # Mock graph to raise an exception
    service.graph = MagicMock()
    service.graph.invoke.side_effect = Exception("Graph error")

    # Replace chat_llm with a MagicMock to avoid Pydantic __setattr__
    service.chat_llm = MagicMock()

    captured_messages = []

    async def mock_astream(msgs):
        nonlocal captured_messages
        captured_messages = msgs
        chunk = MagicMock()
        chunk.content = "fallback"
        yield chunk

    service.chat_llm.astream = mock_astream

    messages = [ChatMessage(role="user", content="hi")]
    async for _ in service.stream_chat(messages):
        pass

    # No system message was prepended (no context)
    system_msgs = [m for m in captured_messages if m.type == "system"]
    assert len(system_msgs) == 0
