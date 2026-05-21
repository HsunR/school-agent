"""Tests for the RAG-enabled LangGraph pipeline."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.graph import (
    ChatState,
    routing_node,
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
    }
    result = routing_node(state, llm)
    assert result["search_manual"] is False
    assert result["search_forum"] is False
    assert result["search_query_manual"] == ""
    assert result["search_query_forum"] == ""


def test_should_retrieve_manual_first():
    state: ChatState = {
        "messages": [],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
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
    }
    assert should_retrieve(state) == "answer_node"
