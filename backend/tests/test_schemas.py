"""Tests for Pydantic schemas (ChatMessage, ChatRequest)."""

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatMessage, ChatRequest


class TestChatMessage:
    """ChatMessage schema validation."""

    def test_valid_user_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_valid_assistant_message(self):
        msg = ChatMessage(role="assistant", content="Hi there")
        assert msg.role == "assistant"

    def test_valid_system_message(self):
        msg = ChatMessage(role="system", content="Be helpful")
        assert msg.role == "system"

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="admin", content="test")

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="")

    def test_content_exceeds_max_length(self):
        long_content = "a" * 1001
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content=long_content)

    def test_content_at_max_length(self):
        content = "a" * 1000
        msg = ChatMessage(role="user", content=content)
        assert len(msg.content) == 1000


class TestChatRequest:
    """ChatRequest schema validation."""

    def test_valid_request(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")]
        )
        assert len(req.messages) == 1
        assert req.stream is True

    def test_empty_messages_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_multiple_messages(self):
        req = ChatRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="Hello"),
            ]
        )
        assert len(req.messages) == 2

    def test_stream_defaults_to_true(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")]
        )
        assert req.stream is True

    def test_stream_can_be_false(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            stream=False,
        )
        assert req.stream is False


