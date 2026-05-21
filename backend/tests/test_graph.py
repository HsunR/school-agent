"""Tests for LangGraph state graph definition.

Tests cover:
- Graph compilation
- Graph structure (nodes, edges)
- Graph invocation returns expected message structure
"""

from typing import TypedDict, Annotated, Sequence
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGenerationChunk, ChatGeneration, ChatResult
from langgraph.graph import START, END

from app.graph.graph import ChatState, compile_graph


@pytest.fixture
def mock_chroma() -> MagicMock:
    """Return a mock ChromaManager for graph compilation."""
    chroma = MagicMock()
    chroma.retrieve.return_value = ["mock chunk"]
    return chroma


class MockStreamingChatModel(BaseChatModel):
    """A mock chat model that streams tokens for testing."""

    streaming: bool = True
    tokens: list = ["Hello", " ", "World", "!"]

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        for token in self.tokens:
            chunk = AIMessageChunk(content=token)
            if run_manager:
                run_manager.on_llm_new_token(token, chunk=chunk)
            yield ChatGenerationChunk(message=chunk)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        full_content = "".join(self.tokens)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=full_content))])

    @property
    def _llm_type(self) -> str:
        return "mock-streaming"


class TestGraphCompilation:
    """Graph should compile without errors."""

    def test_graph_compiles(self, mock_chroma):
        """compile_graph should return a compiled graph."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        assert graph is not None

    def test_graph_is_compiled(self, mock_chroma):
        """The returned graph should be a CompiledStateGraph."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        assert "compile" not in dir(type(graph)) or hasattr(graph, "invoke")
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")


class TestGraphStructure:
    """Graph should have correct structure."""

    def test_has_routing_node(self, mock_chroma):
        """Graph should have a 'routing_node' node."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        node_names = list(graph.nodes.keys())
        assert "routing_node" in node_names, f"Expected 'routing_node' in nodes, got {node_names}"

    def test_has_retrieval_nodes(self, mock_chroma):
        """Graph should have retrieval nodes for both collections."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        node_names = list(graph.nodes.keys())
        assert "manual_retrieval_node" in node_names
        assert "forum_retrieval_node" in node_names

    def test_start_to_routing_edge(self, mock_chroma):
        """There should be an edge from START to routing_node."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        g = graph.get_graph()
        edges = g.edges
        edge_pairs = [(e.source, e.target) for e in edges]
        assert ("__start__", "routing_node") in edge_pairs, (
            f"Expected START->routing_node edge, got {edge_pairs}"
        )

    def test_routing_to_conditional_edges(self, mock_chroma):
        """Routing node should have conditional edges to retrieval nodes or END."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        g = graph.get_graph()
        edges = g.edges
        routing_edges = [(e.source, e.target) for e in edges if e.source == "routing_node"]
        assert len(routing_edges) >= 2, (
            f"Expected routing_node conditional edges, got {routing_edges}"
        )
        targets = {t for _, t in routing_edges}
        assert "manual_retrieval_node" in targets or "forum_retrieval_node" in targets


class TestGraphInvocation:
    """Graph should correctly route messages and set search flags."""

    def test_invoke_returns_messages(self, mock_chroma):
        """Graph invoke should return a dict with 'messages' key."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        result = graph.invoke({"messages": [HumanMessage(content="test")]})
        assert isinstance(result, dict)
        assert "messages" in result

    def test_invoke_sets_search_flags(self, mock_chroma):
        """Graph should set search_manual and search_forum to False by default
        when routing can't parse the LLM response as valid JSON."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        result = graph.invoke({"messages": [HumanMessage(content="test")]})
        assert result.get("search_manual") is False
        assert result.get("search_forum") is False
        assert result.get("search_query_manual") == ""
        assert result.get("search_query_forum") == ""

    @pytest.mark.asyncio
    async def test_ainvoke_returns_messages(self, mock_chroma):
        """Async invoke should also return messages."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        result = await graph.ainvoke({"messages": [HumanMessage(content="test")]})
        assert isinstance(result, dict)
        assert "messages" in result

    def test_invoke_with_system_message(self, mock_chroma):
        """Graph should work with system + user messages."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)
        result = graph.invoke({
            "messages": [
                SystemMessage(content="Be concise"),
                HumanMessage(content="test"),
            ],
        })
        # Messages pass through unchanged (graph doesn't generate responses)
        assert len(result["messages"]) == 2
        assert result["messages"][0].content == "Be concise"
        assert result["messages"][1].content == "test"

    @pytest.mark.asyncio
    async def test_astream_events_yields_token_events(self, mock_chroma):
        """astream_events should yield on_chat_model_stream events."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)

        events = []
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content="test")]},
            version="v2",
        ):
            events.append(event)

        stream_events = [
            e for e in events if e.get("event") == "on_chat_model_stream"
        ]
        assert len(stream_events) > 0

        first = stream_events[0]
        chunk = first.get("data", {}).get("chunk")
        assert chunk is not None
        assert chunk.content

    def test_conversation_context_preserved(self, mock_chroma):
        """Graph should preserve prior conversation context (messages pass through)."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, mock_chroma)

        result1 = graph.invoke({
            "messages": [HumanMessage(content="First message")],
        })
        assert len(result1["messages"]) == 1
        assert result1["messages"][0].content == "First message"

        result2 = graph.invoke({
            "messages": [HumanMessage(content="First message"), HumanMessage(content="Second message")],
        })
        assert len(result2["messages"]) == 2
        assert result2["messages"][0].content == "First message"
        assert result2["messages"][1].content == "Second message"
