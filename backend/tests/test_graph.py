"""Tests for LangGraph state graph definition.

Tests cover:
- Graph compilation
- Graph structure (nodes, edges)
- Graph invocation returns expected message structure
"""

from typing import TypedDict, Annotated, Sequence
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGenerationChunk, ChatGeneration, ChatResult
from langgraph.graph import START

from app.graph.graph import ChatState, compile_graph, manual_retrieval_node


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
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        assert graph is not None

    def test_graph_is_compiled(self, mock_chroma):
        """The returned graph should be a CompiledStateGraph."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        assert "compile" not in dir(type(graph)) or hasattr(graph, "invoke")
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")


class TestGraphStructure:
    """Graph should have correct structure."""

    def test_has_routing_node(self, mock_chroma):
        """Graph should have a 'routing_node' node."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        node_names = list(graph.nodes.keys())
        assert "routing_node" in node_names, f"Expected 'routing_node' in nodes, got {node_names}"

    def test_has_retrieval_nodes(self, mock_chroma):
        """Graph should have retrieval nodes for both collections."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        node_names = list(graph.nodes.keys())
        assert "manual_retrieval_node" in node_names
        assert "forum_retrieval_node" in node_names

    def test_has_answer_node(self, mock_chroma):
        """Graph should have an 'answer_node' node."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        node_names = list(graph.nodes.keys())
        assert "answer_node" in node_names, f"Expected 'answer_node' in nodes, got {node_names}"

    def test_start_to_intent_to_routing_edges(self, mock_chroma):
        """There should be edges from START to intent_node to routing_node."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        g = graph.get_graph()
        edges = g.edges
        edge_pairs = [(e.source, e.target) for e in edges]
        assert ("__start__", "intent_node") in edge_pairs, (
            f"Expected START->intent_node edge, got {edge_pairs}"
        )
        assert ("intent_node", "routing_node") in edge_pairs, (
            f"Expected intent_node->routing_node edge, got {edge_pairs}"
        )

    def test_routing_to_conditional_edges(self, mock_chroma):
        """Routing node should have conditional edges to retrieval or answer nodes."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
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

    @pytest.mark.asyncio
    async def test_ainvoke_returns_messages(self, mock_chroma):
        """Graph ainvoke should return a dict with 'messages' key."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        result = await graph.ainvoke({"messages": [HumanMessage(content="test")]})
        assert isinstance(result, dict)
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_ainvoke_sets_search_flags(self, mock_chroma):
        """Graph should set search flags to False when routing can't parse JSON."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        result = await graph.ainvoke({"messages": [HumanMessage(content="test")]})
        assert result.get("search_manual") is False
        assert result.get("search_forum") is False
        assert result.get("search_query_manual") == ""
        assert result.get("search_query_forum") == ""

    @pytest.mark.asyncio
    async def test_ainvoke_with_system_message(self, mock_chroma):
        """Graph should work with system + user messages."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)
        result = await graph.ainvoke({
            "messages": [
                SystemMessage(content="Be concise"),
                HumanMessage(content="test"),
            ],
        })
        assert len(result["messages"]) == 3
        assert result["messages"][0].content == "Be concise"
        assert result["messages"][1].content == "test"
        assert isinstance(result["messages"][2], AIMessage)

    @pytest.mark.asyncio
    async def test_astream_custom_yields_token_events(self, mock_chroma):
        """graph.astream(stream_mode='custom') should yield token events from answer_node."""
        routing_llm = MockStreamingChatModel()
        routing_llm.streaming = False
        chat_llm = MockStreamingChatModel()
        graph = compile_graph(routing_llm, routing_llm, mock_chroma, chat_llm, routing_llm)

        state: ChatState = {
            "messages": [HumanMessage(content="test")],
            "search_manual": False,
            "search_forum": False,
            "search_query_manual": "",
            "search_query_forum": "",
            "manual_chunks": [],
            "forum_chunks": [],
            "scored_chunks": [],
            "retrieval_mode": "auto",
            "settings": {},
        }

        token_events = []
        async for custom_event in graph.astream(state, stream_mode="custom"):
            if custom_event.get("type") == "token":
                token_events.append(custom_event.get("token", ""))

        assert len(token_events) > 0, "Expected at least one token event from answer_node"
        assert "".join(token_events) == "Hello World!", (
            f"Expected 'Hello World!', got {''.join(token_events)!r}"
        )

    @patch("app.graph.graph.get_stream_writer")
    def test_retrieval_uses_search_query(self, mock_writer, mock_chroma):
        """Retrieval nodes should use search_query from state, not raw user message."""
        state: ChatState = {
            "messages": [HumanMessage("旷课了怎么办")],
            "search_manual": True,
            "search_forum": False,
            "search_query_manual": "旷课 处分 规定",
            "search_query_forum": "",
            "manual_chunks": [],
            "forum_chunks": [],
            "scored_chunks": [],
            "retrieval_mode": "auto",
            "settings": {},
        }

        result = manual_retrieval_node(state, mock_chroma)
        assert "manual_chunks" in result
        mock_chroma.retrieve.assert_called_once()
        called_query = mock_chroma.retrieve.call_args[0][1]
        assert called_query == "旷课 处分 规定"

    @pytest.mark.asyncio
    async def test_conversation_context_preserved(self, mock_chroma):
        """Graph should preserve prior conversation context (messages pass through)."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm, llm, mock_chroma, llm, llm)

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="First message")],
        })
        assert len(result["messages"]) == 2
        assert result["messages"][0].content == "First message"
        assert isinstance(result["messages"][1], AIMessage)

        result2 = await graph.ainvoke({
            "messages": [HumanMessage(content="First message"), HumanMessage(content="Second message")],
        })
        assert len(result2["messages"]) == 3
        assert result2["messages"][0].content == "First message"
        assert result2["messages"][1].content == "Second message"
        assert isinstance(result2["messages"][2], AIMessage)


class TestAnswerNode:
    """Tests for the answer_node and graph topology."""

    @pytest.mark.asyncio
    async def test_answer_node_returns_messages(self, mock_chroma):
        """answer_node should return an AIMessage in messages."""
        from app.graph.graph import answer_node, ChatState

        llm = MagicMock(spec=["astream"])
        llm.astream.return_value = _async_gen([AIMessageChunk(content="根据学生手册规定...")])

        state: ChatState = {
            "messages": [HumanMessage("旷课会怎样")],
            "search_manual": True,
            "search_forum": False,
            "search_query_manual": "旷课 处分",
            "search_query_forum": "",
            "manual_chunks": ["第四十一条 旷课处分规定..."],
            "forum_chunks": [],
            "scored_chunks": [],
            "retrieval_mode": "auto",
            "settings": {},
        }

        with patch("app.graph.graph.get_stream_writer") as mock_writer:
            result = await answer_node(state, llm)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

    @pytest.mark.asyncio
    async def test_graph_always_reaches_answer_node(self, mock_chroma):
        """With no retrieval needed, graph should still reach answer_node."""
        routing_llm = MockStreamingChatModel()
        routing_llm.streaming = False
        chat_llm = MagicMock(spec=["astream"])
        chat_llm.astream.return_value = _async_gen([AIMessageChunk(content="Hello!")])

        graph = compile_graph(routing_llm, routing_llm, mock_chroma, chat_llm, routing_llm)

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="天气怎么样")],
        })
        assert len(result["messages"]) >= 1


async def _async_gen(items):
    """Helper: async generator yielding items."""
    for item in items:
        yield item
