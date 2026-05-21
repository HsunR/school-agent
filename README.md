# School Agent

AI-powered educational assistant with RAG knowledge base. Built with FastAPI + LangGraph + ChromaDB (backend) and Next.js 16 (frontend).

## Architecture

### LangGraph Pipeline (Backend)

```
                                    User Question
                                         │
                                         ▼
              ┌──────────────────────────────────────┐
              │           routing_node                │
              │  Classifies question → needs search?  │
              │  Emits: status event + search flags   │
              └────────────┬─────────────────────────┘
                           │ should_retrieve
                           ▼
              ┌──────────────────────┐
              │  manual_retrieval    │  (if search_manual=true)
              │  ChromaDB: 学生手册  │
              │  Emits: retrieval    │
              └──────────┬───────────┘
                         │ should_retrieve
                         ▼
              ┌──────────────────────┐
              │  forum_retrieval     │  (if search_forum=true)
              │  ChromaDB: 学校贴吧  │
              │  Emits: retrieval    │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │     scoring_node     │
              │  Per-chunk LLM       │
              │  Score (0-100) +     │
              │  compress (crop      │
              │  irrelevant text)    │
              │  Emits: scoring      │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │     answer_node      │
              │  LLM generates final │
              │  answer with context │
              │  Emits: token        │
              └──────────┬───────────┘
                         │
                         ▼
                    Final Answer
```

### SSE Event Stream

Each graph node emits typed events via SSE (POST-based, not EventSource):

| Event | Source | Content |
|-------|--------|---------|
| `status` | routing_node | Decision: which knowledge bases to search |
| `retrieval` | retrieval nodes | Raw chunks from ChromaDB |
| `scoring` | scoring_node | Per-chunk relevance score + compressed text |
| `token` | answer_node | Streaming token of final answer |

### 4-Tier LLM Configuration

| Tier | Model Config | Purpose |
|------|-------------|---------|
| Chat | `LLM_CHAT_*` | Final answer generation (streaming) |
| Routing | `LLM_ROUTING_*` | Question classification (non-streaming) |
| Scoring | `LLM_SCORING_*` | Chunk relevance scoring (non-streaming, 15s timeout) |
| Embedding | `LLM_EMBEDDING_*` | Vector embeddings for ChromaDB |

## Project Structure

```
school-agent/
├── frontend/                    # Next.js 16 + TypeScript + Tailwind v4
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Main chat UI
│       │   ├── admin/           # Knowledge base management page
│       │   └── api/chat/        # BFF proxy to backend
│       ├── components/
│       │   ├── ChatInput.tsx    # Message input with loading state
│       │   ├── ChatMessage.tsx  # Renders user/assistant/status/retrieval/scoring bubbles
│       │   ├── RetrievalCard.tsx# Chunk list with score display + sorting animation
│       │   ├── DetailModal.tsx  # Full content modal (tab: compressed / original)
│       │   └── MarkdownRenderer.tsx
│       ├── hooks/useChat.ts     # SSE streaming consumer (fetch + ReadableStream)
│       └── types/chat.ts        # ChatMessage, SSEPayload, RetrievalPreview
├── backend/
│   └── app/
│       ├── main.py              # FastAPI entry, CORS, router registration
│       ├── api/
│       │   ├── chat.py          # POST /api/chat SSE endpoint
│       │   └── admin.py         # KB admin: upload, preview, clear, stats
│       ├── core/settings.py     # pydantic-settings (4-tier LLM config)
│       ├── schemas/
│       │   ├── chat.py          # ChatRequest, ChatMessage
│       │   └── admin.py         # Admin request/response models
│       ├── services/
│       │   └── chat_service.py  # ChatService: LLM instances → compile_graph
│       ├── graph/graph.py       # LangGraph StateGraph (5 nodes)
│       └── rag/
│           ├── chroma_manager.py # ChromaDB wrapper (2 collections)
│           └── embeddings.py    # OpenAI-compatible embedding client
└── docs/
    ├── api.md                   # Full API contract
    └── superpowers/             # Design specs & implementation plans
```

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements.txt
# Edit .env with your API keys
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:3000

## Environment Variables

All LLMs share the same pattern: `LLM_{TIER}_{PROPERTY}`.

| Variable | Required | Default |
|----------|----------|---------|
| `LLM_CHAT_API_KEY` | Yes | — |
| `LLM_ROUTING_API_KEY` | Yes | — |
| `LLM_SCORING_API_KEY` | Yes | — |
| `LLM_EMBEDDING_API_KEY` | Yes | — |
| `LLM_CHAT_MODEL` | No | `deepseek-chat` |
| `LLM_ROUTING_MODEL` | No | `deepseek-chat` |
| `LLM_SCORING_MODEL` | No | `deepseek-chat` |
| `LLM_EMBEDDING_MODEL` | No | `text-embedding-ada-002` |
| `LLM_CHAT_BASE_URL` | No | `https://api.deepseek.com/v1` |
| `LLM_ROUTING_BASE_URL` | No | `https://api.deepseek.com/v1` |
| `LLM_SCORING_BASE_URL` | No | `https://api.deepseek.com/v1` |
| `LLM_EMBEDDING_BASE_URL` | No | `https://api.deepseek.com/v1` |
| `CHROMA_PERSIST_DIR` | No | `./chroma_db` |
| `RAG_TOP_K_MANUAL` | No | `5` |
| `RAG_TOP_K_FORUM` | No | `5` |

## Test

```bash
cd backend && pytest tests/ -v    # 140+ tests
cd frontend && pnpm test          # 90+ tests
```
