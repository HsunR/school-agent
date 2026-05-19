"""Chat service test stubs."""

import pytest

from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_process_message() -> None:
    """Test chat service processes a message and returns placeholder response."""
    service = ChatService()
    result = await service.process_message("Hello")
    assert result == {"response": "Placeholder response"}
