"""Chat service stubs."""

from typing import Any


class ChatService:
    """Chat service placeholder.

    Will implement chat logic using LangChain and LangGraph.
    """

    def __init__(self) -> None:
        """Initialize the chat service."""
        pass

    async def process_message(self, message: str) -> dict[str, Any]:
        """Process a chat message and return a response.

        Args:
            message: The user's chat message.

        Returns:
            A dict with the response content.
        """
        return {"response": "Placeholder response"}
