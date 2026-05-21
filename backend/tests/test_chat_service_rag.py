"""Tests for the RAG-enabled ChatService (multi-stage SSE output via custom stream)."""

import json

import pytest
from langchain_core.messages import AIMessageChunk

from app.schemas.chat import ChatMessage
from app.services.chat_service import ChatService


@pytest.fixture
def service(settings):
    """Create a ChatService for testing."""
    return ChatService(settings)


@pytest.mark.asyncio
async def test_stream_chat_emits_status_and_token(service):
    """stream_chat emits status then token events when no RAG."""
    async def _mock_astream(*args, **kwargs):
        yield {"type": "status", "node": "routing", "label": "Analyzing...", "decision": {"search_manual": False, "search_forum": False}}
        yield {"type": "token", "token": "Hello"}
        yield {"type": "token", "token": " world"}

    service.graph.astream = _mock_astream

    events = []
    async for event_str in service.stream_chat(
        [ChatMessage(role="user", content="Say hi")]
    ):
        events.append(json.loads(event_str))

    types = [e["type"] for e in events]
    assert "status" in types
    token_text = "".join(e["token"] for e in events if e["type"] == "token" and not e.get("done"))
    assert token_text == "Hello world"


@pytest.mark.asyncio
async def test_stream_chat_with_rag_context(service):
    """When RAG context is retrieved, retrieval event is emitted."""
    async def _mock_astream(*args, **kwargs):
        yield {"type": "status", "node": "routing", "label": "Analyzing...", "decision": {"search_manual": True, "search_forum": False}}
        yield {"type": "retrieval", "source": "student_manual", "label": "已检索到相关规定", "chunks": [{"preview": "Dorm rules: quiet hours 10pm", "source": "学生手册"}]}
        yield {"type": "token", "token": "test"}

    service.graph.astream = _mock_astream

    events = []
    async for event_str in service.stream_chat(
        [ChatMessage(role="user", content="Dorm rules?")]
    ):
        events.append(json.loads(event_str))

    types = [e["type"] for e in events]
    assert "retrieval" in types, f"Expected retrieval event, got types={types}"
    retrieval_events = [e for e in events if e["type"] == "retrieval"]
    assert any("Dorm rules" in c["preview"] for r in retrieval_events for c in r.get("chunks", []))


@pytest.mark.asyncio
async def test_stream_chat_graph_fallback(service):
    """When the graph fails, an error event is emitted."""
    async def _mock_astream(*args, **kwargs):
        raise RuntimeError("Graph error")
        yield  # pragma: no cover

    service.graph.astream = _mock_astream

    events = []
    async for event_str in service.stream_chat(
        [ChatMessage(role="user", content="hi")]
    ):
        events.append(json.loads(event_str))

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert events[0]["done"] is True
