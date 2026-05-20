# BACKEND KNOWLEDGE BASE

**Generated:** 2026-05-20

## OVERVIEW
Python 3.11+ FastAPI service with LangGraph RAG, ChromaDB vector store, and SSE streaming on port 8000.

## STRUCTURE
```
backend/
├── app/
│   ├── main.py          # FastAPI entry point, registers routers, Windows SSE policy
│   ├── api/
│   │   ├── chat.py      # POST /api/chat SSE streaming endpoint
│   │   └── admin.py     # KB admin: upload, preview, clear, stats
│   ├── core/
│   │   └── settings.py  # pydantic-settings: 4-tier LLM config (chat/routing/embedding/legacy)
│   ├── schemas/
│   │   ├── chat.py      # ChatRequest, ChatMessage Pydantic models
│   │   └── admin.py     # Admin request/response models
│   ├── services/
│   │   └── chat_service.py  # ChatService: LLM orchestration, LangGraph invocation
│   ├── graph/
│   │   └── graph.py     # StateGraph: routing + retrieval state machine, ChatState TypedDict
│   └── rag/
│       ├── chroma_manager.py  # ChromaManager: 2 collections (student_manual, school_forum)
│       └── embeddings.py      # OpenAI-compatible embedding client
├── tests/               # 13 test files, pytest + pytest-asyncio (asyncio_mode=auto)
│   ├── conftest.py
│   ├── test_chat_api.py, test_chat_service.py, test_chat_service_rag.py
│   ├── test_admin_api.py, test_admin_schemas.py
│   ├── test_chroma_manager.py, test_embeddings.py
│   ├── test_graph.py, test_rag_graph.py
│   ├── test_schemas.py, test_settings.py
├── requirements.txt     # fastapi>=0.115, langchain-core, langchain-openai, langgraph, chromadb, pydantic v2
├── pyproject.toml       # empty deps (real deps in requirements.txt)
├── .env                 # DEEPSEEK_API_KEY + LLM_* config
└── chroma_db/           # ChromaDB persistent storage (gitignored)
```

## WHERE TO LOOK
| File | What it does |
|------|-------------|
| `app/main.py` | FastAPI app creation, CORS, router registration, Windows SSE event loop fix |
| `app/api/chat.py` | POST-based SSE. AsyncGenerator yields `data: {json}\n\n`, error in-stream |
| `app/api/admin.py` | 4 KB endpoints: POST upload, GET data, DELETE clear, GET stats |
| `app/core/settings.py` | pydantic-settings: 4 separate model configs + legacy fallback |
| `app/services/chat_service.py` | Orchestrates LangGraph, streams final answer via ChatOpenAI.astream() |
| `app/graph/graph.py` | StateGraph with routing + retrieval nodes, ChatState TypedDict |
| `app/rag/chroma_manager.py` | Lazy singleton, 2 collections, cosine similarity search |
| `app/rag/embeddings.py` | Async/sync embedding via OpenAI-compatible API |
| `app/schemas/chat.py` | ChatRequest (messages history), ChatMessage (role/content) |
| `app/schemas/admin.py` | UploadResponse, DataResponse, StatsResponse |

## CONVENTIONS (backend-specific)
- **Lazy singletons**: `global` vars in API routers for ChatService, ChromaManager. Initialized on first request, not import time
- **SSE format**: `data: {"token":"...","done":false}\n\n` and `data: {"error":"...","done":true}\n\n`. Never HTTP 500
- **ChromaDB**: Persistent client at `chroma_db/`, two collections with different embedding dimensions
- **Testing**: `asyncio_mode=auto` in pytest.ini/pyproject. All async tests work without event loop decorators
- **No formatter/linter**: No ruff, black, mypy config. IDE defaults only
- **.env**: Must be in `backend/` directory, loaded via python-dotenv in settings.py
- **pyproject.toml**: Placeholder only. Real dependencies in requirements.txt

## ANTI-PATTERNS
- `except: pass` NEVER allowed (bare except or empty catch)
- `# noqa: ANN401` Permitted only for FastAPI DI parameter annotations
- `global` Permitted only for lazy singleton pattern in API routers
- `# pragma: no cover` Permitted only on unreachable `yield` in mock generators
- Hardcoding ChromaDB paths. Use settings or relative to backend/ root
- Mixing sync/async ChromaDB calls without thread pool. ChromaManager sync methods should run in thread executor
