# KB Retrieval Options & Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-controllable KB retrieval modes (manual/forum/both/none/auto) and configurable RAG top-K settings to the chat page.

**Architecture:** KB selection and settings values are passed from frontend state through the BFF proxy to the backend `ChatRequest`. The `routing_node` in the LangGraph checks `retrieval_mode` before the LLM call — non-auto modes skip the LLM and force search flags directly. Top-K values flow from request settings into `ChromaManager.retrieve()` calls.

**Tech Stack:** Python 3.11+ / FastAPI / LangGraph / ChromaDB / Next.js 16 / React 19 / TypeScript 5

---

### Task 1: Backend — Update ChatRequest and ChatState schemas

**Files:**
- Modify: `backend/app/schemas/chat.py:15-18`
- Modify: `backend/app/graph/graph.py:174-186`

- [ ] **Step 1: Add fields to ChatRequest**

```python
# backend/app/schemas/chat.py
from typing import Literal, Optional

class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    retrieval_mode: Literal["auto", "manual", "forum", "both", "none"] = "auto"
    settings: Optional[dict[str, int]] = None  # keys: top_k_manual, top_k_forum, top_k_scored
```

- [ ] **Step 2: Run existing tests to confirm no regression**

Run: `cd backend && pytest tests/test_schemas.py -v`
Expected: all tests pass

- [ ] **Step 3: Add fields to ChatState TypedDict**

```python
# backend/app/graph/graph.py
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    search_manual: bool
    search_forum: bool
    search_query_manual: str
    search_query_forum: str
    manual_chunks: list[str]
    forum_chunks: list[str]
    scored_chunks: list[dict]
    optimized_query: str
    compressed_context: str
    retrieval_mode: str  # "auto" | "manual" | "forum" | "both" | "none"
    settings: dict  # {top_k_manual: int, top_k_forum: int, top_k_scored: int}
```

- [ ] **Step 4: Update all test fixtures that construct ChatState to include the new fields**

In `tests/test_graph.py`, add `retrieval_mode` and `settings` to every `ChatState(...)` dict:

```python
state: ChatState = {
    "messages": [HumanMessage(content="test")],
    "search_manual": False,
    "search_forum": False,
    "search_query_manual": "",
    "search_query_forum": "",
    "manual_chunks": [],
    "forum_chunks": [],
    "scored_chunks": [],
    # New required fields
    "retrieval_mode": "auto",
    "settings": {},
}
```

This affects: `test_astream_custom_yields_token_events`, `test_retrieval_uses_search_query`, `test_answer_node_returns_messages`.

- [ ] **Step 5: Run graph tests to verify**

Run: `cd backend && pytest tests/test_graph.py -v`
Expected: all pass (after fixture updates)

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/graph/graph.py backend/tests/test_graph.py
git commit -m "feat: add retrieval_mode and settings to ChatRequest and ChatState"
```

---

### Task 2: Backend — Add optional top_k to ChromaManager.retrieve()

**Files:**
- Modify: `backend/app/rag/chroma_manager.py:137-155`

- [ ] **Step 1: Update retrieve() signature and logic**

```python
# backend/app/rag/chroma_manager.py
def retrieve(self, category: str, query: str, top_k: int | None = None) -> list[str]:
    collection = self._collection(category)
    query_embedding = self.embedding_client.embed([query])[0]
    if top_k is not None:
        n_results = top_k
    else:
        n_results = self.top_k_manual if category == "student_manual" else self.top_k_forum
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )
    documents = results.get("documents", [[]])[0] or []
    return list(documents)
```

- [ ] **Step 2: Run chroma tests**

Run: `cd backend && pytest tests/test_chroma_manager.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/rag/chroma_manager.py
git commit -m "feat: add optional top_k override to ChromaManager.retrieve()"
```

---

### Task 3: Backend — Modify routing_node to support retrieval_mode override

**Files:**
- Modify: `backend/app/graph/graph.py:292-338`

- [ ] **Step 1: Update routing_node to check retrieval_mode**

```python
def routing_node(state: ChatState, llm: BaseChatModel) -> dict:
    writer = get_stream_writer()
    retrieval_mode = state.get("retrieval_mode", "auto")

    # Non-auto modes: skip LLM, force flags based on user selection
    if retrieval_mode != "auto":
        search_manual = retrieval_mode in ("manual", "both")
        search_forum = retrieval_mode in ("forum", "both")
        raw = state.get("optimized_query", "")
        search_query = raw.strip() or (state["messages"][-1].content if state["messages"] else "")
        writer({
            "type": "status",
            "node": "routing",
            "label": "正在分析你的问题...",
            "decision": {
                "search_manual": search_manual,
                "search_forum": search_forum,
            },
        })
        logger.info(
            "Routing (user override '%s'): manual=%s, forum=%s",
            retrieval_mode, search_manual, search_forum,
        )
        return {
            "search_manual": search_manual,
            "search_forum": search_forum,
            "search_query_manual": search_query if search_manual else "",
            "search_query_forum": search_query if search_forum else "",
        }

    # Auto mode: existing LLM-based routing (unchanged)
    raw = state.get("optimized_query", "")
    last_msg = raw.strip() or (state["messages"][-1].content if state["messages"] else "")
    # ... rest of existing LLM routing code ...
```

Note: Keep the existing LLM routing code (lines ~297-338) unchanged inside the `else` block.

- [ ] **Step 2: Run graph tests**

Run: `cd backend && pytest tests/test_graph.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/graph/graph.py
git commit -m "feat: routing_node respects retrieval_mode override"
```

---

### Task 4: Backend — Wire settings through graph nodes

**Files:**
- Modify: `backend/app/graph/graph.py:341-378` (retrieval nodes)
- Modify: `backend/app/graph/graph.py:451-513` (answer_node)

- [ ] **Step 1: Pass top_k from state.settings to retrieval nodes**

```python
def manual_retrieval_node(state: ChatState, chroma: ChromaManager) -> dict:
    writer = get_stream_writer()
    if not state.get("search_manual"):
        return {"manual_chunks": []}
    query = state.get("search_query_manual") or ""
    if not query:
        return {"manual_chunks": [], "search_manual": False}
    settings = state.get("settings", {})
    top_k = settings.get("top_k_manual") if settings else None
    chunks = chroma.retrieve(COLLECTION_MANUAL, query, top_k=top_k)
    # ... rest unchanged ...
```

```python
def forum_retrieval_node(state: ChatState, chroma: ChromaManager) -> dict:
    writer = get_stream_writer()
    if not state.get("search_forum"):
        return {"forum_chunks": []}
    query = state.get("search_query_forum") or ""
    if not query:
        return {"forum_chunks": [], "search_forum": False}
    settings = state.get("settings", {})
    top_k = settings.get("top_k_forum") if settings else None
    chunks = chroma.retrieve(COLLECTION_FORUM, query, top_k=top_k)
    # ... rest unchanged ...
```

- [ ] **Step 2: Update answer_node signature and usage of top_k_scored**

Modify `compile_graph()` to remove the `top_k_scored` parameter — instead read it from state:

```python
async def answer_node(state: ChatState, chat_llm: BaseChatModel) -> dict:
    writer = get_stream_writer()
    settings = state.get("settings", {})
    top_k_scored = settings.get("top_k_scored", 3) if settings else 3
    scored = state.get("scored_chunks", [])
    # ... rest uses top_k_scored variable instead of parameter ...
```

Update `compile_graph()`:

```python
def compile_graph(
    intent_llm: BaseChatModel,
    routing_llm: BaseChatModel,
    chroma: ChromaManager,
    chat_llm: BaseChatModel,
    scoring_llm: BaseChatModel,
    top_k_scored: int = 3,  # keep for backward compat, but answer_node reads from state
) -> StateGraph:
    # ... builder setup ...

    async def _answer_node(state):
        return await answer_node(state, chat_llm)
```

The `top_k_scored` parameter in `compile_graph()` stays as a backward-compatible default but `answer_node` now reads from state first. The `top_k_scored` param in `compile_graph` is kept for existing test compatibility.

- [ ] **Step 3: Run graph tests**

Run: `cd backend && pytest tests/test_graph.py -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/graph/graph.py
git commit -m "feat: pass top_k settings through graph state to retrieval and answer nodes"
```

---

### Task 5: Backend — Update ChatService to pass request fields into graph state

**Files:**
- Modify: `backend/app/services/chat_service.py:101-131`

- [ ] **Step 1: Update stream_chat to inject retrieval_mode and settings**

```python
async def stream_chat(
    self,
    messages: list[ChatMessage],
    retrieval_mode: str = "auto",
    settings: dict | None = None,
) -> AsyncGenerator[str, Any]:
    langchain_messages = self._to_langchain(messages)
    resolved_settings = settings or {}

    initial_state = {
        "messages": langchain_messages,
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
        "optimized_query": "",
        "compressed_context": "",
        "retrieval_mode": retrieval_mode,
        "settings": resolved_settings,
    }
    # ... rest unchanged ...
```

- [ ] **Step 2: Update chat API endpoint to pass new request fields**

```python
# backend/app/api/chat.py
@router.post("")
async def chat_endpoint(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        event_generator(request.messages, request.retrieval_mode, request.settings),
        media_type="text/event-stream",
    )

async def event_generator(
    messages: list,
    retrieval_mode: str = "auto",
    settings: dict | None = None,
) -> AsyncGenerator[str, None]:
    global chat_service
    if chat_service is None:
        chat_service = ChatService(get_settings())
    try:
        async for event_str in chat_service.stream_chat(messages, retrieval_mode, settings):
            yield f"data: {event_str}\n\n"
    except Exception:
        logger.exception("Error during SSE stream")
        yield f"data: {json.dumps({'type': 'error', 'error': 'Internal server error', 'done': True})}\n\n"
```

- [ ] **Step 3: Update existing API test mocks to accept extra args**

In `backend/tests/test_chat_api.py`, update all `lambda _messages:` to `lambda *_:` so they accept the 3-arg `stream_chat(messages, retrieval_mode, settings)` call:

```python
# Replace every:
lambda _messages: _event_gen(events)
# With:
lambda *_: _event_gen(events)
```

Affected lines: 46, 64, 85, 111, 149, 232.

- [ ] **Step 4: Run chat API tests**

Run: `cd backend && pytest tests/test_chat_api.py -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/chat_service.py backend/app/api/chat.py
git commit -m "feat: pass retrieval_mode and settings from request into graph state"
```

---

### Task 6: Backend — Update existing tests + add new tests

**Files:**
- Modify: `backend/tests/test_chat_api.py`
- Modify: `backend/tests/test_chat_service.py`
- Modify: `backend/tests/test_rag_graph.py`

- [ ] **Step 1: Add schema test for new ChatRequest fields**

In `backend/tests/test_schemas.py`, add to `TestChatRequest`:

```python
def test_request_with_retrieval_mode(self):
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="Hello")],
        retrieval_mode="manual",
        settings={"top_k_manual": 6, "top_k_forum": 6, "top_k_scored": 3},
    )
    assert req.retrieval_mode == "manual"
    assert req.settings["top_k_manual"] == 6

def test_request_default_retrieval_mode(self):
    req = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])
    assert req.retrieval_mode == "auto"
    assert req.settings is None

def test_request_invalid_retrieval_mode_rejected(self):
    with pytest.raises(ValidationError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            retrieval_mode="invalid",
        )
```

- [ ] **Step 2: Add graph test for retrieval_mode override**

In `backend/tests/test_graph.py`, add to `TestGraphInvocation` or a new class:

```python
@pytest.mark.asyncio
async def test_routing_node_respects_manual_mode(self, mock_chroma):
    routing_llm = MockStreamingChatModel()
    routing_llm.streaming = False
    chat_llm = MockStreamingChatModel()
    graph = compile_graph(routing_llm, routing_llm, mock_chroma, chat_llm, routing_llm)

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Hello")],
        "retrieval_mode": "manual",
        "settings": {},
    })
    assert result.get("search_manual") is True
    assert result.get("search_forum") is False

@pytest.mark.asyncio
async def test_routing_node_respects_forum_mode(self, mock_chroma):
    routing_llm = MockStreamingChatModel()
    routing_llm.streaming = False
    chat_llm = MockStreamingChatModel()
    graph = compile_graph(routing_llm, routing_llm, mock_chroma, chat_llm, routing_llm)

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Hello")],
        "retrieval_mode": "forum",
        "settings": {},
    })
    assert result.get("search_manual") is False
    assert result.get("search_forum") is True

@pytest.mark.asyncio
async def test_routing_node_respects_both_mode(self, mock_chroma):
    routing_llm = MockStreamingChatModel()
    routing_llm.streaming = False
    chat_llm = MockStreamingChatModel()
    graph = compile_graph(routing_llm, routing_llm, mock_chroma, chat_llm, routing_llm)

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Hello")],
        "retrieval_mode": "both",
        "settings": {},
    })
    assert result.get("search_manual") is True
    assert result.get("search_forum") is True

@pytest.mark.asyncio
async def test_routing_node_respects_none_mode(self, mock_chroma):
    routing_llm = MockStreamingChatModel()
    routing_llm.streaming = False
    chat_llm = MockStreamingChatModel()
    graph = compile_graph(routing_llm, routing_llm, mock_chroma, chat_llm, routing_llm)

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Hello")],
        "retrieval_mode": "none",
        "settings": {},
    })
    assert result.get("search_manual") is False
    assert result.get("search_forum") is False
```

- [ ] **Step 3: Add API test for sending retrieval_mode in request body**

In `backend/tests/test_chat_api.py`:

```python
@pytest.mark.asyncio
async def test_sse_with_retrieval_mode(client: AsyncClient) -> None:
    events = [
        {"type": "token", "token": "Hello"},
        {"type": "token", "token": "", "done": True},
    ]
    mock = _mock_service(lambda _messages: _event_gen(events))
    with patch("app.api.chat.chat_service", mock):
        response = await client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "retrieval_mode": "both",
                "settings": {"top_k_manual": 6, "top_k_forum": 6, "top_k_scored": 3},
            },
        )
    assert response.status_code == 200
    # Verify mock received the messages — the mock lambda ignores extra params
```

- [ ] **Step 4: Run all backend tests**

Run: `cd backend && pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_schemas.py backend/tests/test_graph.py backend/tests/test_chat_api.py
git commit -m "test: add tests for retrieval_mode and settings overrides"
```

---

### Task 7: Frontend — Update types and useChat hook

**Files:**
- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Add retrieval mode type**

In `frontend/src/types/chat.ts`:

```typescript
export type RetrievalMode = "auto" | "manual" | "forum" | "both" | "none";

export interface RetrievalSettings {
  top_k_manual: number;
  top_k_forum: number;
  top_k_scored: number;
}
```

- [ ] **Step 2: Add state + localStorage persistence to useChat**

In `frontend/src/hooks/useChat.ts`:

```typescript
import type { ChatMessage, SSEPayload, RetrievalMode, RetrievalSettings } from "@/types/chat";

const STORAGE_KEY_MODE = "retrieval_mode";
const STORAGE_KEY_SETTINGS = "retrieval_settings";

const DEFAULT_SETTINGS: RetrievalSettings = {
  top_k_manual: 6,
  top_k_forum: 6,
  top_k_scored: 3,
};

function loadStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(
    () => loadStorage<RetrievalMode>(STORAGE_KEY_MODE, "auto"),
  );
  const [settings, setSettings] = useState<RetrievalSettings>(
    () => loadStorage<RetrievalSettings>(STORAGE_KEY_SETTINGS, DEFAULT_SETTINGS),
  );

  const setRetrievalModeAndPersist = useCallback((mode: RetrievalMode) => {
    setRetrievalMode(mode);
    try { localStorage.setItem(STORAGE_KEY_MODE, JSON.stringify(mode)); } catch {}
  }, []);

  const setSettingsAndPersist = useCallback((s: RetrievalSettings) => {
    setSettings(s);
    try { localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(s)); } catch {}
  }, []);

  // In sendMessage, include retrievalMode and settings in the fetch body:
  const body = JSON.stringify({
    messages: [...historyMessages, userMessage],
    retrieval_mode: retrievalModeRef.current,
    settings: settingsRef.current,
  });
```

Add refs:
```typescript
const retrievalModeRef = useRef(retrievalMode);
retrievalModeRef.current = retrievalMode;
const settingsRef = useRef(settings);
settingsRef.current = settings;
```

Update the return value:
```typescript
return {
  messages, isLoading, error,
  sendMessage, clearMessages, clearError,
  retrievalMode, setRetrievalMode: setRetrievalModeAndPersist,
  settings, setSettings: setSettingsAndPersist,
};
```

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: all tests pass (existing useChat tests still work)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/chat.ts frontend/src/hooks/useChat.ts
git commit -m "feat: add retrievalMode and settings state to useChat with localStorage"
```

---

### Task 8: Frontend — Update ChatInput with KB radio buttons and settings popover

**Files:**
- Modify: `frontend/src/components/ChatInput.tsx`

- [ ] **Step 1: Rewrite ChatInput with KB selector + settings gear**

```typescript
"use client";

import { useState, useRef, useCallback, useEffect, KeyboardEvent, ChangeEvent } from "react";
import type { RetrievalMode, RetrievalSettings } from "@/types/chat";

interface ChatInputProps {
  onSend: (content: string) => void;
  isLoading: boolean;
  retrievalMode: RetrievalMode;
  onRetrievalModeChange: (mode: RetrievalMode) => void;
  settings: RetrievalSettings;
  onSettingsChange: (settings: RetrievalSettings) => void;
}

const RETRIEVAL_OPTIONS: { value: RetrievalMode; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "manual", label: "学生手册" },
  { value: "forum", label: "学校贴吧" },
  { value: "both", label: "都检索" },
  { value: "none", label: "不检索" },
];

export default function ChatInput({
  onSend, isLoading,
  retrievalMode, onRetrievalModeChange,
  settings, onSettingsChange,
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);
  const showSettingsRef = useRef(showSettings);
  showSettingsRef.current = showSettings;

  useEffect(() => {
    if (!showSettings) return;
    const handleClick = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showSettings]);

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value);
      adjustHeight();
    },
    [adjustHeight],
  );

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const canSend = text.trim().length > 0 && !isLoading;

  return (
    <div className="mx-auto w-full max-w-[700px] px-4 pb-4">
      {/* KB selector row */}
      <div className="mb-2 flex items-center justify-between rounded-xl bg-bg-card px-4 py-2">
        <div className="flex items-center gap-1">
          {RETRIEVAL_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onRetrievalModeChange(opt.value)}
              disabled={isLoading}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${
                retrievalMode === opt.value
                  ? "bg-brand text-white"
                  : "bg-transparent text-text-tertiary hover:bg-bg-soft hover:text-foreground"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {/* Gear button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className="rounded-lg p-1.5 text-text-tertiary transition-colors hover:bg-bg-soft hover:text-foreground"
            aria-label="Settings"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path fillRule="evenodd" d="M7.84 1.804A1 1 0 0 1 8.82 1h2.36a1 1 0 0 1 .98.804l.331 1.652a6.993 6.993 0 0 1 1.929 1.115l1.598-.54a1 1 0 0 1 1.186.447l1.18 2.044a1 1 0 0 1-.205 1.251l-1.267 1.113a7.047 7.047 0 0 1 0 2.228l1.267 1.113a1 1 0 0 1 .205 1.25l-1.18 2.045a1 1 0 0 1-1.187.447l-1.598-.54a6.993 6.993 0 0 1-1.929 1.115l-.33 1.652A1 1 0 0 1 11.18 19H8.82a1 1 0 0 1-.98-.804l-.331-1.652a6.993 6.993 0 0 1-1.929-1.115l-1.598.54a1 1 0 0 1-1.186-.447l-1.18-2.044a1 1 0 0 1 .205-1.251l1.267-1.113a7.05 7.05 0 0 1 0-2.228L1.82 7.593a1 1 0 0 1-.205-1.25l1.18-2.045a1 1 0 0 1 1.187-.447l1.598.54A6.993 6.993 0 0 1 7.51 3.456l.33-1.652Z" clipRule="evenodd" />
              <path d="M10 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
            </svg>
          </button>
          {/* Settings popover */}
          {showSettings && (
            <div
              ref={settingsRef}
              className="absolute bottom-full right-0 mb-2 w-64 rounded-xl border border-border-soft bg-white p-4 shadow-lg"
            >
              <h3 className="mb-3 text-sm font-semibold text-foreground">RAG 检索设置</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-text-tertiary">学生手册 Top-K</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={settings.top_k_manual}
                    onChange={(e) => onSettingsChange({ ...settings, top_k_manual: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border-soft px-3 py-1.5 text-sm outline-none focus:border-brand"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-tertiary">学校贴吧 Top-K</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={settings.top_k_forum}
                    onChange={(e) => onSettingsChange({ ...settings, top_k_forum: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border-soft px-3 py-1.5 text-sm outline-none focus:border-brand"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-tertiary">评分筛选 Top-K</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={settings.top_k_scored}
                    onChange={(e) => onSettingsChange({ ...settings, top_k_scored: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border-soft px-3 py-1.5 text-sm outline-none focus:border-brand"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Message input */}
      <div className="flex items-center gap-3 rounded-2xl bg-bg-card px-5 py-5">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="请输入..."
            disabled={isLoading}
            rows={1}
            className="w-full resize-none rounded-xl border border-border-soft bg-bg-soft px-5 py-3 text-sm text-foreground placeholder-text-tertiary outline-none transition-colors focus:border-brand focus:bg-white disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Message input"
          />
        </div>
        <button
          type="button"
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Send"
          className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-full bg-brand text-white transition-colors hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
            <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChatInput.tsx
git commit -m "feat: add KB retrieval radio buttons and settings popover to ChatInput"
```

---

### Task 9: Frontend — Wire new state through page.tsx

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Pass retrieval state props to ChatInput**

```typescript
const {
  messages, isLoading, error,
  sendMessage, clearMessages, clearError,
  retrievalMode, setRetrievalMode,
  settings, setSettings,
} = useChat();

// In the JSX:
<ChatInput
  onSend={sendMessage}
  isLoading={isLoading}
  retrievalMode={retrievalMode}
  onRetrievalModeChange={setRetrievalMode}
  settings={settings}
  onSettingsChange={setSettings}
/>
```

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && pnpm test`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: wire retrieval mode and settings through page to ChatInput"
```

---

### Task 10: Frontend — Add tests for new ChatInput and useChat features

**Files:**
- Modify: `frontend/src/__tests__/hooks/useChat.test.ts`
- Modify: `frontend/src/__tests__/components/ChatInput.test.tsx`

- [ ] **Step 1: Add useChat test for retrievalMode payload**

In `frontend/src/__tests__/hooks/useChat.test.ts`:

```typescript
it("should include retrieval_mode and settings in POST body", async () => {
  const stream = createSSEStream('data: {"type":"token","token":"","done":true}\n\n');
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: true, body: stream,
  });

  const { result } = renderHook(() => useChat());

  await act(async () => {
    await result.current.sendMessage("Hello");
  });

  const body = JSON.parse(
    (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
  );
  expect(body.retrieval_mode).toBe("auto");
  expect(body.settings).toEqual({ top_k_manual: 6, top_k_forum: 6, top_k_scored: 3 });
});

it("should update retrievalMode state when setRetrievalMode is called", () => {
  const { result } = renderHook(() => useChat());

  act(() => {
    result.current.setRetrievalMode("manual");
  });

  expect(result.current.retrievalMode).toBe("manual");
});

it("should update settings state when setSettings is called", () => {
  const { result } = renderHook(() => useChat());

  act(() => {
    result.current.setSettings({ top_k_manual: 8, top_k_forum: 4, top_k_scored: 5 });
  });

  expect(result.current.settings.top_k_manual).toBe(8);
});
```

- [ ] **Step 2: Add ChatInput tests for KB selector**

In `frontend/src/__tests__/components/ChatInput.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ChatInput from "@/components/ChatInput";

describe("ChatInput KB selector", () => {
  const defaultProps = {
    onSend: vi.fn(),
    isLoading: false,
    retrievalMode: "auto" as const,
    onRetrievalModeChange: vi.fn(),
    settings: { top_k_manual: 6, top_k_forum: 6, top_k_scored: 3 },
    onSettingsChange: vi.fn(),
  };

  it("renders all KB options", () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByText("Auto")).toBeDefined();
    expect(screen.getByText("学生手册")).toBeDefined();
    expect(screen.getByText("学校贴吧")).toBeDefined();
    expect(screen.getByText("都检索")).toBeDefined();
    expect(screen.getByText("不检索")).toBeDefined();
  });

  it("calls onRetrievalModeChange when a KB option is clicked", () => {
    render(<ChatInput {...defaultProps} />);
    fireEvent.click(screen.getByText("学生手册"));
    expect(defaultProps.onRetrievalModeChange).toHaveBeenCalledWith("manual");
  });

  it("highlights the active retrieval mode", () => {
    const props = { ...defaultProps, retrievalMode: "forum" as const };
    render(<ChatInput {...props} />);
    const btn = screen.getByText("学校贴吧");
    expect(btn.className).toContain("bg-brand");
  });

  it("opens settings popover on gear click", () => {
    render(<ChatInput {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Settings"));
    expect(screen.getByText("RAG 检索设置")).toBeDefined();
  });
});
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && pnpm test`
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/__tests__/
git commit -m "test: add tests for retrieval mode and settings in frontend"
```

---

### Task 11: End-to-end verification

**Files:**
- No code changes — verification only

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && pytest tests/ -v`
Expected: all pass

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && pnpm test`
Expected: all pass

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: no type errors

- [ ] **Step 4: Final commit if any fixes were made**

```bash
# Only if there were fixes:
git add -A
git commit -m "fix: address review feedback"
```
