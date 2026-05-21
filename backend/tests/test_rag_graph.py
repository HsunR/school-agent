"""Tests for the RAG-enabled LangGraph pipeline."""

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
