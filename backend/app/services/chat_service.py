"""Chat service using LangChain.

Provides ChatService that wraps an LLM and exposes a streaming
interface for chat interactions via Server-Sent Events.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI

from app.core.settings import Settings
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

# Mapping from ChatMessage role strings to LangChain message classes
_ROLE_MAP: dict[str, type[BaseMessage]] = {
    "user": HumanMessage,
    "assistant": AIMessage,
    "system": SystemMessage,
}


class ChatService:
    """Service for handling chat interactions via LLM streaming.

    Encapsulates LLM configuration and streaming response generation.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the service with the given application settings.

        Args:
            settings: Application settings containing LLM configuration.
        """
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.deepseek_api_key,
            streaming=True,
            timeout=settings.llm_timeout,
        )

    def _to_langchain(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convert a list of ChatMessage schemas to LangChain message objects.

        Args:
            messages: List of ChatMessage Pydantic models.

        Returns:
            A list of LangChain BaseMessage instances.

        Raises:
            ValueError: If an unknown role is encountered.
        """
        result: list[BaseMessage] = []
        for msg in messages:
            msg_class = _ROLE_MAP.get(msg.role)
            if msg_class is None:
                msg = f"Unknown role: {msg.role}"
                raise ValueError(msg)
            result.append(msg_class(content=msg.content))
        return result

    async def stream_chat(
        self,
        messages: list[ChatMessage],
    ) -> AsyncGenerator[str, Any]:
        """Stream a chat response token by token from the LLM.

        Converts ChatMessage schemas to LangChain format, invokes
        ``llm.astream``, and yields individual content chunks.

        Args:
            messages: List of chat messages forming the conversation history.

        Yields:
            Content tokens from the LLM response, one by one.

        Raises:
            RuntimeError: If the underlying LLM call fails.
        """
        langchain_messages = self._to_langchain(messages)
        try:
            async for chunk in self.llm.astream(langchain_messages):
                content: str = chunk.content
                if content:
                    yield content
        except Exception:
            logger.exception("Stream chat error")
            raise
