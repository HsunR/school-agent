"""Chat service using LangChain with RAG support.

Runs the LangGraph pipeline for routing + retrieval, then streams
the final answer directly via ``llm.astream()`` for proper per-token SSE.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
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
        self.graph = compile_graph(self.routing_llm, self.chroma, self.chat_llm)

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
        """Stream a chat response with SSE-typed events via graph.astream."""
        langchain_messages = self._to_langchain(messages)

        initial_state = {
            "messages": langchain_messages,
            "search_manual": False,
            "search_forum": False,
            "search_query_manual": "",
            "search_query_forum": "",
            "manual_chunks": [],
            "forum_chunks": [],
        }

        try:
            async for event_type, event_data in self.graph.astream(
                initial_state,
                stream_mode=["updates", "messages"],
            ):
                if event_type == "updates":
                    for node_name, node_output in event_data.items():
                        sse_event = self._convert_update_to_sse(node_name, node_output)
                        if sse_event:
                            yield sse_event
                elif event_type == "messages":
                    msg_chunk, metadata = event_data
                    if isinstance(msg_chunk, AIMessageChunk) and msg_chunk.content:
                        yield json.dumps({
                            "type": "token",
                            "token": msg_chunk.content,
                        }, ensure_ascii=False)
        except Exception:
            logger.exception("Graph streaming failed")
            yield json.dumps({
                "type": "error", "error": "服务异常，请重试", "done": True,
            }, ensure_ascii=False)
            return

        yield json.dumps({"type": "token", "token": "", "done": True})

    def _convert_update_to_sse(self, node_name: str, node_output: dict) -> str | None:
        if node_name == "routing_node":
            decision = {
                "search_manual": node_output.get("search_manual", False),
                "search_forum": node_output.get("search_forum", False),
            }
            return json.dumps({
                "type": "status", "node": "routing",
                "label": "正在分析你的问题...",
                "decision": decision,
            }, ensure_ascii=False)

        elif node_name == "manual_retrieval_node":
            chunks = node_output.get("manual_chunks", [])
            previews = [{"preview": c[:200], "source": "学生手册"} for c in chunks]
            label = "已检索到【学生手册】相关规定" if chunks else "【学生手册】未检索到相关内容"
            return json.dumps({
                "type": "retrieval", "source": "student_manual",
                "label": label, "chunks": previews,
            }, ensure_ascii=False)

        elif node_name == "forum_retrieval_node":
            chunks = node_output.get("forum_chunks", [])
            previews = [{"preview": c[:200], "source": "学校贴吧"} for c in chunks]
            label = "已检索到【学校贴吧】相关讨论" if chunks else "【学校贴吧】未检索到相关内容"
            return json.dumps({
                "type": "retrieval", "source": "school_forum",
                "label": label, "chunks": previews,
            }, ensure_ascii=False)

        return None
