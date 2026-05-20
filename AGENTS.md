# PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-20
**Commit:** c0b9798
**Branch:** master

## OVERVIEW
AI-powered educational assistant (FastAPI + Next.js) with LangGraph-based RAG, SSE streaming, and ChromaDB vector store.

## STRUCTURE
```
school-agent/
├── backend/     # Python FastAPI service (port 8000) — see backend/AGENTS.md
├── frontend/    # Next.js 16 app (port 3000, proxies /api/*) — see frontend/AGENTS.md
└── docs/        # API contract documentation
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Chat SSE endpoint | `backend/app/api/chat.py` | POST-based SSE streaming |
| RAG knowledge base | `backend/app/api/admin.py` | Upload/preview/clear/stats |
| LLM config | `backend/app/core/settings.py` | 4-tier LLM config (chat/routing/embedding + legacy) |
| LangGraph graph | `backend/app/graph/graph.py` | Routing + retrieval state machine |
| ChromaDB wrapper | `backend/app/rag/chroma_manager.py` | Two collections: student_manual, school_forum |
| Chat UI | `frontend/src/app/page.tsx` | Main chat interface |
| SSE streaming hook | `frontend/src/hooks/useChat.ts` | Uses fetch() + ReadableStream |
| API contract | `docs/api.md` | Full endpoint reference |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `app` | FastAPI app | `backend/app/main.py` | Backend entry point, register routers |
| `chat_endpoint` | Route | `backend/app/api/chat.py` | SSE chat POST |
| `admin_router` | Route set | `backend/app/api/admin.py` | KB CRUD: upload, data, clear, stats |
| `ChatService` | Service | `backend/app/services/chat_service.py` | LLM orchestration |
| `ChatState` | TypedDict | `backend/app/graph/graph.py` | LangGraph state schema |
| `ChromaManager` | Class | `backend/app/rag/chroma_manager.py` | Vector store wrapper |
| `Settings` | Settings | `backend/app/core/settings.py` | pydantic-settings config |
| `useChat` | Hook | `frontend/src/hooks/useChat.ts` | SSE stream consumer, client state |
| `ChatInput`/`ChatMessage` | Components | `frontend/src/components/` | UI components |

## CONVENTIONS
- **Mixed monorepo**: Frontend uses pnpm workspace (`frontend/` only); backend uses pip independently
- **SSE**: POST-based (not GET/EventSource). Frontend uses `fetch()` + `ReadableStream`
- **LangGraph**: Only handles routing + retrieval; final answer streams directly via `ChatOpenAI.astream()`
- **Lazy singletons**: Services initialized lazily at first request (avoids import-time env dependency)
- **"use client"**: Required on all interactive Next.js components (App Router)
- **@/ alias**: Maps to `./src/` in both TypeScript and Vitest
- **Tailwind v4**: CSS-based config (no `tailwind.config.js`)
- **No Prettier / no Python formatter**: Formatting relies on IDE defaults
- **No CI**: No CI pipeline configured — tests run manually

## ANTI-PATTERNS (THIS PROJECT)
- `as any` / `@ts-ignore` / `@ts-expect-error` — NEVER allowed
- `except: pass` — NEVER allowed (bare except or empty catch)
- `# noqa: ANN401` — Permitted only for FastAPI DI parameter annotations
- `# pragma: no cover` — Permitted only on unreachable `yield` in mock generators
- `global` — Permitted only for lazy singleton pattern in API routers

## UNIQUE STYLES
- Section comment markers: `# ── ... ──` (Python), `/* ── ... ── */` (TypeScript)
- Chat state: Fully client-side (stateless API — full history in every request)
- LLM config: 3 separate tiers (chat, routing, embedding) + legacy backward-compat fallback
- SSE error handling: Errors delivered as `{"error":"...", "done":true}` in-stream (not HTTP errors)

## COMMANDS
```bash
# Backend (terminal 1)
cd backend && pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && pytest tests/ -v

# Frontend (terminal 2)
cd frontend && pnpm install
cd frontend && pnpm dev       # runs: next dev --webpack
cd frontend && pnpm test      # runs: vitest run

# Root (orchestrates frontend only)
pnpm dev    # starts frontend (backend excluded from workspace)
pnpm build  # builds frontend only
pnpm test   # runs vitest in frontend only
```

## NOTES
- `.env` lives in `backend/` — run uvicorn from `backend/` directory
- Next.js 16 with `--webpack`: explicitly opts out of Turbopack default
- Windows: SSE may need `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`
- No Docker setup — runs as bare processes
