"""LangGraph state graph definition for the conversational agent.

Graph:
    START -> intent_node -> routing_node
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
    "当前系统是「广师大助手」，所属广东技术师范大学，你是系统的路由节点。\n"
    "核心任务：判断用户问题是否需要从校园知识库中检索相关信息。\n"
    "知识库包含两种类型：\n"
    "1. student_manual —— 《广东技术师范大学学生手册》，内容涵盖学籍、学位、奖惩、资助、住宿、安全、收费等正式规章制度。\n"
    "2. school_forum —— 学校贴吧帖子合集（2014-2026年），包含招生、宿舍、食堂、考研、就业、日常吐槽、校园文化等真实学生讨论。\n\n"

    "【判断规则】\n"
    "一、**不需要检索**的情况（search_manual=false, search_forum=false）：\n"
    "   - 单纯问候：你好、嗨、在吗、上午好等\n"
    "   - 简单感谢或告别：谢谢、拜拜、知道了等\n"
    "   - 无意义或测试：测试、123、？、随便发的内容\n"
    "   - 与广师大/校园生活完全无关的问题：今天天气、美国总统是谁、怎么做红烧肉等\n"
    "   - 用户要求不检索或闲聊（明确说“聊聊天”等）\n\n"

    "二、**需要检索**的情况：\n"
    "   - 问题明确涉及广师大的制度、规定、政策、学校申请相关问题 → 优先检索 student_manual\n"
    "   - 问题涉及校园生活、学生真实体验（宿舍、食堂、老师、社团、求职经验、吐槽等）→ 检索 school_forum\n"
    "   - 问题同时涉及规定和实际体验（如“旷课了还能去食堂吗”）→ 两者都检索\n"
    "   - 问题使用学校别称（广技师、广师大、gjs、技校等）且内容与学校相关 → 需要检索\n\n"

    "三、**查询生成优化**：\n"
    "   - 提取用户问题中的核心关键词（如“旷课 处分 次数”、“白云校区 宿舍 几人间”）。\n"
    "   - 去除口语化词汇和与检索无关的语气词。\n"
    "   - 如果用户问题模糊，可适当补充常见相关词（例如问“转专业难吗”→补充“转专业 条件 流程”）。\n"
    "   - 若不需要检索，对应查询字段留空字符串。\n\n"

    "【输出格式】\n"
    "只输出合法的 JSON 对象，不要输出任何其他解释或文本。\n"
    '{"search_manual": true/false, "search_forum": true/false,\n'
    ' "search_query_manual": "...", "search_query_forum": "..."}\n\n'

    "【典型示例】\n"
    "- 用户：\"你好\"\n"
    '  → {"search_manual": false, "search_forum": false, "search_query_manual": "", "search_query_forum": ""}\n'
    "- 用户：\"谢谢你的帮助\"\n"
    '  → {"search_manual": false, "search_forum": false, "search_query_manual": "", "search_query_forum": ""}\n'
    "- 用户：\"旷课几次会被处分？\"\n"
    '  → {"search_manual": true, "search_forum": false, "search_query_manual": "旷课 处分 次数 规定", "search_query_forum": ""}\n'
    "- 用户：\"白云校区食堂有什么好吃的？\"\n"
    '  → {"search_manual": false, "search_forum": true, "search_query_manual": "", "search_query_forum": "白云校区 食堂 推荐 好吃"}\n'
    "- 用户：\"听说学校要改名？到底叫什么？\"\n"
    '  → {"search_manual": false, "search_forum": true, "search_query_manual": "", "search_query_forum": "改名 广技师 广师大 简称 争议"}\n'
    "- 用户：\"申请助学金的流程是什么？\"\n"
    '  → {"search_manual": true, "search_forum": false, "search_query_manual": "助学金 申请 流程 条件", "search_query_forum": ""}\n'
    "- 用户：\"计算机专业就业怎么样？\"\n"
    '  → {"search_manual": false, "search_forum": true, "search_query_manual": "", "search_query_forum": "计算机 就业 薪资 实习"}\n'
    "- 用户：\"旷课了还能去食堂吃饭吗？\"\n"
    '  → {"search_manual": true, "search_forum": true, "search_query_manual": "旷课 处分 规定", "search_query_forum": "食堂 吃饭 经验"}\n'
    "- 用户：\"今天广州天气怎么样？\"\n"
    '  → {"search_manual": false, "search_forum": false, "search_query_manual": "", "search_query_forum": ""}\n'
    "- 用户：\"河源校区宿舍是几人间？\"\n"
    '  → {"search_manual": false, "search_forum": true, "search_query_manual": "", "search_query_forum": "河源校区 宿舍 几人间 环境"}\n\n'

    "请严格按照上述规则和格式进行判断和输出。"
)

RETRIEVAL_CONTEXT_TEMPLATE = (
    "当前系统是「广师大助手」，所属广东技术师范大学，你是系统的检索节点，。\n"
    "以下是从校园知识库中检索到的相关信息，请结合这些信息回答用户问题。\n"
    "如果检索到的内容与问题无关，请忽略它们。\n\n"
    "-----以下是从校园知识库中检索到的相关信息-----\n"
    "【学生手册】\n{manual_context}\n\n"
    "【学校贴吧】\n{forum_context}\n\n"
    "-----结束从校园知识库中检索到的相关信息------\n"
    "请用中文回答。\n"
    "【important你的核心任务】：以上是系统从校园知识库中检索到的相关信息给你辅助回答用户问题的信息，不是用户给你的，请结合这些信息回答用户问题。"
)

SCORING_SYSTEM_PROMPT = (
    "当前系统是「广师大助手」，所属广东技术师范大学，你是系统的评分节点，。\n"
    "你是一个校园助手的内容过滤器。你的任务是判断给定的资料文本是否与用户问题相关。\n\n"
    "【评分标准】\n"
    "100分：资料完全回答了用户问题，包含所有必要信息。\ "  # 注意转义
    "75-99分：资料与问题高度相关，能回答大部分内容，但可能缺少部分细节。\n"
    "50-74分：资料部分相关，只能间接或局部回答用户问题。\n"
    "1-49分：资料仅提及相关术语但实际不解决问题，或相关性很弱。\n"
    "0分：资料与用户问题完全无关，或资料为空。\n\n"
    "【输出格式】\n"
    "只输出合法的 JSON 对象，不要有任何额外解释。格式如下：\n"
    '{"score": 整数}'
)

INTENT_SYSTEM_PROMPT = (
    "当前系统是「广师大助手」，所属广东技术师范大学，你是系统的意图分析节点，。\n"
    "你是一个校园助手的意图分析器。你的任务：\n"
    "1. **优化用户问题** — 结合上下文分析用户问题，将用户当前问题改写成一个清晰、自包含、可直接用于检索的问题。\n"
    "   具体做法：\n"
    "   - 修复错别字、语法错误和不通顺的表达。\n"
    "   - 将指代不明的词（如“那个”“它”“那里”）替换为明确的实体。\n"
    "   - 如果问题缺少主语或关键信息，根据对话历史补充完整。\n"
    "   - 去除口头禅、语气词（如“嗯”“那个”“请问一下”），保留核心信息。\n"
    "   - 不要私自推理联想用户的情况（如迟到旷课会怎么样改为如果学生因故迟到或旷课，通常会有什么后果？ 没有提到因故这件事），只根据用户问题和对话历史。\n"
    "2. **压缩对话历史记录** — 从最近的对话中提取对回答当前问题有帮助的关键信息，输出一个简短的上下文摘要。\n"
    "   具体做法：\n"
    "   - 提取用户已经明确说过的事实。\n"
    "   - 提取用户已经表达过的目标或需求。\n"
    "   - 提取助手已经给出过的关键答案或信息。\n"
    "   - 忽略纯粹的问候、感谢、无关闲聊。\n"
    "输出必须是以下 JSON 格式，不要添加任何额外内容：\n"
    '{{"optimized_query": "...", "compressed_context": "..."}}'
)


# ── Answer node ──

ANSWER_SYSTEM_PROMPT = (
    "你是「广师大助手」，广东技术师范大学的温暖热心的校园助手。\n"
    "你以温暖、耐心、细致的方式回答同学们关于校园生活的各种问题。\n"
    "你熟悉广东技术师范大学的校园环境、规章制度、学习生活、校园文化等各方面信息。\n\n"
    "【核心原则】\n"
    "- 使用亲切、温暖的口吻，像热心的学长学姐一样回答问题\n"
    "- 回答要详细、具体、有用，结合检索到的校园知识库信息\n"
    "- 如果不确定的信息，要诚实说明，不要编造\n"
    "- 尊重每一位同学，营造包容、友善的校园氛围\n"
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
    retrieval_mode: str
    settings: dict


# ── Nodes ──

def _extract_json(text: str) -> str:
    best = text.strip()
    # 1. Try ```json ... ``` block first
    if "```json" in best:
        start = best.find("```json") + 7
        end = best.find("```", start)
        if end != -1:
            return best[start:end].strip()
    # 2. Try extracting the first { ... } object
    brace_start = best.find("{")
    brace_end = best.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return best[brace_start:brace_end + 1].strip()
    # 3. Fallback to raw text
    return best


RETRY_HINT_TEMPLATE = (
    "注意：上次输出格式错误。\n"
    "请只输出合法的 JSON 对象，格式如下：\n"
    "{expected_format}\n"
    "不要包含任何其他解释或文本。"
)


def _parse_json_llm_response(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    expected_format: str,
) -> dict | None:
    """Invoke LLM, parse JSON response, retry once on parse failure.

    Returns the parsed dict on success, or None if both attempts fail
    (or LLM invocation itself fails).
    """
    for attempt in range(2):
        try:
            response: AIMessage = llm.invoke(messages)
            text = _extract_json(response.content)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError, TypeError):
            if attempt == 0:
                logger.warning(
                    "JSON parse failed (attempt 1/2), retrying with hint. "
                    "Expected format: %s", expected_format,
                )
                messages = [
                    *messages,
                    HumanMessage(
                        content=RETRY_HINT_TEMPLATE.format(expected_format=expected_format)
                    ),
                ]
            else:
                logger.error("JSON parse failed after retry, falling back to defaults")
                return None
        except Exception:
            logger.exception("LLM invocation failed, falling back to defaults")
            return None
    return None


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
    user_text = (
        f"对话历史记录：\n{formatted_history}\n\n"
        f"用户问题： {last_msg}"
    )
    optimized_query = last_msg
    compressed_context = ""
    parsed = _parse_json_llm_response(
        intent_llm,
        [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ],
        expected_format='{"optimized_query": "...", "compressed_context": "..."}',
    )
    if parsed:
        optimized_query = str(parsed.get("optimized_query", last_msg))
        compressed_context = str(parsed.get("compressed_context", ""))
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
    retrieval_mode = state.get("retrieval_mode", "auto")

    # Non-auto modes: skip LLM, force flags based on user selection
    if retrieval_mode != "auto":
        search_manual = retrieval_mode in ("manual", "both")
        search_forum = retrieval_mode in ("forum", "both")
        raw = state.get("optimized_query", "")
        search_query = raw.strip() or (state["messages"][-1].content if state["messages"] else "")
        writer({
            "type": "status",
            "node": "routing",
            "label": "正在分析你的问题...",
            "decision": {
                "search_manual": search_manual,
                "search_forum": search_forum,
            },
        })
        logger.info(
            "Routing (user override '%s'): manual=%s, forum=%s",
            retrieval_mode, search_manual, search_forum,
        )
        return {
            "search_manual": search_manual,
            "search_forum": search_forum,
            "search_query_manual": search_query if search_manual else "",
            "search_query_forum": search_query if search_forum else "",
        }

    # Auto mode: LLM-based routing below
    raw = state.get("optimized_query", "")
    last_msg = raw.strip() or (state["messages"][-1].content if state["messages"] else "")
    parsed = _parse_json_llm_response(
        llm,
        [
            SystemMessage(content=ROUTING_SYSTEM_PROMPT),
            HumanMessage(content=last_msg),
        ],
        expected_format=(
            '{"search_manual": true/false, "search_forum": true/false, '
            '"search_query_manual": "...", "search_query_forum": "..."}'
        ),
    )
    if parsed:
        search_manual = bool(parsed.get("search_manual", False))
        search_forum = bool(parsed.get("search_forum", False))
        search_query_manual = parsed.get("search_query_manual", "")
        search_query_forum = parsed.get("search_query_forum", "")
    else:
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
    settings = state.get("settings", {})
    top_k = settings.get("top_k_manual") if settings else None
    chunks = chroma.retrieve(COLLECTION_MANUAL, query, top_k=top_k)
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
    settings = state.get("settings", {})
    top_k = settings.get("top_k_forum") if settings else None
    chunks = chroma.retrieve(COLLECTION_FORUM, query, top_k=top_k)
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

    raw = state.get("optimized_query", "")
    user_question = raw.strip() or (state["messages"][-1].content if state["messages"] else "")
    scored_chunks: list[dict] = []
    source_counters: dict[str, int] = {}

    for chunk_text, source in all_chunks:
        source_key = SOURCE_LABEL_TO_KEY[source]
        idx = source_counters.get(source_key, 0)
        source_counters[source_key] = idx + 1

        score = 0
        safe_question = user_question[:MAX_QUESTION_CHARS]
        safe_chunk = chunk_text[:MAX_CHUNK_INPUT_CHARS]
        logger.debug("Scoring prompt for %s chunk %d: user_question=%.50s..., chunk=%.50s...",
                     source_key, idx, user_question, chunk_text)
        parsed = _parse_json_llm_response(
            scoring_llm,
            [
                SystemMessage(content=SCORING_SYSTEM_PROMPT),
                HumanMessage(content=(
                    f"资料文本：{source}\n"
                    f"用户问题：{safe_question}\n"
                    f"文本内容：{safe_chunk}"
                )),
            ],
            expected_format='{"score": 整数}',
        )
        if parsed:
            score = max(0, min(100, int(parsed.get("score", 0))))
            logger.info("Scored %s chunk %d: score=%d",
                        source_key, idx, score)
        else:
            logger.warning("Scoring failed for %s chunk %d, defaulting to 0", source_key, idx)
            score = 0

        scored_chunks.append({
            "original": chunk_text,
            "source": source,
            "score": score,
        })
        writer({
            "type": "scoring",
            "source": source_key,
            "index": idx,
            "score": score,
        })

    writer({"type": "scoring", "source": "done", "done": True})
    return {"scored_chunks": scored_chunks}




async def answer_node(state: ChatState, chat_llm: BaseChatModel) -> dict:
    """Generate the final answer using optimized query, compressed context, and retrieved context."""
    writer = get_stream_writer()
    settings = state.get("settings", {})
    top_k_scored = settings.get("top_k_scored", 3) if settings else 3
    scored = state.get("scored_chunks", [])
    manual_chunks = state.get("manual_chunks", [])
    forum_chunks = state.get("forum_chunks", [])

    if scored and any(c["score"] > 0 for c in scored):
        sorted_scored = sorted(scored, key=lambda c: c["score"], reverse=True)[:top_k_scored]
        manual_context = "\n\n".join(
            c["original"] for c in sorted_scored
            if c["source"] == SOURCE_MANUAL_LABEL and c["score"] > 0
        )
        forum_context = "\n\n".join(
            c["original"] for c in sorted_scored
            if c["source"] == SOURCE_FORUM_LABEL and c["score"] > 0
        )
        if not manual_context:
            manual_context = "（未检索到相关内容）"
        if not forum_context:
            forum_context = "（未检索到相关内容）"
    else:
        manual_context = "\n\n".join(manual_chunks) if manual_chunks else "（未检索到相关内容）"
        forum_context = "\n\n".join(forum_chunks) if forum_chunks else "（未检索到相关内容）"

    context_parts = []
    if manual_chunks or forum_chunks:
        context_parts.append(
            RETRIEVAL_CONTEXT_TEMPLATE.format(
                manual_context=manual_context.replace("{", "{{").replace("}", "}}"),
                forum_context=forum_context.replace("{", "{{").replace("}", "}}"),
            )
        )
    compressed = state.get("compressed_context", "")
    optimized = state.get("optimized_query", "")
    last_raw = state["messages"][-1].content if state["messages"] else ""
    user_question = optimized.strip() or last_raw

    if context_parts:
        if compressed:
            context_parts.append(
                "【以下是对话摘要（历史上下文）和用户这轮发给你的对话消息】\n"
                f"对话摘要（历史上下文）：{compressed}\n"
                f"用户对话消息：{user_question}"
            )
        else:
            context_parts.append(f"用户对话消息：{user_question}")
        user_content = "\n\n".join(context_parts)
    else:
        user_content = user_question

    messages = [
        SystemMessage(content=ANSWER_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

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
        return await answer_node(state, chat_llm)

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
