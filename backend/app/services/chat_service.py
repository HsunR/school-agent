"""Chat service using LangChain with RAG support.

Runs the LangGraph pipeline via ``graph.astream(stream_mode="custom")``,
passing through typed events emitted by each graph node via ``get_stream_writer()``.
"""

import json
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
from app.rag.chroma_manager import ChromaManager
from app.rag.embeddings import EmbeddingClient
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

_ROLE_MAP: dict[str, type[BaseMessage]] = {
    "user": HumanMessage,
    "assistant": AIMessage,
    "system": SystemMessage,
}


class ChatService:
    """Service for handling chat interactions with optional RAG.

    Uses ``graph.astream(stream_mode="custom")`` where graph nodes
    emit typed events directly via ``get_stream_writer()``.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        self.chat_llm = ChatOpenAI(
            model=settings.llm_chat_model,
            base_url=settings.llm_chat_base_url,
            api_key=settings.llm_chat_api_key,
            streaming=True,
            timeout=settings.llm_timeout,
        )

        self.routing_llm = ChatOpenAI(
            model=settings.llm_routing_model,
            base_url=settings.llm_routing_base_url,
            api_key=settings.llm_routing_api_key,
            streaming=False,
            timeout=settings.llm_timeout,
        )

        self.embedding_client = EmbeddingClient(settings)
        self.chroma = ChromaManager(settings, self.embedding_client)

        self.scoring_llm = ChatOpenAI(
            model=settings.llm_scoring_model,
            base_url=settings.llm_scoring_base_url,
            api_key=settings.llm_scoring_api_key,
            streaming=False,
            timeout=15,
        )

        self.graph = compile_graph(
            self.routing_llm, self.chroma, self.chat_llm, self.scoring_llm,
        )

    def _to_langchain(self, messages: list[ChatMessage]) -> list[BaseMessage]:
        result: list[BaseMessage] = []
        for msg in messages:
            msg_class = _ROLE_MAP.get(msg.role)
            if msg_class is None:
                raise ValueError(f"Unknown role: {msg.role}")
            result.append(msg_class(content=msg.content))
        return result

    async def stream_chat(
        self,
        messages: list[ChatMessage],
    ) -> AsyncGenerator[str, Any]:
        """Stream a chat response with SSE-typed events via graph.astream(custom)."""
        langchain_messages = self._to_langchain(messages)

        initial_state = {
            "messages": langchain_messages,
            "search_manual": False,
            "search_forum": False,
            "search_query_manual": "",
            "search_query_forum": "",
        }

        try:
            async for custom_event in self.graph.astream(
                initial_state,
                stream_mode="custom",
            ):
                yield json.dumps(custom_event, ensure_ascii=False)
        except Exception:
            logger.exception("Graph streaming failed")
            yield json.dumps({
                "type": "error", "error": "服务异常，请重试", "done": True,
            }, ensure_ascii=False)
            return

        yield json.dumps({"type": "token", "token": "", "done": True})
