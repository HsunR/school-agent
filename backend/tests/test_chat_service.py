"""Tests for ChatService.

Tests cover:
- Message format conversion (ChatMessage -> LangChain messages)
- Token streaming via graph.astream_events
- Error handling
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


class MockStreamingChatModel:
    """Mock chat model that streams tokens.

    This is not a BaseChatModel subclass - we use it to replace
    ChatOpenAI at the module level via patch. The graph.astream_events
    approach means we need to mock at a higher level for service tests.
    """

    streaming = True

    def __init__(self, **kwargs):
        self.model = kwargs.get("model", "test")
        self.base_url = kwargs.get("base_url", "")
        self.api_key = kwargs.get("api_key", "")
        self.timeout = kwargs.get("timeout", 30)


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
    """Token streaming via the compiled graph."""

    @pytest.mark.asyncio
    async def test_stream_chat_yields_tokens(self):
        """stream_chat should yield tokens from the graph's astream_events."""
        settings = Settings()
        with patch("app.services.chat_service.ChatOpenAI"):
            service = ChatService(settings)

        # Mock the graph's astream_events to yield sample token events
        async def mock_astream_events(*args, **kwargs):
            tokens = ["Hello", " ", "World", "!"]
            for token in tokens:
                yield {
                    "event": "on_chat_model_stream",
                    "data": {
                        "chunk": AIMessageChunk(content=token),
                    },
                }
            # Also yield a final end event to be safe
            yield {
                "event": "on_chat_model_end",
                "data": {},
            }

        service.graph.astream_events = mock_astream_events

        collected = []
        async for token in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            collected.append(token)

        assert "".join(collected) == "Hello World!", (
            f"Expected 'Hello World!', got {''.join(collected)!r}"
        )

    @pytest.mark.asyncio
    async def test_stream_chat_with_empty_token(self):
        """Empty tokens from the graph should be skipped."""
        settings = Settings()
        with patch("app.services.chat_service.ChatOpenAI"):
            service = ChatService(settings)

        async def mock_astream_events(*args, **kwargs):
            tokens = ["Hello", "", "World", ""]
            for token in tokens:
                yield {
                    "event": "on_chat_model_stream",
                    "data": {
                        "chunk": AIMessageChunk(content=token),
                    },
                }

        service.graph.astream_events = mock_astream_events

        collected = []
        async for token in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            collected.append(token)

        assert "".join(collected) == "HelloWorld", (
            f"Expected 'HelloWorld', got {''.join(collected)!r}"
        )

    @pytest.mark.asyncio
    async def test_stream_chat_ignores_non_stream_events(self):
        """Non-stream events should be ignored."""
        settings = Settings()
        with patch("app.services.chat_service.ChatOpenAI"):
            service = ChatService(settings)

        async def mock_astream_events(*args, **kwargs):
            yield {"event": "on_chain_start", "data": {}}
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": AIMessageChunk(content="token1")},
            }
            yield {"event": "on_chain_end", "data": {}}
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": AIMessageChunk(content="token2")},
            }

        service.graph.astream_events = mock_astream_events

        collected = []
        async for token in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            collected.append(token)

        assert "".join(collected) == "token1token2", (
            f"Expected 'token1token2', got {''.join(collected)!r}"
        )


class TestErrorHandling:
    """Error handling in stream_chat."""

    @pytest.mark.asyncio
    async def test_stream_chat_re_raises_error(self):
        """Errors from the graph should be re-raised."""
        settings = Settings()
        with patch("app.services.chat_service.ChatOpenAI"):
            service = ChatService(settings)

        async def mock_astream_events(*args, **kwargs):
            raise RuntimeError("LLM API error")
            yield  # pragma: no cover

        service.graph.astream_events = mock_astream_events

        with pytest.raises(RuntimeError, match="LLM API error"):
            async for _ in service.stream_chat(
                [ChatMessage(role="user", content="test")]
            ):
                pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_stream_chat_with_graph_error_mid_stream(self):
        """Error mid-stream should be re-raised."""
        settings = Settings()
        with patch("app.services.chat_service.ChatOpenAI"):
            service = ChatService(settings)

        class MidStreamError(RuntimeError):
            pass

        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": AIMessageChunk(content="partial")},
            }
            raise MidStreamError("Connection lost")

        service.graph.astream_events = mock_astream_events

        tokens = []
        with pytest.raises(MidStreamError, match="Connection lost"):
            async for token in service.stream_chat(
                [ChatMessage(role="user", content="test")]
            ):
                tokens.append(token)

        # Should have yielded partial token before error
        assert "".join(tokens) == "partial"


class TestTimeout:
    """Timeout configuration handling in ChatService."""

    @pytest.mark.asyncio
    async def test_timeout_passed_to_chatopenai(self):
        """The llm_timeout setting should be forwarded to ChatOpenAI."""
        settings = Settings(llm_timeout=15)
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(settings)
            mock_llm_cls.assert_called_once()
            _call_kwargs = mock_llm_cls.call_args.kwargs
            assert _call_kwargs.get("timeout") == 15

    @pytest.mark.asyncio
    async def test_default_timeout_is_30(self):
        """Default llm_timeout should be 30."""
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            service = ChatService(Settings())
            mock_llm_cls.assert_called_once()
            _call_kwargs = mock_llm_cls.call_args.kwargs
            assert _call_kwargs.get("timeout") == 30

    @pytest.mark.asyncio
    async def test_custom_timeout_value(self):
        """Custom timeout value should propagate correctly."""
        settings = Settings(llm_timeout=60)
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(settings)
            mock_llm_cls.assert_called_once()
            _call_kwargs = mock_llm_cls.call_args.kwargs
            assert _call_kwargs.get("timeout") == 60

    @pytest.mark.asyncio
    async def test_stream_chat_with_simulated_timeout(self):
        """Simulate a timeout by having the graph sleep then raise.

        The service should re-raise the timeout exception so the caller
        can handle it appropriately.
        """
        settings = Settings(llm_timeout=1)
        with patch("app.services.chat_service.ChatOpenAI"):
            service = ChatService(settings)

        async def mock_astream_events(*args, **kwargs):
            import asyncio

            await asyncio.sleep(0.01)  # simulate brief work
            raise TimeoutError("LLM timed out")
            yield  # pragma: no cover

        service.graph.astream_events = mock_astream_events

        with pytest.raises(TimeoutError, match="LLM timed out"):
            async for _ in service.stream_chat(
                [ChatMessage(role="user", content="test")]
            ):
                pass  # pragma: no cover
