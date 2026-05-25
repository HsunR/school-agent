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
        msg = ChatMessage(role="user", content=long_content)
        assert len(msg.content) == 1001

    def test_content_long_accepted(self):
        content = "a" * 2000
        msg = ChatMessage(role="user", content=content)
        assert len(msg.content) == 2000


class TestChatRequest:
    """ChatRequest schema validation."""

    def test_valid_request(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")]
        )
        assert len(req.messages) == 1

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

    def test_request_with_retrieval_mode(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            retrieval_mode="manual",
            settings={"top_k_manual": 6, "top_k_forum": 6, "top_k_scored": 3},
        )
        assert req.retrieval_mode == "manual"
        assert req.settings["top_k_manual"] == 6

    def test_request_default_retrieval_mode(self):
        req = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])
        assert req.retrieval_mode == "auto"
        assert req.settings is None

    def test_request_invalid_retrieval_mode_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                retrieval_mode="invalid",
            )


