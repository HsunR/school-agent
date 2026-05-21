"""LangGraph state graph definition for the conversational agent.

Extended graph:
    START → routing_node
              │
              ▼ (should_retrieve)
         ┌────┴────┐
    manual_node  forum_node  (or END if neither)
         │           │
         └─────┬─────┘
               ▼ (should_retrieve again if needed)
              END

After the graph completes, the service layer streams the chat answer
directly via ``llm.astream()`` (not through the graph), preserving
per-token SSE delivery.
"""

import json
import logging
from typing import Annotated, Sequence, TypedDict

import operator

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.rag.chroma_manager import ChromaManager, COLLECTION_MANUAL, COLLECTION_FORUM

logger = logging.getLogger(__name__)

# ── Prompt templates (developer config, not exposed to .env) ──

ROUTING_SYSTEM_PROMPT = (
    "You are a routing classifier for a campus assistant. "
    "Given a user's question, determine whether it requires knowledge from:\n"
    "1. student_manual — the school's student handbook (rules, policies, procedures)\n"
    "2. school_forum — the school's forum/bbs (campus life, events, gossip)\n\n"
    "For each knowledge source that is relevant, generate an optimized search query "
    "for vector retrieval. Extract key terms and reformulate specifically for that source.\n\n"
    "Respond with valid JSON only:\n"
    '{"search_manual": true/false, "search_forum": true/false,\n'
    ' "search_query_manual": "...", "search_query_forum": "..."}\n\n'
    "Examples:\n"
    '- "旷课会不会被处分"\n'
    '  → {"search_manual": true, "search_forum": false,\n'
    '     "search_query_manual": "旷课 处分 规定 节数",\n'
    '     "search_query_forum": ""}\n'
    '- "旷课了能去食堂吃饭吗"\n'
    '  → {"search_manual": true, "search_forum": true,\n'
    '     "search_query_manual": "旷课 处分 规定",\n'
    '     "search_query_forum": "食堂 吃饭 推荐"}\n'
    '- "今天天气怎么样"\n'
    '  → {"search_manual": false, "search_forum": false,\n'
    '     "search_query_manual": "", "search_query_forum": ""}'
)

RETRIEVAL_CONTEXT_TEMPLATE = (
    "以下是从校园知识库中检索到的相关信息，请结合这些信息回答用户问题。\n"
    "如果检索到的内容与问题无关，请忽略它们。\n\n"
    "【学生手册】\n{manual_context}\n\n"
    "【学校贴吧】\n{forum_context}\n\n"
    "请用中文回答。"
)


# ── State ──

class ChatState(TypedDict):
    """State of the chat conversation and RAG pipeline."""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    search_manual: bool
    search_forum: bool
    search_query_manual: str
    search_query_forum: str
    manual_chunks: list[str]
    forum_chunks: list[str]


# ── Nodes ──

def routing_node(state: ChatState, llm: BaseChatModel) -> dict:
    """Classify whether the user question needs each knowledge source."""
    last_msg = state["messages"][-1].content if state["messages"] else ""
    response: AIMessage = llm.invoke([
        SystemMessage(content=ROUTING_SYSTEM_PROMPT),
        *state["messages"],
    ])
    try:
        text = response.content.strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(text)
        search_manual = bool(parsed.get("search_manual", False))
        search_forum = bool(parsed.get("search_forum", False))
        search_query_manual = parsed.get("search_query_manual", "")
        search_query_forum = parsed.get("search_query_forum", "")
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Routing parse failed, defaulting to no search")
        search_manual = False
        search_forum = False
        search_query_manual = ""
        search_query_forum = ""
    logger.info(
        "Routing decision for '%s...': manual=%s, forum=%s",
        last_msg[:50], search_manual, search_forum,
    )
    return {
        "search_manual": search_manual,
        "search_forum": search_forum,
        "search_query_manual": search_query_manual,
        "search_query_forum": search_query_forum,
    }


def manual_retrieval_node(state: ChatState, chroma: ChromaManager) -> dict:
    """Retrieve chunks from the student manual collection."""
    if not state.get("search_manual"):
        return {"manual_chunks": []}
    last_msg = state["messages"][-1].content if state["messages"] else ""
    chunks = chroma.retrieve(COLLECTION_MANUAL, last_msg)
    logger.info("Manual retrieval: %d chunks", len(chunks))
    return {"manual_chunks": chunks}


def forum_retrieval_node(state: ChatState, chroma: ChromaManager) -> dict:
    """Retrieve chunks from the school forum collection."""
    if not state.get("search_forum"):
        return {"forum_chunks": []}
    last_msg = state["messages"][-1].content if state["messages"] else ""
    chunks = chroma.retrieve(COLLECTION_FORUM, last_msg)
    logger.info("Forum retrieval: %d chunks", len(chunks))
    return {"forum_chunks": chunks}


# ── Conditional edge ──

def should_retrieve(state: ChatState) -> str:
    """Return the next retrieval node, or END if both are done/skipped."""
    if state.get("search_manual") and not state.get("manual_chunks"):
        return "manual_retrieval_node"
    if state.get("search_forum") and not state.get("forum_chunks"):
        return "forum_retrieval_node"
    return END


# ── Graph builder ──

def compile_graph(llm: BaseChatModel, chroma: ChromaManager) -> StateGraph:
    """Build and compile the LangGraph state graph.

    Args:
        llm: The LLM instance for the routing node.
        chroma: The ChromaDB manager instance.

    Returns:
        A compiled ``StateGraph``.
    """
    builder = StateGraph(ChatState)

    builder.add_node("routing_node", lambda state: routing_node(state, llm))
    builder.add_node("manual_retrieval_node", lambda state: manual_retrieval_node(state, chroma))
    builder.add_node("forum_retrieval_node", lambda state: forum_retrieval_node(state, chroma))

    builder.add_edge(START, "routing_node")
    builder.add_conditional_edges("routing_node", should_retrieve, {
        "manual_retrieval_node": "manual_retrieval_node",
        "forum_retrieval_node": "forum_retrieval_node",
        END: END,
    })
    builder.add_conditional_edges("manual_retrieval_node", should_retrieve, {
        "forum_retrieval_node": "forum_retrieval_node",
        END: END,
    })
    builder.add_conditional_edges("forum_retrieval_node", should_retrieve, {
        END: END,
    })

    return builder.compile()
