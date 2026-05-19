"""LangGraph state graph definition for the conversational agent.

Uses LangGraph's StateGraph to define a simple single-node graph
that invokes the LLM and returns the response.
"""

from typing import Annotated, Sequence, TypedDict

import operator

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph


class ChatState(TypedDict):
    """State of the chat conversation.

    Attributes:
        messages: Sequence of chat messages accumulated via operator.add.
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]


def call_model(state: ChatState, llm: BaseChatModel) -> dict:
    """Invoke the LLM with current messages and return the response.

    Args:
        state: Current chat state containing message history.
        llm: The language model to call.

    Returns:
        A dict with a 'messages' key containing the model's response.
    """
    response: AIMessage = llm.invoke(state["messages"])  # type: ignore[arg-type]
    return {"messages": [response]}


def compile_graph(llm: BaseChatModel) -> StateGraph:
    """Build and compile the LangGraph state graph.

    The graph has a single node 'call_model' that invokes the LLM.
    Flow: START -> call_model -> END.

    Args:
        llm: The language model instance to use in the graph node.

    Returns:
        A compiled StateGraph ready for invocation.
    """
    builder = StateGraph(ChatState)

    # Define the single processing node
    builder.add_node("call_model", lambda state: call_model(state, llm))

    # Define edges: START -> call_model -> END
    builder.add_edge(START, "call_model")
    builder.add_edge("call_model", END)

    return builder.compile()
