# KB Retrieval Options & Settings — Design Spec

**Date:** 2026-05-25
**Status:** Approved

## Overview

Add user-controllable knowledge base retrieval options and configurable RAG top-K settings to the chat page. Users can override the AI's automatic retrieval decision and adjust retrieval depth parameters directly from the chat input area.

## Frontend Changes

### Layout

KB selection radio buttons and settings gear button appear on a single row directly above the ChatInput textarea.

```
┌─────────────────────────────────────────────┐
│  · Auto  学生手册  学校贴吧  都检索  不检索  ⚙️  │  ← above input
│  ┌───────────────────────────────────┐      │
│  │  [输入框]                   [发送] │      │  ← ChatInput
│  └───────────────────────────────────┘      │
└─────────────────────────────────────────────┘
```

### ChatInput.tsx

- Add a row above the textarea with:
  - 5 radio-style chips/buttons: `Auto` | `学生手册` | `学校贴吧` | `都检索` | `不检索`
  - A gear icon button that opens a settings popover
- Settings popover contains 3 numeric inputs:
  - `RAG_TOP_K_MANUAL` (default 6, min 1, max 20)
  - `RAG_TOP_K_FORUM` (default 6, min 1, max 20)
  - `RAG_TOP_K_SCORED` (default 3, min 1, max 10)
- Selection and settings values are managed via props from parent

### useChat.ts

- Add two new pieces of client state:
  - `retrievalMode: "auto" | "manual" | "forum" | "both" | "none"` (default `"auto"`)
  - `settings: { top_k_manual: number, top_k_forum: number, top_k_scored: number }` (defaults: 6, 6, 3)
- Persist both to `localStorage` on change, restore on init
- Include both in the `fetch("/api/chat")` POST body

### page.tsx

- Wire KB state and settings state from `useChat` to `ChatInput`
- No additional structural changes needed

## Backend Changes

### schemas/chat.py

```python
class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    retrieval_mode: Literal["auto", "manual", "forum", "both", "none"] = "auto"
    settings: dict[str, int] | None = None  # optional override keys: top_k_manual, top_k_forum, top_k_scored
```

### graph/graph.py

- `ChatState` TypedDict: add `retrieval_mode` and `settings` fields
- `routing_node`:
  - `"auto"` — use current LLM-based routing (unchanged, generates search queries via LLM)
  - `"manual"` — skip LLM; set `search_manual=true, search_forum=false`; use `optimized_query` as `search_query_manual`
  - `"forum"` — skip LLM; set `search_manual=false, search_forum=true`; use `optimized_query` as `search_query_forum`
  - `"both"` — skip LLM; set `search_manual=true, search_forum=true`; use `optimized_query` for both queries
  - `"none"` — skip LLM; set both to false; no queries needed
- `answer_node`: read `top_k_scored` from `settings` (fallback to compiled default)

### chroma_manager.py

- `retrieve()` method: add optional `top_k: int | None = None` parameter
  - When provided, override `self.top_k_manual` / `self.top_k_forum`
  - When `None`, use instance defaults as before

### chat_service.py

- Pass `retrieval_mode` and `settings` from request into the initial graph state
- Extract `top_k_manual` and `top_k_forum` from `settings` (or fall back to `settings.rag_top_k_manual`/`rag_top_k_forum`) and pass to ChromaManager for retrieval calls

### BFF route (frontend/src/app/api/chat/route.ts)

- No changes needed — already proxies full request body

## Data Flow

```
User clicks KB radio → useChat state updates → stored in localStorage
User opens settings → changes top-k values → useChat state updates → stored in localStorage
User sends message → POST /api/chat { messages, retrieval_mode, settings }
  → BFF proxy → backend ChatRequest
  → ChatService builds initial state with retrieval_mode + settings
  → routing_node checks retrieval_mode:
       "auto" → LLM decides (current behavior)
       other  → force search_manual/search_forum flags
  → retrieval nodes use settings.top_k_manual / top_k_forum
  → scoring + answer node use settings.top_k_scored
  → SSE stream as usual
```

## Error Handling

- Invalid `retrieval_mode` values → backend treats as `"auto"` (fallback)
- Missing/invalid `settings` keys → backend uses defaults from `Settings` class
- No new error types needed — existing SSE error stream handles failures

## Testing

### Frontend
- KB radio selection renders and updates state
- Settings popover opens/closes and persists values
- `sendMessage` payload includes `retrieval_mode` and `settings`

### Backend
- `routing_node` correctly forces KB selection for each mode
- `ChromaManager.retrieve()` uses override `top_k` when provided
- Defaults and fallbacks work with missing/partial settings
