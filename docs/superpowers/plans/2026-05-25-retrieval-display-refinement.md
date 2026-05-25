# Retrieval Display Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make retrieval cards collapsible by default and highlight the specific chunks the AI selected for the final answer context.

**Architecture:** Backend emits a new `context_selected` SSE event from `answer_node` listing which chunks were used. Frontend stores the selected chunk identifiers, passes them to `RetrievalCard`, and renders matching chunks with a green highlight. The retrieval card in `ChatMessage` becomes collapsible (default collapsed).

**Tech Stack:** Python 3.11+ / FastAPI / LangGraph / Next.js 16 / React 19 / TypeScript 5

---

### Task 1: Backend — Emit `context_selected` SSE event from answer_node

**Files:**
- Modify: `backend/app/graph/graph.py:486-520` (answer_node)

- [ ] **Step 1: Add context_selected emission after selecting top_k_scored**

In `answer_node`, after `sorted_scored` is computed and before the context building, emit the selected chunks:

```python
    # After line ~496, before the context building:
    selected_for_context = []
    sorted_scored = sorted(scored, key=lambda c: c["score"], reverse=True)[:top_k_scored]
    for c in sorted_scored:
        if c["score"] > 0:
            selected_for_context.append({
                "source": c["source"],
                "preview": c["original"][:60],
            })
    if selected_for_context:
        writer({
            "type": "context_selected",
            "selected": selected_for_context,
        })
```

Place this right after the `sorted_scored = ...[:top_k_scored]` line at line ~496, before the context string building.

- [ ] **Step 2: Run graph tests**

Run: `cd backend && pytest tests/test_graph.py tests/test_rag_graph.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/graph/graph.py
git commit -m "feat: emit context_selected SSE event from answer_node"
```

---

### Task 2: Backend — Add test for context_selected event

**Files:**
- Modify: `backend/tests/test_rag_graph.py`

- [ ] **Step 1: Add test for context_selected emission**

In `backend/tests/test_rag_graph.py`, add after `test_answer_node_uses_top_k_scored_chunks`:

```python
@patch("app.graph.graph.get_stream_writer")
@pytest.mark.asyncio
async def test_answer_node_emits_context_selected(mock_writer):
    """answer_node should emit context_selected with selected chunks."""
    from app.graph.graph import answer_node

    chat_llm = MagicMock()
    async def _mock_astream(messages):
        yield AIMessageChunk(content="Answer")
    chat_llm.astream = _mock_astream

    state = {
        "messages": [HumanMessage(content="test")],
        "search_manual": True,
        "search_forum": False,
        "search_query_manual": "test",
        "search_query_forum": "",
        "manual_chunks": ["chunk A content here"],
        "forum_chunks": [],
        "scored_chunks": [
            {"original": "chunk A content here", "source": "学生手册", "score": 90},
        ],
        "retrieval_mode": "auto",
        "settings": {"top_k_scored": 3},
    }

    result = await answer_node(state, chat_llm)

    writer_calls = mock_writer.call_args_list
    context_events = [call[0][0] for call in writer_calls if call[0][0].get("type") == "context_selected"]
    assert len(context_events) == 1, "Expected exactly one context_selected event"
    event = context_events[0]
    assert "selected" in event
    assert len(event["selected"]) == 1
    assert event["selected"][0]["source"] == "学生手册"
```

- [ ] **Step 2: Run the new test**

Run: `cd backend && pytest tests/test_rag_graph.py::test_answer_node_emits_context_selected -v`
Expected: PASS

- [ ] **Step 3: Run all related tests**

Run: `cd backend && pytest tests/test_graph.py tests/test_rag_graph.py -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_rag_graph.py
git commit -m "test: add test for context_selected SSE event"
```

---

### Task 3: Frontend — Add types for context_selected SSE event

**Files:**
- Modify: `frontend/src/types/chat.ts`

- [ ] **Step 1: Add SelectedChunk interface and update SSEPayload**

```typescript
export interface SelectedChunk {
  source: string;
  preview: string;
}

export interface SSEPayload {
  type: "status" | "retrieval" | "scoring" | "token" | "intent" | "error" | "context_selected";
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
  optimized_query?: string;
  compressed_context?: string;
  selected?: SelectedChunk[];
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/chat.ts
git commit -m "feat: add SelectedChunk type and context_selected to SSEPayload"
```

---

### Task 4: Frontend — Handle context_selected in useChat hook

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Add selectedChunks state + handle the new SSE event**

Add state:
```typescript
const [selectedChunks, setSelectedChunks] = useState<SelectedChunk[]>([]);
const selectedChunksRef = useRef<SelectedChunk[]>(selectedChunks);
selectedChunksRef.current = selectedChunks;
```

In the SSE parsing loop, add a handler before `if (payload.type === "token")`:
```typescript
if (payload.type === "context_selected" && payload.selected) {
  setSelectedChunks(payload.selected);
  continue;
}
```

Update the return to include `selectedChunks`:
```typescript
return {
  messages, isLoading, error,
  sendMessage, clearMessages, clearError,
  retrievalMode, setRetrievalMode: setRetrievalModeAndPersist,
  settings, setSettings: setSettingsAndPersist,
  selectedChunks,
};
```

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && pnpm test 2>&1`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: handle context_selected SSE event in useChat"
```

---

### Task 5: Frontend — Make retrieval card collapsible + highlight selected chunks

**Files:**
- Modify: `frontend/src/components/ChatMessage.tsx`
- Modify: `frontend/src/components/RetrievalCard.tsx`

- [ ] **Step 1: Make retrieval card collapsible in ChatMessage.tsx**

Change the `role === "retrieval"` section:

```typescript
if (message.role === "retrieval") {
  const [expanded, setExpanded] = useState(false);
  return (
    <div data-testid="chat-message">
      <BentoCard className="flex flex-col gap-3.5">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between text-left"
        >
          <span className="font-display text-base font-semibold text-black">
            📄 {message.content}
          </span>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className={`h-4 w-4 text-text-tertiary transition-transform ${expanded ? "rotate-180" : ""}`}
          >
            <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clipRule="evenodd" />
          </svg>
        </button>
        {expanded && message.chunks && (
          <RetrievalCard
            chunks={message.chunks}
            selectedChunks={selectedChunks}
          />
        )}
      </BentoCard>
    </div>
  );
}
```

Note: Add `import { useState } from "react";` at the top of the file.

- [ ] **Step 2: Update RetrievalCard to accept and render selected chunks**

Update props and add green highlight for selected chunks:

```typescript
"use client";

import { useState, useMemo } from "react";
import type { RetrievalPreview, SelectedChunk } from "@/types/chat";
import DetailModal from "@/components/DetailModal";

interface RetrievalCardProps {
  chunks: RetrievalPreview[];
  selectedChunks?: SelectedChunk[];
}

function isSelected(chunk: RetrievalPreview, selected: SelectedChunk[]): boolean {
  return selected.some((s) => s.source === chunk.source && chunk.preview.startsWith(s.preview));
}

export default function RetrievalCard({ chunks, selectedChunks = [] }: RetrievalCardProps) {
  const [modalIndex, setModalIndex] = useState<number | null>(null);

  const allScored = chunks.every((c) => c.score !== undefined);
  const sorted = useMemo(() => {
    if (!allScored) return chunks;
    return [...chunks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  }, [chunks, allScored]);

  if (chunks.length === 0) {
    return (
      <div className="rounded-xl bg-bg-soft px-4 py-3 text-sm text-text-tertiary shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
        无相关内容
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((chunk, i) => {
        const selected = isSelected(chunk, selectedChunks);
        return (
          <div
            key={i}
            className={`rounded-xl bg-bg-soft px-[18px] py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] ${
              selected ? "border-l-4 border-green-500" : ""
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className="shrink-0 rounded bg-brand-light px-1.5 py-0.5 text-xs font-medium text-brand">
                {chunk.source}
              </span>
              {chunk.score !== undefined ? (
                <span className="shrink-0 text-xs font-semibold text-brand">
                  score: {chunk.score}
                </span>
              ) : (
                <span className="shrink-0 animate-pulse text-xs text-text-tertiary">
                  评分中...
                </span>
              )}
              {selected && (
                <span className="ml-auto shrink-0 text-xs font-medium text-green-600">
                  ✓ 已用于回答
                </span>
              )}
            </div>
            <div className="mt-2 text-sm leading-relaxed text-text-body line-clamp-1">
              {chunk.preview.slice(0, 60)}...
            </div>
            <div className="mt-2">
              {chunk.score !== undefined && (
                <button
                  onClick={() => setModalIndex(i)}
                  className="text-xs font-medium text-brand hover:text-orange-700"
                >
                  详情 →
                </button>
              )}
            </div>
          </div>
        );
      })}
      {modalIndex !== null && (
        <DetailModal
          content={sorted[modalIndex].preview}
          source={sorted[modalIndex].source}
          onClose={() => setModalIndex(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Update page.tsx to pass selectedChunks to ChatInput**

Wait — `selectedChunks` is not a ChatInput prop. It's used by `ChatMessage` which is rendered in `page.tsx`. The `ChatMessage` component needs access to `selectedChunks`.

In `page.tsx`, pass `selectedChunks` from `useChat` to `ChatMessage`:

```typescript
const {
  messages, isLoading, error,
  sendMessage, clearMessages, clearError,
  retrievalMode, setRetrievalMode,
  settings, setSettings,
  selectedChunks,
} = useChat();

// In the map:
{messages.map((msg) => (
  <ChatMessage key={msg.id} message={msg} selectedChunks={selectedChunks} />
))}
```

Update `ChatMessageProps` in ChatMessage.tsx:
```typescript
interface ChatMessageProps {
  message: ChatMessageType;
  selectedChunks?: SelectedChunk[];
}
```

And pass it through:
```typescript
export default function ChatMessage({ message, selectedChunks = [] }: ChatMessageProps) {
```

For the retrieval card rendering:
```typescript
{expanded && message.chunks && (
  <RetrievalCard
    chunks={message.chunks}
    selectedChunks={selectedChunks}
  />
)}
```

- [ ] **Step 4: Run frontend tests**

Run: `cd frontend && pnpm test 2>&1`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChatMessage.tsx frontend/src/components/RetrievalCard.tsx frontend/src/app/page.tsx
git commit -m "feat: collapsible retrieval cards with green highlight on selected chunks"
```

---

### Task 6: Frontend — Add/update tests

**Files:**
- Modify: `frontend/src/__tests__/components/RetrievalCard.test.tsx`
- Modify: `frontend/src/__tests__/hooks/useChat.test.ts`

- [ ] **Step 1: Update RetrievalCard test**

Read the current `frontend/src/__tests__/components/RetrievalCard.test.tsx` and add a new `describe("selected chunks")` block:

```typescript
describe("RetrievalCard selected chunks", () => {
  const chunks: RetrievalPreview[] = [
    { preview: "宿舍管理费每学期500元", source: "学校贴吧", score: 90 },
    { preview: "食堂推荐窗口", source: "学校贴吧", score: 30 },
  ];

  it("renders green highlight for selected chunks", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[{ source: "学校贴吧", preview: "宿舍管理费每学期500元" }]} />);
    const labels = screen.getAllByText("✓ 已用于回答");
    expect(labels).toHaveLength(1);
  });

  it("renders no highlight when selectedChunks is empty", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[]} />);
    expect(screen.queryByText("✓ 已用于回答")).toBeNull();
  });

  it("renders no highlight when no match", () => {
    render(<RetrievalCard chunks={chunks} selectedChunks={[{ source: "学校贴吧", preview: "nonexistent" }]} />);
    expect(screen.queryByText("✓ 已用于回答")).toBeNull();
  });
});
```

- [ ] **Step 2: Add useChat test for context_selected event**

In `frontend/src/__tests__/hooks/useChat.test.ts`:

```typescript
it("should store selectedChunks from context_selected event", async () => {
  const stream = createSSEStream(
    'data: {"type":"context_selected","selected":[{"source":"学生手册","preview":"旷课处分规定"}]}\n\n',
    'data: {"type":"token","token":"","done":true}\n\n',
  );
  (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: true, body: stream,
  });

  const { result } = renderHook(() => useChat());

  await act(async () => {
    await result.current.sendMessage("test");
  });

  expect(result.current.selectedChunks).toEqual([
    { source: "学生手册", preview: "旷课处分规定" },
  ]);
});
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && pnpm test 2>&1`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/__tests__/
git commit -m "test: add tests for selected chunks highlighting and context_selected event"
```

---

### Task 7: End-to-end verification

**Files:**
- No code changes — verification only

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && pytest tests/test_graph.py tests/test_rag_graph.py -v`
Expected: all pass

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && pnpm test 2>&1`
Expected: all pass

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no errors
