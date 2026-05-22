"""Tests for ChatService.

Tests cover:
- Message format conversion (ChatMessage -> LangChain messages)
- Multi-stage SSE streaming via graph.astream(stream_mode="custom")
- Error handling
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from app.core.settings import Settings
from app.schemas.chat import ChatMessage
from app.services.chat_service import ChatService


class TestToLangChain:
    """Message format conversion."""

    def setup_method(self):
        with patch("app.services.chat_service.ChatOpenAI") as mock:
            self.service = ChatService(Settings())
            self.service.llm = mock.return_value

    def test_user_message(self):
        result = self.service._to_langchain(
            [ChatMessage(role="user", content="Hello")]
        )
        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello"

    def test_assistant_message(self):
        result = self.service._to_langchain(
            [ChatMessage(role="assistant", content="Hi")]
        )
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Hi"

    def test_system_message(self):
        result = self.service._to_langchain(
            [ChatMessage(role="system", content="Be helpful")]
        )
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "Be helpful"

    def test_multiple_messages(self):
        result = self.service._to_langchain(
            [
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi there"),
            ]
        )
        assert len(result) == 3
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage)


class TestStreamChat:
    """Multi-stage SSE streaming via graph.astream(stream_mode='custom')."""

    @pytest.mark.asyncio
    async def test_stream_chat_yields_typed_events(self):
        """stream_chat should yield typed SSE events from custom stream."""
        settings = Settings(llm_scoring_api_key="test-key")
        service = ChatService(settings)

        async def _mock_astream(*args, **kwargs):
            yield {"type": "status", "node": "routing", "label": "Analyzing...", "decision": {"search_manual": False, "search_forum": False}}
            yield {"type": "token", "token": "Hello"}
            yield {"type": "token", "token": " World"}

        service.graph.astream = _mock_astream

        events = []
        async for event_str in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            events.append(json.loads(event_str))

        types = [e["type"] for e in events]
        assert "status" in types
        assert "token" in types
        token_contents = [e["token"] for e in events if e["type"] == "token" and not e.get("done")]
        assert "".join(token_contents) == "Hello World"

    @pytest.mark.asyncio
    async def test_stream_chat_skips_empty_tokens(self):
        """Empty tokens from answer_node should still be yielded (answer_node controls it)."""
        settings = Settings(llm_scoring_api_key="test-key")
        service = ChatService(settings)

        async def _mock_astream(*args, **kwargs):
            yield {"type": "status", "node": "routing", "label": "Analyzing...", "decision": {"search_manual": False, "search_forum": False}}
            yield {"type": "token", "token": "Hello"}
            yield {"type": "token", "token": "World"}

        service.graph.astream = _mock_astream

        events = []
        async for event_str in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            events.append(json.loads(event_str))

        token_contents = [e["token"] for e in events if e["type"] == "token" and not e.get("done")]
        assert "".join(token_contents) == "HelloWorld"


class TestErrorHandling:
    """Error handling in stream_chat via graph.astream."""

    @pytest.mark.asyncio
    async def test_stream_chat_re_raises_error(self):
        """Errors from graph.astream should yield an error event."""
        settings = Settings(llm_scoring_api_key="test-key")
        service = ChatService(settings)

        async def _mock_astream(*args, **kwargs):
            raise RuntimeError("Graph error")
            yield  # pragma: no cover

        service.graph.astream = _mock_astream

        events = []
        async for event_str in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            events.append(json.loads(event_str))

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert events[0]["done"] is True


class TestTimeout:
    """Timeout configuration handling in ChatService."""

    @pytest.mark.asyncio
    async def test_timeout_passed_to_chatopenai(self):
        """The llm_timeout setting should be forwarded to ChatOpenAI."""
        settings = Settings(llm_timeout=15)
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(settings)
            assert mock_llm_cls.call_count == 4
            # chat(0), routing(1) use llm_timeout; scoring(2) hardcoded 15; intent(3) uses llm_timeout
            for idx in [0, 1, 3]:
                assert mock_llm_cls.call_args_list[idx].kwargs.get("timeout") == 15
            assert mock_llm_cls.call_args_list[2].kwargs.get("timeout") == 15

    @pytest.mark.asyncio
    async def test_default_timeout_is_30(self):
        """Default llm_timeout should be 30."""
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(Settings(llm_scoring_api_key="test-key"))
            assert mock_llm_cls.call_count == 4
            for idx in [0, 1, 3]:
                assert mock_llm_cls.call_args_list[idx].kwargs.get("timeout") == 30
            assert mock_llm_cls.call_args_list[2].kwargs.get("timeout") == 15

    @pytest.mark.asyncio
    async def test_custom_timeout_value(self):
        """Custom timeout value should propagate correctly."""
        settings = Settings(llm_timeout=60, llm_scoring_api_key="test-key")
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(settings)
            assert mock_llm_cls.call_count == 4
            for idx in [0, 1, 3]:
                assert mock_llm_cls.call_args_list[idx].kwargs.get("timeout") == 60
            assert mock_llm_cls.call_args_list[2].kwargs.get("timeout") == 15

    @pytest.mark.asyncio
    async def test_stream_chat_with_simulated_timeout(self):
        """A timeout in graph.astream yields an error event instead of crashing."""
        settings = Settings(llm_timeout=1)

        async def _mock_astream(*args, **kwargs):
            raise TimeoutError("LLM timed out")
            yield  # pragma: no cover

        with patch("app.services.chat_service.ChatOpenAI") as mock:
            mock_instance = mock.return_value
            service = ChatService(settings)
            service.graph.astream = _mock_astream

        events = []
        async for event_str in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            events.append(event_str)

        assert len(events) > 0
        import json
        assert json.loads(events[0]).get("type") == "error"
