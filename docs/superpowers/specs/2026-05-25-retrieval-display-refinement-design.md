# Retrieval Display Refinement — Design Spec

**Date:** 2026-05-25
**Status:** Approved

## Overview

Refine the retrieval chunk display in the chat UI: make retrieval cards collapsible (default collapsed), and highlight the specific chunks that the AI selected for the final answer context.

## Changes

### Backend: New SSE event `context_selected`

The `answer_node` already selects `top_k_scored` chunks by sorting `scored_chunks` descending and taking top N. After selecting, emit a new SSE event telling the frontend exactly which chunks made it into the final context.

```python
# In answer_node, after selecting sorted_scored:
selected_chunks = []
for c in sorted_scored:
    if c["score"] > 0:
        selected_chunks.append({"source": c["source"], "preview": c["original"][:60]})
if selected_chunks:
    writer({
        "type": "context_selected",
        "selected": selected_chunks,
    })
```

Format:
```json
{"type": "context_selected", "selected": [{"source": "学生手册", "preview": "..."}, {"source": "学校贴吧", "preview": "..."}]}
```

### Frontend: New SSE event handler

In `useChat.ts`, handle `"context_selected"` events by storing the selected chunks in a new state field.

### Frontend: Collapsible retrieval cards

In `ChatMessage.tsx`, the `role === "retrieval"` card changes to:
- Default collapsed — show only the header line with collapse indicator (chevron icon)
- Click to expand/collapse, revealing the full `RetrievalCard`

### Frontend: Highlight selected chunks

In `RetrievalCard.tsx`, accept a new `selectedChunks` prop (set of source+preview identifiers). Chunks present in this set render with:
- Green left border (`border-l-4 border-green-500`)
- A small green badge "✓ 已用于回答"
- Remains sorted by score descending (existing behavior)

### Data Flow

```
answer_node selects top_k_scored chunks
  → emits "context_selected" SSE with selected chunk identifiers
  → frontend stores selectedChunks in state
  → RetrievalCard receives selectedChunks prop
  → matching chunks render with green highlight
```

### SSE Event Type Update

Add `"context_selected"` to `SSEPayload.type` union and `SSEPayload` interface in `frontend/src/types/chat.ts`.

```typescript
export interface SelectedChunk {
  source: string;
  preview: string;
}

// In SSEPayload:
type?: "status" | "retrieval" | "scoring" | "token" | "intent" | "error" | "context_selected";
selected?: SelectedChunk[];
```

### Files Changed

| File | Change |
|------|--------|
| `backend/app/graph/graph.py` | Emit `context_selected` event in `answer_node` after selecting top_k_scored |
| `frontend/src/types/chat.ts` | Add `context_selected` to SSEPayload type + `SelectedChunk` interface |
| `frontend/src/hooks/useChat.ts` | Handle `context_selected` SSE events |
| `frontend/src/components/ChatMessage.tsx` | Make retrieval card collapsible (default collapsed) |
| `frontend/src/components/RetrievalCard.tsx` | Accept `selectedChunks` prop, render green highlight |

## Error Handling

- If `answer_node` fails to select chunks, no `context_selected` event is emitted — frontend shows all chunks without highlights (graceful degradation)
- Empty `selected` array is not emitted

## Testing

### Backend
- `answer_node` emits `context_selected` event with correct selected chunks
- Event is not emitted when no chunks have score > 0

### Frontend
- Retrieval card renders collapsed by default
- Click expands/collapses the card
- Selected chunks render with green highlight and "已用于回答" badge
- Non-selected chunks render normally
