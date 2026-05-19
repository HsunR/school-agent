"""Chat service using LangChain with RAG support.

Runs the LangGraph pipeline for routing + retrieval, then streams
the final answer directly via ``llm.astream()`` for proper per-token SSE.
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
from app.graph.graph import RETRIEVAL_CONTEXT_TEMPLATE, compile_graph
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

    Uses a LangGraph pipeline for routing + retrieval decisions, then
    streams the LLM answer token-by-token via ``astream()``.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Chat LLM (for the final answer)
        self.chat_llm = ChatOpenAI(
            model=settings.llm_chat_model,
            base_url=settings.llm_chat_base_url,
            api_key=settings.llm_chat_api_key,
            streaming=True,
            timeout=settings.llm_timeout,
        )

        # Routing LLM (for classification)
        self.routing_llm = ChatOpenAI(
            model=settings.llm_routing_model,
            base_url=settings.llm_routing_base_url,
            api_key=settings.llm_routing_api_key,
            streaming=False,
            timeout=settings.llm_timeout,
        )

        # RAG components
        self.embedding_client = EmbeddingClient(settings)
        self.chroma = ChromaManager(settings, self.embedding_client)

        # Compiled graph
        self.graph = compile_graph(self.routing_llm, self.chroma)

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
        """Stream a chat response with optional RAG context.

        1. Run the LangGraph pipeline (routing + retrieval, sync).
        2. If context was retrieved, prepend it as a system message.
        3. Stream the answer via ``llm.astream()``.
        """
        langchain_messages = self._to_langchain(messages)

        # ── Step 1: Run graph for routing + retrieval ──
        try:
            initial_state = {
                "messages": langchain_messages,
                "search_manual": False,
                "search_forum": False,
                "manual_chunks": [],
                "forum_chunks": [],
            }
            final_state = self.graph.invoke(initial_state)
        except Exception:
            logger.exception("Graph pipeline failed, falling back to direct chat")
            final_state = {"manual_chunks": [], "forum_chunks": []}

        # ── Step 2: Build context-augmented messages ──
        manual_ctx = "\n\n".join(final_state.get("manual_chunks", []))
        forum_ctx = "\n\n".join(final_state.get("forum_chunks", []))
        has_context = bool(manual_ctx.strip() or forum_ctx.strip())

        if has_context:
            context_prompt = RETRIEVAL_CONTEXT_TEMPLATE.format(
                manual_context=manual_ctx or "（未检索到相关内容）",
                forum_context=forum_ctx or "（未检索到相关内容）",
            )
            augmented_messages = [
                SystemMessage(content=context_prompt),
                *langchain_messages,
            ]
        else:
            augmented_messages = langchain_messages

        # ── Step 3: Stream answer ──
        try:
            async for chunk in self.chat_llm.astream(augmented_messages):
                content: str = chunk.content
                if content:
                    yield content
        except Exception:
            logger.exception("Stream chat error")
            raise
