"""Chat service using LangChain and LangGraph.

Provides ChatService that wraps an LLM in a LangGraph state graph
and exposes a streaming interface for chat interactions.
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
from app.graph.graph import compile_graph
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

# Mapping from ChatMessage role strings to LangChain message classes
_ROLE_MAP: dict[str, type[BaseMessage]] = {
    "user": HumanMessage,
    "assistant": AIMessage,
    "system": SystemMessage,
}


class ChatService:
    """Service for handling chat interactions via a LangGraph state graph.

    Encapsulates LLM configuration, graph compilation, and streaming
    response generation.
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
        self.graph = compile_graph(self.llm)

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
        """Stream a chat response token by token from the compiled graph.

        Converts ChatMessage schemas to LangChain format, invokes the
        LangGraph state graph with ``astream_events``, and yields individual
        content tokens from ``on_chat_model_stream`` events.

        Args:
            messages: List of chat messages forming the conversation history.

        Yields:
            Content tokens from the LLM response, one by one.

        Raises:
            RuntimeError: If the underlying LLM or graph call fails.
        """
        langchain_messages = self._to_langchain(messages)
        try:
            async for event in self.graph.astream_events(
                {"messages": langchain_messages},
                version="v2",
                include_types=["chat_model"],
            ):
                if event.get("event") == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is not None and hasattr(chunk, "content"):
                        content: str = chunk.content
                        if content:
                            yield content
        except Exception:
            logger.exception("Stream chat error")
            raise
