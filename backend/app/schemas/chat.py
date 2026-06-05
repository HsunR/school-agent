"""Chat-related Pydantic schemas for request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Request payload for chat completion."""

    messages: list[ChatMessage] = Field(..., min_length=1)
    retrieval_mode: Literal["auto", "manual", "forum", "both", "none"] = "auto"
    settings: Optional[dict[str, int]] = None  # keys: top_k_manual, top_k_forum, top_k_scored
    skip_intent: bool = False

