# Retrieval Scoring & Compression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM-based scoring and compression stage to the RAG pipeline between retrieval and answer nodes.

**Architecture:** New `scoring_node` in the LangGraph state machine. Each chunk is serially sent to a dedicated scoring LLM (5th config tier), producing a score (0-100) and compressed content. SSE events per-chunk stream to frontend, which re-sorts by score with animation.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, LangChain, ChromaDB, Next.js 16, TypeScript, Tailwind CSS

---

### Task 1: Add llm_scoring config to Settings

**Files:**
- Modify: `backend/app/core/settings.py`
- Test: `backend/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_settings.py` in `TestSettingsDefaults` class:

```python
def test_default_scoring_llm_model(self):
    settings = get_settings()
    assert settings.llm_scoring_model == "deepseek-chat"

def test_default_scoring_llm_base_url(self):
    settings = get_settings()
    assert settings.llm_scoring_base_url == "https://api.deepseek.com/v1"

def test_default_scoring_llm_api_key_is_empty(self):
    settings = get_settings()
    assert settings.llm_scoring_api_key == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings.py::TestSettingsDefaults::test_default_scoring_llm_model -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'llm_scoring_model'`

- [ ] **Step 3: Write minimal implementation**

Add after the Embedding section in `backend/app/core/settings.py:21-25`:

```python
    # ── Scoring Node ──
    llm_scoring_model: str = "deepseek-chat"
    llm_scoring_base_url: str = "https://api.deepseek.com/v1"
    llm_scoring_api_key: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings.py::TestSettingsDefaults::test_default_scoring_llm_model tests/test_settings.py::TestSettingsDefaults::test_default_scoring_llm_base_url tests/test_settings.py::TestSettingsDefaults::test_default_scoring_llm_api_key_is_empty -v`
Expected: PASS x3

- [ ] **Step 5: Commit**

```bash
git add -f backend/app/core/settings.py backend/tests/test_settings.py
git commit -m "feat: add llm_scoring config tier"
```

---

### Task 2: Add scoring_node to graph

**Files:**
- Modify: `backend/app/graph/graph.py`
- Test: `backend/tests/test_rag_graph.py`

- [ ] **Step 1: Write the failing test for scoring_node**

Add to `backend/tests/test_rag_graph.py`:

```python
from app.graph.graph import (
    ChatState,
    routing_node,
    manual_retrieval_node,
    forum_retrieval_node,
    scoring_node,
    should_retrieve,
)


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_emits_scoring_events(mock_writer):
    scoring_llm = MagicMock()
    scoring_llm.invoke.return_value = AIMessage(
        content='{"score": 85, "compressed": "保留的关键内容"}'
    )
    state: ChatState = {
        "messages": [HumanMessage(content="宿舍管理费多少")],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "宿舍 规定",
        "search_query_forum": "",
        "manual_chunks": ["宿舍管理费每学期500元。收费时间为每学期开学第一周。"],
        "forum_chunks": [],
    }
    result = scoring_node(state, scoring_llm)
    assert "scored_chunks" in result
    assert len(result["scored_chunks"]) == 1
    assert result["scored_chunks"][0]["score"] == 85
    assert result["scored_chunks"][0]["compressed"] == "保留的关键内容"
    assert result["scored_chunks"][0]["source"] == "学生手册"


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_handles_empty_chunks(mock_writer):
    scoring_llm = MagicMock()
    state: ChatState = {
        "messages": [HumanMessage(content="hi")],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
    }
    result = scoring_node(state, scoring_llm)
    assert result["scored_chunks"] == []


@patch("app.graph.graph.get_stream_writer")
def test_scoring_node_fallback_on_llm_error(mock_writer):
    scoring_llm = MagicMock()
    scoring_llm.invoke.side_effect = Exception("API error")
    state: ChatState = {
        "messages": [HumanMessage(content="宿舍")],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "宿舍",
        "search_query_forum": "",
        "manual_chunks": ["内容1"],
        "forum_chunks": [],
    }
    result = scoring_node(state, scoring_llm)
    assert len(result["scored_chunks"]) == 1
    assert result["scored_chunks"][0]["score"] == 0
    assert result["scored_chunks"][0]["compressed"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rag_graph.py::test_scoring_node_emits_scoring_events -v`
Expected: FAIL with `ImportError: cannot import name 'scoring_node'`

- [ ] **Step 3: Write scoring_node implementation**

Add `scored_chunks` to `ChatState` in `backend/app/graph/graph.py:82`:

```python
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    search_manual: bool
    search_forum: bool
    search_query_manual: str
    search_query_forum: str
    manual_chunks: list[str]
    forum_chunks: list[str]
    scored_chunks: list[dict]
```

Add the scoring prompt constant after `RETRIEVAL_CONTEXT_TEMPLATE`:

```python
SCORING_PROMPT = (
    "你是一个校园助手的内容过滤器。你的任务：\n"
    "1. 给你一段文本和一个用户问题\n"
    "2. 判断文本是否与用户问题相关，打分 0-100\n"
    "3. 裁剪掉完全无关的内容，保留与问题相关的部分\n"
    "4. 如果文本中涉及日期等时间信息，务必保留\n"
    "5. 如果整段文本与问题无关，打 0 分，压缩内容留空\n\n"
    "输出必须是以下 JSON 格式，不要添加任何额外内容：\n"
    '{"score": 85, "compressed": "保留的关键内容"}\n\n'
    "用户问题：{user_question}\n"
    "文本内容：{chunk}"
)
```

Add the scoring node function after `forum_retrieval_node`:

```python
def scoring_node(state: ChatState, scoring_llm: BaseChatModel) -> dict:
    """Score and compress each retrieved chunk for relevance."""
    writer = get_stream_writer()
    manual_chunks = state.get("manual_chunks", [])
    forum_chunks = state.get("forum_chunks", [])
    all_chunks: list[tuple[str, str]] = []
    for c in manual_chunks:
        all_chunks.append((c, "学生手册"))
    for c in forum_chunks:
        all_chunks.append((c, "学校贴吧"))

    if not all_chunks:
        writer({"type": "scoring", "source": "done", "done": True})
        return {"scored_chunks": []}

    user_question = state["messages"][-1].content if state["messages"] else ""
    scored_chunks: list[dict] = []
    source_counters: dict[str, int] = {}

    for chunk_text, source in all_chunks:
        source_key = "student_manual" if source == "学生手册" else "school_forum"
        idx = source_counters.get(source_key, 0)
        source_counters[source_key] = idx + 1

        score = 0
        compressed = ""
        try:
            prompt = SCORING_PROMPT.format(
                user_question=user_question[:500],
                chunk=chunk_text[:2000],
            )
            response: AIMessage = scoring_llm.invoke([
                SystemMessage(content=prompt),
            ])
            text = response.content.strip()
            text = text.removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(text)
            score = max(0, min(100, int(parsed.get("score", 0))))
            compressed = parsed.get("compressed", "")
        except Exception:
            logger.warning("Scoring failed for %s chunk %d, defaulting to 0", source_key, idx)
            score = 0
            compressed = ""

        scored_chunks.append({
            "original": chunk_text,
            "source": source,
            "score": score,
            "compressed": compressed,
        })
        writer({
            "type": "scoring",
            "source": source_key,
            "index": idx,
            "score": score,
            "compressed": compressed,
        })

    writer({"type": "scoring", "source": "done", "done": True})
    return {"scored_chunks": scored_chunks}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rag_graph.py::test_scoring_node_emits_scoring_events tests/test_rag_graph.py::test_scoring_node_handles_empty_chunks tests/test_rag_graph.py::test_scoring_node_fallback_on_llm_error -v`
Expected: PASS x3

- [ ] **Step 5: Update graph edges and compile_graph**

Modify `should_retrieve` to route through scoring_node:

```python
def should_retrieve(state: ChatState) -> str:
    """Return the next node: retrieval node or scoring_node."""
    if state.get("search_manual") and not state.get("manual_chunks"):
        return "manual_retrieval_node"
    if state.get("search_forum") and not state.get("forum_chunks"):
        return "forum_retrieval_node"
    return "scoring_node"
```

Update `compile_graph` signature and body:

```python
def compile_graph(
    routing_llm: BaseChatModel,
    chroma: ChromaManager,
    chat_llm: BaseChatModel,
    scoring_llm: BaseChatModel,
) -> StateGraph:
    builder = StateGraph(ChatState)

    builder.add_node("routing_node", lambda state: routing_node(state, routing_llm))
    builder.add_node("manual_retrieval_node", lambda state: manual_retrieval_node(state, chroma))
    builder.add_node("forum_retrieval_node", lambda state: forum_retrieval_node(state, chroma))
    builder.add_node("scoring_node", lambda state: scoring_node(state, scoring_llm))

    async def _answer_node(state):
        return await answer_node(state, chat_llm)

    builder.add_node("answer_node", _answer_node)

    builder.add_edge(START, "routing_node")
    builder.add_conditional_edges("routing_node", should_retrieve, {
        "manual_retrieval_node": "manual_retrieval_node",
        "forum_retrieval_node": "forum_retrieval_node",
        "scoring_node": "scoring_node",
    })
    builder.add_conditional_edges("manual_retrieval_node", should_retrieve, {
        "forum_retrieval_node": "forum_retrieval_node",
        "scoring_node": "scoring_node",
    })
    builder.add_edge("forum_retrieval_node", "scoring_node")
    builder.add_edge("scoring_node", "answer_node")
    builder.add_edge("answer_node", END)

    return builder.compile()
```

- [ ] **Step 6: Update should_retrieve tests**

Update existing tests in `tests/test_rag_graph.py` that expect `"answer_node"` as the terminal edge — they should now expect `"scoring_node"`:

```python
def test_should_retrieve_answer_node_when_no_search():
    state: ChatState = {
        "messages": [],
        "search_manual": False,
        "search_forum": False,
        "search_query_manual": "",
        "search_query_forum": "",
        "manual_chunks": [],
        "forum_chunks": [],
        "scored_chunks": [],
    }
    assert should_retrieve(state) == "scoring_node"
```

Also add `"scored_chunks": []` to all existing test ChatState dicts in `test_rag_graph.py`.

- [ ] **Step 7: Update answer_node to use scored_chunks**

Replace the context construction in `answer_node`:

```python
async def answer_node(state: ChatState, chat_llm: BaseChatModel) -> dict:
    writer = get_stream_writer()
    scored = state.get("scored_chunks", [])
    manual_chunks = state.get("manual_chunks", [])
    forum_chunks = state.get("forum_chunks", [])

    if scored:
        manual_context = "\n\n".join(
            c["compressed"][:500] for c in scored
            if c["source"] == "学生手册" and c["score"] > 0 and c["compressed"]
        )
        forum_context = "\n\n".join(
            c["compressed"][:500] for c in scored
            if c["source"] == "学校贴吧" and c["score"] > 0 and c["compressed"]
        )
        if not manual_context:
            manual_context = "（未检索到相关内容）"
        if not forum_context:
            forum_context = "（未检索到相关内容）"
    else:
        manual_context = "\n\n".join(manual_chunks) if manual_chunks else "（未检索到相关内容）"
        forum_context = "\n\n".join(forum_chunks) if forum_chunks else "（未检索到相关内容）"

    has_context = bool(manual_chunks or forum_chunks)
    messages = list(state["messages"])
    # ... rest unchanged
```

- [ ] **Step 8: Run all graph tests**

Run: `pytest tests/test_rag_graph.py tests/test_graph.py -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add -f backend/app/graph/graph.py backend/tests/test_rag_graph.py
git commit -m "feat: add scoring_node to LangGraph pipeline"
```

---

### Task 3: Wire scoring_llm in ChatService

**Files:**
- Modify: `backend/app/services/chat_service.py`
- Test: `backend/tests/` (existing tests should pass)

- [ ] **Step 1: Create scoring_llm and pass to compile_graph**

In `ChatService.__init__`, add after `self.embedding_client = ...`:

```python
        self.scoring_llm = ChatOpenAI(
            model=settings.llm_scoring_model,
            base_url=settings.llm_scoring_base_url,
            api_key=settings.llm_scoring_api_key,
            streaming=False,
            timeout=15,
        )
```

Update the `compile_graph` call:

```python
        self.graph = compile_graph(
            self.routing_llm, self.chroma, self.chat_llm, self.scoring_llm,
        )
```

- [ ] **Step 2: Run chat service tests**

Run: `pytest tests/test_chat_service.py tests/test_chat_service_rag.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add -f backend/app/services/chat_service.py
git commit -m "feat: wire scoring_llm into ChatService and graph"
```

---

### Task 4: Update frontend types

**Files:**
- Modify: `frontend/src/types/chat.ts`

- [ ] **Step 1: Add "scoring" to MessageRole and update SSEPayload**

```typescript
export type MessageRole = "user" | "assistant" | "system" | "status" | "retrieval" | "scoring" | "error";

export interface SSEPayload {
  type: "status" | "retrieval" | "scoring" | "token" | "error";
  token?: string;
  done?: boolean;
  error?: string;
  node?: string;
  label?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  source?: string;
  chunks?: RetrievalPreview[];
  index?: number;
  score?: number;
  compressed?: string;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add -f frontend/src/types/chat.ts
git commit -m "feat: add scoring type to frontend message types"
```

---

### Task 5: Handle scoring SSE events in useChat hook

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`
- Test: `frontend/src/__tests__/hooks/useChat.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/__tests__/hooks/useChat.test.ts`:

```typescript
  it("should handle scoring events and update chunk scores", async () => {
    const stream = createSSEStream(
      'data: {"type":"retrieval","source":"school_forum","label":"已检索到【学校贴吧】相关讨论","chunks":[{"preview":"宿舍管理费每学期500元","source":"学校贴吧"},{"preview":"食堂推荐窗口","source":"学校贴吧"}]}\n\n',
      'data: {"type":"scoring","source":"school_forum","index":0,"score":85,"compressed":"宿舍管理费500元"}\n\n',
      'data: {"type":"scoring","source":"school_forum","index":1,"score":30,"compressed":"食堂"}\n\n',
      'data: {"type":"scoring","source":"done","done":true}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("宿舍管理费");
    });

    const msgs = result.current.messages;
    const retrievalMsg = msgs.find((m) => m.role === "retrieval");
    expect(retrievalMsg).toBeDefined();
    expect(retrievalMsg!.chunks![0].score).toBe(85);
    expect(retrievalMsg!.chunks![0].compressed).toBe("宿舍管理费500元");
    expect(retrievalMsg!.chunks![1].score).toBe(30);
    expect(retrievalMsg!.chunks![1].compressed).toBe("食堂");
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test -- src/__tests__/hooks/useChat.test.ts`
Expected: FAIL - scoring not handled yet

- [ ] **Step 3: Add scoring event handling in useChat**

After the `retrieval` event handler block in `useChat.ts:104-119`, add:

```typescript
            if (payload.type === "scoring" && payload.source === "done" && payload.done) {
              continue;
            }

            if (payload.type === "scoring" && payload.source && payload.index !== undefined) {
              setMessages((prev) => {
                const updated = [...prev];
                const sourceMap: Record<string, string> = {
                  school_forum: "学校贴吧",
                  student_manual: "学生手册",
                };
                const targetSource = sourceMap[payload.source] || payload.source;
                for (let j = updated.length - 1; j >= 0; j--) {
                  const msg = updated[j];
                  if (msg.role === "retrieval" && msg.chunks) {
                    const chunksFromSource = msg.chunks.filter(
                      (c) => c.source === targetSource,
                    );
                    if (chunksFromSource.length > 0) {
                      const newChunks = [...msg.chunks];
                      const localIdx = msg.chunks.indexOf(chunksFromSource[payload.index!]);
                      if (localIdx >= 0) {
                        newChunks[localIdx] = {
                          ...newChunks[localIdx],
                          score: payload.score,
                          compressed: payload.compressed,
                        };
                        updated[j] = { ...msg, chunks: newChunks };
                      }
                      break;
                    }
                  }
                }
                return updated;
              });
              continue;
            }
```

Also update `RetrievalPreview` type in `frontend/src/types/chat.ts` to include optional `score` and `compressed`:

```typescript
export interface RetrievalPreview {
  preview: string;
  source: string;
  score?: number;
  compressed?: string;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test -- src/__tests__/hooks/useChat.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -f frontend/src/hooks/useChat.ts frontend/src/types/chat.ts frontend/src/__tests__/hooks/useChat.test.ts
git commit -m "feat: handle scoring SSE events in useChat hook"
```

---

### Task 6: Update RetrievalCard with score display and sorting animation

**Files:**
- Modify: `frontend/src/components/RetrievalCard.tsx`
- Modify: `frontend/src/components/ChatMessage.tsx`
- Test: `frontend/src/__tests__/components/RetrievalCard.test.tsx`

- [ ] **Step 1: Write the failing test**

Overwrite `frontend/src/__tests__/components/RetrievalCard.test.tsx`:

```typescript
import "@testing-library/jest-dom/vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";
import RetrievalCard from "@/components/RetrievalCard";

afterEach(() => {
  cleanup();
});

describe("RetrievalCard", () => {
  const chunks = [
    { preview: "宿舍管理费每学期500元", source: "学校贴吧", score: 85, compressed: "宿舍管理费500元" },
    { preview: "食堂推荐窗口", source: "学校贴吧", score: 30, compressed: "食堂" },
  ];

  it("shows score for each chunk", () => {
    render(<RetrievalCard chunks={chunks} />);
    expect(screen.getByText("score: 85")).toBeInTheDocument();
    expect(screen.getByText("score: 30")).toBeInTheDocument();
  });

  it("opens a modal with compressed content when clicking 详情", () => {
    render(<RetrievalCard chunks={chunks} />);
    const detailButtons = screen.getAllByText("详情");
    fireEvent.click(detailButtons[0]);
    expect(screen.getByText("宿舍管理费500元")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows 评分中... when score is undefined", () => {
    const pendingChunks = [
      { preview: "宿舍管理费每学期500元", source: "学校贴吧" },
    ];
    render(<RetrievalCard chunks={pendingChunks} />);
    expect(screen.getByText("评分中...")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test -- src/__tests__/components/RetrievalCard.test.tsx`
Expected: FAIL - current component doesn't show score or "评分中..."

- [ ] **Step 3: Update RetrievalCard implementation**

Rewrite `frontend/src/components/RetrievalCard.tsx`:

```typescript
"use client";

import { useState, useMemo } from "react";
import type { RetrievalPreview } from "@/types/chat";
import DetailModal from "@/components/DetailModal";

interface RetrievalCardProps {
  chunks: RetrievalPreview[];
}

export default function RetrievalCard({ chunks }: RetrievalCardProps) {
  const [modalIndex, setModalIndex] = useState<number | null>(null);

  const allScored = chunks.every((c) => c.score !== undefined);
  const sorted = useMemo(() => {
    if (!allScored) return chunks;
    return [...chunks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  }, [chunks, allScored]);

  if (chunks.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-400">
        无相关内容
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sorted.map((chunk, i) => (
        <div
          key={i}
          className="overflow-hidden rounded-lg border border-gray-200 transition-all duration-500"
        >
          <div className="flex w-full items-center gap-2 bg-white px-3 py-2 text-left text-sm">
            <span className="shrink-0 rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
              {chunk.source}
            </span>
            {chunk.score !== undefined ? (
              <span className="shrink-0 text-xs font-semibold text-blue-600">
                score: {chunk.score}
              </span>
            ) : (
              <span className="shrink-0 animate-pulse text-xs text-gray-400">
                评分中...
              </span>
            )}
            <span className="line-clamp-1 min-w-0 flex-1 text-gray-500">
              {chunk.preview.slice(0, 60)}...
            </span>
            {chunk.score !== undefined && (
              <button
                onClick={() => setModalIndex(i)}
                className="shrink-0 text-xs text-blue-500 hover:text-blue-700"
              >
                详情
              </button>
            )}
          </div>
        </div>
      ))}
      {modalIndex !== null && (
        <DetailModal
          content={sorted[modalIndex].compressed || sorted[modalIndex].preview}
          source={sorted[modalIndex].source}
          onClose={() => setModalIndex(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test -- src/__tests__/components/RetrievalCard.test.tsx`
Expected: PASS

- [ ] **Step 5: Ensure all frontend tests pass**

Run: `cd frontend && pnpm test`
Expected: All 90+ tests pass

- [ ] **Step 6: Commit**

```bash
git add -f frontend/src/components/RetrievalCard.tsx frontend/src/__tests__/components/RetrievalCard.test.tsx
git commit -m "feat: add score display and sorting animation to RetrievalCard"
```

---

### Task 7: Full verification

**Files:**
- All modified files

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: All 136+ tests pass

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && pnpm test`
Expected: All 90+ tests pass

- [ ] **Step 3: TypeScript typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors
