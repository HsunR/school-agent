"""Tests for the RAG-enabled LangGraph pipeline."""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, SystemMessage

from app.graph.graph import (
    ChatState,
    routing_node,
    manual_retrieval_node,
    forum_retrieval_node,
    scoring_node,
    should_retrieve,
)


@patch("app.graph.graph.get_stream_writer")
def test_routing_node_parses_json(mock_writer):
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(
        content='{"search_manual": true, "search_forum": false, '
                '"search_query_manual": "宿舍 规定", '
                '"search_query_forum": ""}'
    )
    state: ChatState = {
        "messages": [HumanMessage(content="What are the dorm rules?")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = routing_node(state, llm)
    assert result["search_manual"] is True
    assert result["search_forum"] is False
    assert result["search_query_manual"] != ""
    assert result["search_query_forum"] == ""


@patch("app.graph.graph.get_stream_writer")
def test_routing_node_fallback_on_bad_json(mock_writer):
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="not json")
    state: ChatState = {
        "messages": [HumanMessage(content="hi")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = routing_node(state, llm)
    assert result["search_manual"] is False
    assert result["search_forum"] is False
    assert result["search_query_manual"] == ""
    assert result["search_query_forum"] == ""


@patch("app.graph.graph.get_stream_writer")
def test_manual_retrieval_node_emits_full_content(mock_writer):
    chroma = MagicMock()
    long_content = "a" * 500
    chroma.retrieve.return_value = [long_content]
    state: ChatState = {
        "messages": [],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "宿舍 规定",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    manual_retrieval_node(state, chroma)
    written = mock_writer.return_value.call_args[0][0]
    assert written["type"] == "retrieval"
    assert len(written["chunks"]) == 1
    assert written["chunks"][0]["preview"] == long_content


@patch("app.graph.graph.get_stream_writer")
def test_manual_retrieval_node_skips_when_query_empty(mock_writer):
    """When search_manual=True but search_query_manual is empty, should return empty and disable search."""
    chroma = MagicMock()
    state: ChatState = {
        "messages": [],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = manual_retrieval_node(state, chroma)
    assert result["manual_chunks"] == []
    assert result["search_manual"] is False
    chroma.retrieve.assert_not_called()


@patch("app.graph.graph.get_stream_writer")
def test_forum_retrieval_node_skips_when_query_empty(mock_writer):
    """When search_forum=True but search_query_forum is empty, should return empty and disable search."""
    chroma = MagicMock()
    state: ChatState = {
        "messages": [],
        "search_manual": False,
        "search_forum": True,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = forum_retrieval_node(state, chroma)
    assert result["forum_chunks"] == []
    assert result["search_forum"] is False
    chroma.retrieve.assert_not_called()


def test_should_retrieve_manual_first():
    state: ChatState = {
        "messages": [],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    assert should_retrieve(state) == "manual_retrieval_node"


def test_should_retrieve_forum_after_manual():
    state: ChatState = {
        "messages": [],
        "search_manual": False,
        "search_forum": True,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    assert should_retrieve(state) == "forum_retrieval_node"


def test_should_retrieve_answer_node_when_no_search():
    state: ChatState = {
        "messages": [],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    assert should_retrieve(state) == "scoring_node"


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_emits_scoring_events(mock_writer):
    scoring_llm = MagicMock()
    scoring_llm.invoke.return_value = AIMessage(
        content='{"score": 85, "compressed": "保留的关键内容"}'
    )
    state: ChatState = {
        "messages": [HumanMessage(content="宿舍管理费多少")],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "宿舍 规定",
        "search_query_forum": "",
        "manual_chunks": ["宿舍管理费每学期500元。收费时间为每学期开学第一周。"],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = scoring_node(state, scoring_llm)
    assert "scored_chunks" in result
    assert len(result["scored_chunks"]) == 1
    assert result["scored_chunks"][0]["score"] == 85
    assert result["scored_chunks"][0]["compressed"] == "保留的关键内容"
    assert result["scored_chunks"][0]["source"] == "学生手册"


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_handles_empty_chunks(mock_writer):
    scoring_llm = MagicMock()
    state: ChatState = {
        "messages": [HumanMessage(content="hi")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = scoring_node(state, scoring_llm)
    assert result["scored_chunks"] == []


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_fallback_on_llm_error(mock_writer):
    scoring_llm = MagicMock()
    scoring_llm.invoke.side_effect = Exception("API error")
    state: ChatState = {
        "messages": [HumanMessage(content="宿舍")],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "宿舍",
        "search_query_forum": "",
        "manual_chunks": ["内容1"],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    result = scoring_node(state, scoring_llm)
    assert len(result["scored_chunks"]) == 1
    assert result["scored_chunks"][0]["score"] == 0
    assert result["scored_chunks"][0]["compressed"] == ""


@patch("app.graph.graph.get_stream_writer")
@pytest.mark.asyncio
async def test_answer_node_falls_back_to_raw_chunks_when_all_scores_zero(mock_writer):
    """answer_node should use raw chunks when all scored_chunks have score 0."""
    from app.graph.graph import answer_node

    chat_llm = MagicMock()
    async def _mock_astream(messages):
        # Capture the context from the system message
        for msg in messages:
            if isinstance(msg, SystemMessage):
                assert "宿舍管理费每学期500元" in msg.content, (
                    "Expected raw chunk content in context, got: %s", msg.content
                )
        yield AIMessageChunk(content="Hello World!")
    chat_llm.astream = _mock_astream

    state = {
        "messages": [HumanMessage(content="宿舍管理费多少")],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "宿舍",
        "search_query_forum": "",
        "manual_chunks": ["宿舍管理费每学期500元"],
        "forum_chunks": [],
        "scored_chunks": [
            {"original": "宿舍管理费每学期500元", "source": "学生手册", "score": 0, "compressed": ""},
        ],
    }
    result = await answer_node(state, chat_llm)
    assert "messages" in result


@patch("app.graph.graph.get_stream_writer")
@pytest.mark.asyncio
async def test_answer_node_uses_top_k_scored_chunks(mock_writer):
    """answer_node should sort by score descending and take only top_k_scored."""
    from app.graph.graph import answer_node

    chat_llm = MagicMock()
    captured_context: list[str] = []

    async def _mock_astream(messages):
        for msg in messages:
            if isinstance(msg, SystemMessage):
                captured_context.append(msg.content)
        yield AIMessageChunk(content="Hello World!")
    chat_llm.astream = _mock_astream

    state = {
        "messages": [HumanMessage(content="东校区宿舍")],
        "search_manual": False,
        "search_forum": True,
        "search_query_manual": "",
        "search_query_forum": "宿舍",
        "manual_chunks": [],
        "forum_chunks": ["帖A", "帖B", "帖C", "帖D"],
        "scored_chunks": [
            {"original": "帖A", "source": "学校贴吧", "score": 90, "compressed": "帖A内容"},
            {"original": "帖B", "source": "学校贴吧", "score": 20, "compressed": "帖B内容"},
            {"original": "帖C", "source": "学校贴吧", "score": 80, "compressed": "帖C内容"},
            {"original": "帖D", "source": "学校贴吧", "score": 60, "compressed": "帖D内容"},
        ],
    }
    result = await answer_node(state, chat_llm, top_k_scored=2)
    assert "messages" in result
    context = captured_context[0] if captured_context else ""
    # top 2 by score: 帖A(90) and 帖C(80)
    assert "帖A内容" in context
    assert "帖C内容" in context
    assert "帖B内容" not in context
    assert "帖D内容" not in context


@patch("app.graph.graph.get_stream_writer")
def test_intent_node_emits_intent_event(mock_writer):
    """Verify intent_node emits correct optimized_query and compressed_context."""
    from app.graph.graph import intent_node

    chat_state = {
        "messages": [HumanMessage(content="旷课了怎么办")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
        "optimized_query": "",
        "compressed_context": "",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json.dumps({
        "optimized_query": "旷课处罚规定查询",
        "compressed_context": "用户询问旷课后果",
    }))
    result = intent_node(chat_state, mock_llm)
    assert result["optimized_query"] == "旷课处罚规定查询"
    assert result["compressed_context"] == "用户询问旷课后果"


@patch("app.graph.graph.get_stream_writer")
def test_intent_node_fallback_on_bad_json(mock_writer):
    """Verify intent_node falls back to raw input when LLM returns bad JSON."""
    from app.graph.graph import intent_node

    chat_state = {
        "messages": [HumanMessage(content="原始问题")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
        "optimized_query": "",
        "compressed_context": "",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="not valid json")
    result = intent_node(chat_state, mock_llm)
    assert result["optimized_query"] == "原始问题"
    assert result["compressed_context"] == ""


@patch("app.graph.graph.get_stream_writer")
def test_routing_node_uses_optimized_query(mock_writer):
    """Verify routing node uses optimized_query when available."""
    from app.graph.graph import routing_node

    chat_state = {
        "messages": [HumanMessage(content="原始问题很多错别字")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
        "optimized_query": "优化后的问题",
        "compressed_context": "对话摘要",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json.dumps({
        "search_manual": True, "search_forum": False,
        "search_query_manual": "查询关键词", "search_query_forum": "",
    }))
    routing_node(chat_state, mock_llm)
    call_text = str(mock_llm.invoke.call_args)
    assert "优化后的问题" in call_text
    assert "原始问题很多错别字" not in call_text


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_uses_optimized_query(mock_writer):
    """Verify scoring node uses optimized_query when available."""
    from app.graph.graph import scoring_node

    chat_state = {
        "messages": [HumanMessage(content="原始问题")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": ["宿舍管理费每学期500元"],
        "forum_chunks": [],
        "scored_chunks": [],
        "optimized_query": "优化后的问题",
        "compressed_context": "对话摘要",
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=json.dumps({
        "score": 85, "compressed": "500元",
    }))
    scoring_node(chat_state, mock_llm)
    call_text = str(mock_llm.invoke.call_args)
    assert "优化后的问题" in call_text
    assert "原始问题" not in call_text


@pytest.mark.asyncio
async def test_answer_node_injects_compressed_context():
    """Verify answer_node prepends compressed_context SystemMessage."""
    from app.graph.graph import answer_node
    from langchain_core.messages import HumanMessage

    chat_llm = MagicMock()
    captured_context: list[str] = []

    async def _mock_astream(messages):
        for msg in messages:
            if isinstance(msg, SystemMessage):
                captured_context.append(msg.content)
        yield AIMessage(content="回答")
    chat_llm.astream = _mock_astream

    state = {
        "messages": [HumanMessage(content="用户问题")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": ["宿舍管理费500元"],
        "forum_chunks": [],
        "scored_chunks": [{"original": "宿舍管理费500元", "source": "学生手册", "score": 85, "compressed": "500元"}],
        "optimized_query": "优化问题",
        "compressed_context": "用户询问关于宿舍管理费的问题",
    }
    with patch("app.graph.graph.get_stream_writer"):
        await answer_node(state, chat_llm)

    assert any("对话摘要（历史上下文）" in c for c in captured_context), "compressed_context not found"


@pytest.mark.asyncio
async def test_answer_node_skips_empty_compressed_context():
    """Verify answer_node skips compressed_context when empty."""
    from app.graph.graph import answer_node
    from langchain_core.messages import HumanMessage

    chat_llm = MagicMock()
    captured_context: list[str] = []

    async def _mock_astream(messages):
        for msg in messages:
            if isinstance(msg, SystemMessage):
                captured_context.append(msg.content)
        yield AIMessage(content="回答")
    chat_llm.astream = _mock_astream

    state = {
        "messages": [HumanMessage(content="用户问题")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": ["宿舍管理费500元"],
        "forum_chunks": [],
        "scored_chunks": [],
        "optimized_query": "优化问题",
        "compressed_context": "",
    }
    with patch("app.graph.graph.get_stream_writer"):
        await answer_node(state, chat_llm)

    assert not any("对话摘要（历史上下文）" in c for c in captured_context), "compressed_context should not appear"
