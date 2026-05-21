"""Chat-related Pydantic schemas for request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    """Request payload for chat completion."""

    messages: list[ChatMessage] = Field(..., min_length=1)
    stream: bool = True

