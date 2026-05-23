"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

# Load .env into os.environ BEFORE any other imports
# so LangSmith SDK can detect LANGSMITH_TRACING etc.
from dotenv import load_dotenv

load_dotenv()

# Apply WindowsSelectorEventLoopPolicy on Windows for SSE compatibility
if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.core.settings import get_settings
from app.rag.chroma_manager import ChromaManager, ALL_COLLECTIONS
from app.rag.embeddings import EmbeddingClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm up ChromaDB collections. Shutdown: no-op."""
    settings = get_settings()
    embedding = EmbeddingClient(settings)
    chroma = ChromaManager(settings, embedding)
    chroma.warmup()
    yield


app = FastAPI(title="School Agent Backend", version="0.1.0", lifespan=lifespan)

# CORS middleware — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
