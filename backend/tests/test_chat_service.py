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
    """Token streaming via the chat_llm.astream()."""

    @pytest.mark.asyncio
    async def test_stream_chat_yields_tokens(self):
        """stream_chat should yield tokens from chat_llm.astream()."""
        settings = Settings()

        async def _mock_astream(*args, **kwargs):
            for token in ["Hello", " ", "World", "!"]:
                yield AIMessageChunk(content=token)

        with patch("app.services.chat_service.ChatOpenAI") as mock:
            mock_instance = mock.return_value
            mock_instance.invoke.return_value = AIMessage(
                content='{"search_manual": false, "search_forum": false}'
            )
            mock_instance.astream.return_value = _mock_astream()
            service = ChatService(settings)

        collected = []
        async for token in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            collected.append(token)

        assert "".join(collected) == "Hello World!", (
            f"Expected 'Hello World!', got {''.join(collected)!r}"
        )

    @pytest.mark.asyncio
    async def test_stream_chat_skips_empty_tokens(self):
        """Empty tokens from chat_llm.astream() should be skipped."""
        settings = Settings()

        async def _mock_astream(*args, **kwargs):
            for token in ["Hello", "", "World", ""]:
                yield AIMessageChunk(content=token)

        with patch("app.services.chat_service.ChatOpenAI") as mock:
            mock_instance = mock.return_value
            mock_instance.invoke.return_value = AIMessage(
                content='{"search_manual": false, "search_forum": false}'
            )
            mock_instance.astream.return_value = _mock_astream()
            service = ChatService(settings)

        collected = []
        async for token in service.stream_chat(
            [ChatMessage(role="user", content="test")]
        ):
            collected.append(token)

        assert "".join(collected) == "HelloWorld", (
            f"Expected 'HelloWorld', got {''.join(collected)!r}"
        )


class TestErrorHandling:
    """Error handling in stream_chat."""

    @pytest.mark.asyncio
    async def test_stream_chat_re_raises_error(self):
        """Errors from chat_llm.astream() should be re-raised."""
        settings = Settings()

        async def _mock_astream(*args, **kwargs):
            raise RuntimeError("LLM API error")
            yield  # pragma: no cover

        with patch("app.services.chat_service.ChatOpenAI") as mock:
            mock_instance = mock.return_value
            mock_instance.invoke.return_value = AIMessage(
                content='{"search_manual": false, "search_forum": false}'
            )
            mock_instance.astream.return_value = _mock_astream()
            service = ChatService(settings)

        with pytest.raises(RuntimeError, match="LLM API error"):
            async for _ in service.stream_chat(
                [ChatMessage(role="user", content="test")]
            ):
                pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_stream_chat_with_stream_error_mid_stream(self):
        """Error mid-stream should be re-raised."""
        settings = Settings()

        class MidStreamError(RuntimeError):
            pass

        async def _mock_astream(*args, **kwargs):
            yield AIMessageChunk(content="partial")
            raise MidStreamError("Connection lost")

        with patch("app.services.chat_service.ChatOpenAI") as mock:
            mock_instance = mock.return_value
            mock_instance.invoke.return_value = AIMessage(
                content='{"search_manual": false, "search_forum": false}'
            )
            mock_instance.astream.return_value = _mock_astream()
            service = ChatService(settings)

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
            # ChatOpenAI is called twice: streaming=True + streaming=False
            assert mock_llm_cls.call_count == 2
            for call_args in mock_llm_cls.call_args_list:
                assert call_args.kwargs.get("timeout") == 15

    @pytest.mark.asyncio
    async def test_default_timeout_is_30(self):
        """Default llm_timeout should be 30."""
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(Settings())
            assert mock_llm_cls.call_count == 2
            for call_args in mock_llm_cls.call_args_list:
                assert call_args.kwargs.get("timeout") == 30

    @pytest.mark.asyncio
    async def test_custom_timeout_value(self):
        """Custom timeout value should propagate correctly."""
        settings = Settings(llm_timeout=60)
        with patch("app.services.chat_service.ChatOpenAI") as mock_llm_cls:
            ChatService(settings)
            assert mock_llm_cls.call_count == 2
            for call_args in mock_llm_cls.call_args_list:
                assert call_args.kwargs.get("timeout") == 60

    @pytest.mark.asyncio
    async def test_stream_chat_with_simulated_timeout(self):
        """Simulate a timeout by having chat_llm.astream() raise.

        The service should re-raise the timeout exception so the caller
        can handle it appropriately.
        """
        settings = Settings(llm_timeout=1)

        async def _mock_astream(*args, **kwargs):
            import asyncio

            await asyncio.sleep(0.01)  # simulate brief work
            raise TimeoutError("LLM timed out")
            yield  # pragma: no cover

        with patch("app.services.chat_service.ChatOpenAI") as mock:
            mock_instance = mock.return_value
            mock_instance.invoke.return_value = AIMessage(
                content='{"search_manual": false, "search_forum": false}'
            )
            mock_instance.astream.return_value = _mock_astream()
            service = ChatService(settings)

        with pytest.raises(TimeoutError, match="LLM timed out"):
            async for _ in service.stream_chat(
                [ChatMessage(role="user", content="test")]
            ):
                pass  # pragma: no cover
