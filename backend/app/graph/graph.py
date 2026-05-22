"""LangGraph state graph definition for the conversational agent.

Graph:
    START -> routing_node
               |
               v (should_retrieve)
          +----+----+
    manual_retrieval_node  forum_retrieval_node  (or scoring_node if neither)
          |                    |
          +---------+----------+
                    |
              scoring_node
                    |
               answer_node
                    |
                   v
                  END

Nodes emit typed events via ``get_stream_writer()`` for SSE streaming.
"""

import json
import logging
from typing import Annotated, Sequence, TypedDict

import operator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.config import get_stream_writer
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

SCORING_SYSTEM_PROMPT = (
    "你是一个校园助手的内容过滤器。你的任务：\n"
    "1. 给你一个资料的原文文本和一个用户问题\n"
    "2. 判断资料文本是否与用户问题相关，打分 0-100\n"
    "3. 从资料文本中删除与用户问题完全无关的帖子楼层或者条例，只做这种减法不做任何改动\n"
    "4. 只做删除操作，不得改写、总结、理解或重组原文内容\n"
    "5. 如果整段文本与问题无关，打 0 分，压缩内容留空\n\n"
    "输出必须是以下 JSON 格式，不要添加任何额外内容：\n"
    '{"score": 85, "compressed": "裁剪后保留的原文片段（逐字复制，不做任何改动）"}'
)

INTENT_SYSTEM_PROMPT = (
    "You are an intent analyzer for a campus assistant. "
    "Given the user's question and conversation history, perform two tasks:\n"
    "1. **Optimize the user question** — Fix typos, fill in omitted context, "
    "extract the core query intent. Output a clear, self-contained question.\n"
    "2. **Compress the conversation history** — Summarize recent conversation "
    "into a concise paragraph, preserving key facts, user goals, and any answers already given.\n\n"
    "Output valid JSON only:\n"
    '{{"optimized_query": "...", "compressed_context": "..."}}\n\n'
    "Conversation history:\n{formatted_history}\n\n"
    "User question: {last_message}"
)

# ── Constants ──

SOURCE_MANUAL_LABEL = "学生手册"
SOURCE_FORUM_LABEL = "学校贴吧"
SOURCE_MANUAL_KEY = "student_manual"
SOURCE_FORUM_KEY = "school_forum"

SOURCE_LABEL_TO_KEY = {
    SOURCE_MANUAL_LABEL: SOURCE_MANUAL_KEY,
    SOURCE_FORUM_LABEL: SOURCE_FORUM_KEY,
}

MAX_QUESTION_CHARS = 500
MAX_CHUNK_INPUT_CHARS = 2000
MAX_COMPRESSED_CHARS = 500


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
    scored_chunks: list[dict]
    optimized_query: str
    compressed_context: str


# ── Nodes ──

def _format_history(messages: Sequence[BaseMessage]) -> str:
    parts = []
    for m in messages:
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        content = m.content[:200] if m.content else ""
        parts.append(f"{role}: {content}")
    return "\n".join(parts[-6:])


def intent_node(state: ChatState, intent_llm: BaseChatModel) -> dict:
    writer = get_stream_writer()
    last_msg = state["messages"][-1].content if state["messages"] else ""
    history_msgs = list(state["messages"][:-1])
    formatted_history = _format_history(history_msgs)
    prompt_text = INTENT_SYSTEM_PROMPT.format(
        formatted_history=formatted_history, last_message=last_msg
    )
    optimized_query = last_msg
    compressed_context = ""
    try:
        response: AIMessage = intent_llm.invoke([
            SystemMessage(content=prompt_text),
        ])
        text = response.content.strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(text)
        optimized_query = str(parsed.get("optimized_query", last_msg))
        compressed_context = str(parsed.get("compressed_context", ""))
    except Exception:
        logger.exception("Intent parsing failed, falling back to raw input")
    writer({
        "type": "intent",
        "optimized_query": optimized_query,
        "compressed_context": compressed_context,
        "label": "正在理解你的问题...",
    })
    return {"optimized_query": optimized_query, "compressed_context": compressed_context}


def routing_node(state: ChatState, llm: BaseChatModel) -> dict:
    """Classify whether the user question needs each knowledge source."""
    writer = get_stream_writer()
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
        "Routing decision for '%s...': manual=%s, forum=%s, "
        "manual_query=%s, forum_query=%s",
        last_msg[:50], search_manual, search_forum,
        search_query_manual, search_query_forum,
    )
    writer({
        "type": "status",
        "node": "routing",
        "label": "正在分析你的问题...",
        "decision": {
            "search_manual": search_manual,
            "search_forum": search_forum,
        },
    })
    return {
        "search_manual": search_manual,
        "search_forum": search_forum,
        "search_query_manual": search_query_manual,
        "search_query_forum": search_query_forum,
    }


def manual_retrieval_node(state: ChatState, chroma: ChromaManager) -> dict:
    """Retrieve chunks from the student manual collection."""
    writer = get_stream_writer()
    if not state.get("search_manual"):
        return {"manual_chunks": []}
    query = state.get("search_query_manual") or ""
    if not query:
        return {"manual_chunks": [], "search_manual": False}
    chunks = chroma.retrieve(COLLECTION_MANUAL, query)
    logger.info("Manual retrieval: %d chunks", len(chunks))
    previews = [{"preview": c, "source": SOURCE_MANUAL_LABEL} for c in chunks]
    writer({
        "type": "retrieval",
        "source": SOURCE_MANUAL_KEY,
        "label": "已检索到【学生手册】相关规定" if chunks else "【学生手册】未检索到相关内容",
        "chunks": previews,
    })
    return {"manual_chunks": chunks}


def forum_retrieval_node(state: ChatState, chroma: ChromaManager) -> dict:
    """Retrieve chunks from the school forum collection."""
    writer = get_stream_writer()
    if not state.get("search_forum"):
        return {"forum_chunks": []}
    query = state.get("search_query_forum") or ""
    if not query:
        return {"forum_chunks": [], "search_forum": False}
    chunks = chroma.retrieve(COLLECTION_FORUM, query)
    logger.info("Forum retrieval: %d chunks", len(chunks))
    previews = [{"preview": c, "source": SOURCE_FORUM_LABEL} for c in chunks]
    writer({
        "type": "retrieval",
        "source": SOURCE_FORUM_KEY,
        "label": "已检索到【学校贴吧】相关讨论" if chunks else "【学校贴吧】未检索到相关内容",
        "chunks": previews,
    })
    return {"forum_chunks": chunks}


# ── Scoring node ──

def scoring_node(state: ChatState, scoring_llm: BaseChatModel) -> dict:
    """Score and compress each retrieved chunk for relevance."""
    writer = get_stream_writer()
    manual_chunks = state.get("manual_chunks", [])
    forum_chunks = state.get("forum_chunks", [])
    all_chunks: list[tuple[str, str]] = []
    for c in manual_chunks:
        all_chunks.append((c, SOURCE_MANUAL_LABEL))
    for c in forum_chunks:
        all_chunks.append((c, SOURCE_FORUM_LABEL))

    if not all_chunks:
        writer({"type": "scoring", "source": "done", "done": True})
        return {"scored_chunks": []}

    user_question = state["messages"][-1].content if state["messages"] else ""
    scored_chunks: list[dict] = []
    source_counters: dict[str, int] = {}

    for chunk_text, source in all_chunks:
        source_key = SOURCE_LABEL_TO_KEY[source]
        idx = source_counters.get(source_key, 0)
        source_counters[source_key] = idx + 1

        score = 0
        compressed = ""
        try:
            safe_question = user_question[:MAX_QUESTION_CHARS]
            safe_chunk = chunk_text[:MAX_CHUNK_INPUT_CHARS]
            logger.debug("Scoring prompt for %s chunk %d: user_question=%.50s..., chunk=%.50s...",
                         source_key, idx, user_question, chunk_text)
            response: AIMessage = scoring_llm.invoke([
                SystemMessage(content=SCORING_SYSTEM_PROMPT),
                HumanMessage(content=(
                    f"资料文本：{source}\n"
                    f"用户问题：{safe_question}\n"
                    f"文本内容：{safe_chunk}"
                )),
            ])
            text = response.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(text)
            score = max(0, min(100, int(parsed.get("score", 0))))
            compressed = parsed.get("compressed", "")
            logger.info("Scored %s chunk %d: score=%d, compressed_len=%d",
                        source_key, idx, score, len(compressed))
        except Exception:
            logger.exception("Scoring failed for %s chunk %d, defaulting to 0", source_key, idx)
            score = 0
            compressed = ""

        scored_chunks.append({
            "original": chunk_text,
            "source": source,
            "score": score,
            "compressed": compressed,
        })
        writer({
            "type": "scoring",
            "source": source_key,
            "index": idx,
            "score": score,
            "compressed": compressed,
        })

    writer({"type": "scoring", "source": "done", "done": True})
    return {"scored_chunks": scored_chunks}


# ── Answer node ──

async def answer_node(state: ChatState, chat_llm: BaseChatModel, top_k_scored: int = 3) -> dict:
    """Generate the final answer using retrieved context, streaming tokens."""
    writer = get_stream_writer()
    scored = state.get("scored_chunks", [])
    manual_chunks = state.get("manual_chunks", [])
    forum_chunks = state.get("forum_chunks", [])

    if scored and any(c["score"] > 0 and c["compressed"] for c in scored):
        sorted_scored = sorted(scored, key=lambda c: c["score"], reverse=True)[:top_k_scored]
        manual_context = "\n\n".join(
            c["compressed"][:MAX_COMPRESSED_CHARS] for c in sorted_scored
            if c["source"] == SOURCE_MANUAL_LABEL and c["score"] > 0 and c["compressed"]
        )
        forum_context = "\n\n".join(
            c["compressed"][:MAX_COMPRESSED_CHARS] for c in sorted_scored
            if c["source"] == SOURCE_FORUM_LABEL and c["score"] > 0 and c["compressed"]
        )
        if not manual_context:
            manual_context = "（未检索到相关内容）"
        if not forum_context:
            forum_context = "（未检索到相关内容）"
    else:
        manual_context = "\n\n".join(manual_chunks) if manual_chunks else "（未检索到相关内容）"
        forum_context = "\n\n".join(forum_chunks) if forum_chunks else "（未检索到相关内容）"

    has_context = bool(manual_chunks or forum_chunks)
    messages = list(state["messages"])

    if has_context:
        context_msg = SystemMessage(
            RETRIEVAL_CONTEXT_TEMPLATE.format(
                manual_context=manual_context.replace("{", "{{").replace("}", "}}"),
                forum_context=forum_context.replace("{", "{{").replace("}", "}}"),
            )
        )
        messages.insert(0, context_msg)

    full_response = ""
    async for chunk in chat_llm.astream(messages):
        if chunk.content:
            full_response += chunk.content
            writer({"type": "token", "token": chunk.content})

    return {"messages": [AIMessage(content=full_response)]}


# ── Conditional edge ──

def should_retrieve(state: ChatState) -> str:
    """Return the next node: retrieval node or scoring_node."""
    if state.get("search_manual") and not state.get("manual_chunks"):
        return "manual_retrieval_node"
    if state.get("search_forum") and not state.get("forum_chunks"):
        return "forum_retrieval_node"
    return "scoring_node"


# ── Graph builder ──

def compile_graph(
    intent_llm: BaseChatModel,
    routing_llm: BaseChatModel,
    chroma: ChromaManager,
    chat_llm: BaseChatModel,
    scoring_llm: BaseChatModel,
    top_k_scored: int = 3,
) -> StateGraph:
    """Build and compile the LangGraph state graph.

    Args:
        routing_llm: The LLM instance for the routing node.
        chroma: The ChromaDB manager instance.
        chat_llm: The LLM instance for the answer node (streaming).
        scoring_llm: The LLM instance for the scoring node.
        top_k_scored: Max scored chunks to include in final context.

    Returns:
        A compiled ``StateGraph``.
    """
    builder = StateGraph(ChatState)

    builder.add_node("intent_node", lambda state: intent_node(state, intent_llm))
    builder.add_node("routing_node", lambda state: routing_node(state, routing_llm))
    builder.add_node("manual_retrieval_node", lambda state: manual_retrieval_node(state, chroma))
    builder.add_node("forum_retrieval_node", lambda state: forum_retrieval_node(state, chroma))
    builder.add_node("scoring_node", lambda state: scoring_node(state, scoring_llm))

    async def _answer_node(state):
        return await answer_node(state, chat_llm, top_k_scored)

    builder.add_node("answer_node", _answer_node)

    builder.add_edge(START, "intent_node")
    builder.add_edge("intent_node", "routing_node")
    builder.add_conditional_edges("routing_node", should_retrieve, {
        "manual_retrieval_node": "manual_retrieval_node",
        "forum_retrieval_node": "forum_retrieval_node",
        "scoring_node": "scoring_node",
    })
    builder.add_conditional_edges("manual_retrieval_node", should_retrieve, {
        "forum_retrieval_node": "forum_retrieval_node",
        "scoring_node": "scoring_node",
    })
    builder.add_edge("forum_retrieval_node", "scoring_node")
    builder.add_edge("scoring_node", "answer_node")
    builder.add_edge("answer_node", END)

    return builder.compile()
