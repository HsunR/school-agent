"""Tests for LangGraph state graph definition.

Tests cover:
- Graph compilation
- Graph structure (nodes, edges)
- Graph invocation returns expected message structure
"""

from typing import TypedDict, Annotated, Sequence

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGenerationChunk, ChatGeneration, ChatResult
from langgraph.graph import START, END

from app.graph.graph import ChatState, compile_graph


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

    def test_graph_compiles(self):
        """compile_graph should return a compiled graph."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        assert graph is not None

    def test_graph_is_compiled(self):
        """The returned graph should be a CompiledStateGraph."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        assert "compile" not in dir(type(graph)) or hasattr(graph, "invoke")
        # Compiled graphs have invoke/ainvoke methods
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")


class TestGraphStructure:
    """Graph should have correct structure."""

    def test_has_call_model_node(self):
        """Graph should have a 'call_model' node."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        node_names = list(graph.nodes.keys())
        assert "call_model" in node_names, f"Expected 'call_model' in nodes, got {node_names}"

    def test_has_two_edges(self):
        """Graph should have exactly 2 edges (START->call_model, call_model->END)."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        g = graph.get_graph()
        edges = g.edges
        assert len(edges) == 2, f"Expected 2 edges, got {len(edges)}: {edges}"

    def test_start_to_call_model_edge(self):
        """There should be an edge from START to call_model."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        g = graph.get_graph()
        edges = g.edges
        edge_pairs = [(e.source, e.target) for e in edges]
        assert (
            "__start__",
            "call_model",
        ) in edge_pairs, f"Expected START->call_model edge, got {edge_pairs}"

    def test_call_model_to_end_edge(self):
        """There should be an edge from call_model to END."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        g = graph.get_graph()
        edges = g.edges
        edge_pairs = [(e.source, e.target) for e in edges]
        assert (
            "call_model",
            "__end__",
        ) in edge_pairs, f"Expected call_model->END edge, got {edge_pairs}"


class TestGraphInvocation:
    """Graph should correctly invoke the LLM and return messages."""

    def test_invoke_returns_messages(self):
        """Graph invoke should return a dict with 'messages' key."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        result = graph.invoke({"messages": [HumanMessage(content="test")]})
        assert isinstance(result, dict)
        assert "messages" in result

    def test_invoke_appends_response(self):
        """The response message should be appended to the messages list."""
        llm = MockStreamingChatModel()
        graph = compile_graph(llm)
        result = graph.invoke({"messages": [HumanMessage(content="test")]})
        assert len(result["messages"]) == 2  # input + response
        assert result["messages"][0].content == "test"
        assert result["messages"][1].content == "Hello World!"

    def test_ainvoke_returns_messages(self):
        """Async invoke should also return messages."""
        import asyncio

        llm = MockStreamingChatModel()
        graph = compile_graph(llm)

        async def run():
            result = await graph.ainvoke({"messages": [HumanMessage(content="test")]})
            return result

        result = asyncio.run(run())
        assert isinstance(result, dict)
        assert "messages" in result
        assert len(result["messages"]) == 2
