"""Chat API router stubs."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("")
async def chat_root():
    """Chat endpoint stub.

    Returns a placeholder response for chat queries.
    """
    return {"message": "Chat API placeholder"}
