# Multi-Stage SSE Streaming for Chat Interface

**Date:** 2026-05-21
**Status:** Draft
**Authors:** brainstorming session

## Overview

Currently the chat SSE endpoint streams only final answer tokens (`{"token":"...","done":false}`). The user sees no intermediate feedback while the backend performs routing classification and RAG retrieval. This spec describes a multi-stage SSE protocol that exposes graph node execution as visible stages in the frontend: **thinking/status → retrieval cards → final answer**.

## Architecture

```
User Question
    │
    ▼
graph.astream(["updates", "messages"])
    │
    ├── routing_node
    │     └── SSE: type="status" (node=routing, decision, label)
    │
    ├── manual_retrieval_node  (if search_manual=true)
    │     └── SSE: type="retrieval" (source=student_manual, chunks)
    │
    ├── forum_retrieval_node   (if search_forum=true)
    │     └── SSE: type="retrieval" (source=school_forum, chunks)
    │
    └── answer_node
          └── SSE: type="token" (token="...")  ← streaming final answer
               └── SSE: type="token" (token="", done=true)  ← terminal
```

## 1. SSE Event Protocol

### Event Types

#### `type: "status"`
Emitted when a non-retrieval graph node completes (e.g. routing).

```
{"type":"status","node":"routing","label":"正在分析你的问题...",
 "decision":{"search_manual":true,"search_forum":false}}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"status"` | yes | Event type |
| `node` | string | yes | Graph node name (`routing`, `answer`, etc.) |
| `label` | string | yes | Human-readable status text for frontend display |
| `decision` | object | no | Routing decision (`search_manual`, `search_forum`) |
| `done` | boolean | no | Always falsy for status events |

#### `type: "retrieval"`
Emitted when a retrieval node completes.

```
{"type":"retrieval","source":"student_manual",
 "label":"已检索到【学生手册】相关规定",
 "chunks":[{"preview":"第四十一条 对无故旷课学生按下列原则处理...\n（一）...","source":"学生手册"}]}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"retrieval"` | yes | Event type |
| `source` | `"student_manual"` \| `"school_forum"` | yes | Knowledge base identifier |
| `label` | string | yes | Human-readable label |
| `chunks` | array of `ChunkPreview` | yes | Retrieved chunk previews (may be empty) |
| `done` | boolean | no | Always falsy for retrieval events |

`ChunkPreview`:
| Field | Type | Description |
|-------|------|-------------|
| `preview` | string | First ~200 chars of the chunk |
| `source` | string | Chinese label: `"学生手册"` or `"学校贴吧"` |

#### `type: "token"`
Streaming token from the final answer.

```
{"type":"token","token":"根据"}
{"type":"token","token":"","done":true}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"token"` | yes | Event type |
| `token` | string | yes | Text fragment (empty in terminal event) |
| `done` | boolean | no | `true` signals stream end |

#### `type: "error"`
Fatal error during any stage.

```
{"type":"error","error":"生成回答失败，请重试","done":true}
```

### Terminal Signal

- **Normal flow**: `{"type":"token","token":"","done":true}`
- **Error flow**: `{"type":"error","error":"...","done":true}`

The frontend MUST treat *any* event with `"done":true` as terminal and finalize the assistant message.

### Example: Complete SSE Sequence

```
# Routing executes
data: {"type":"status","node":"routing","label":"正在分析你的问题...","decision":{"search_manual":true,"search_forum":false}}

# Manual retrieval executes
data: {"type":"retrieval","source":"student_manual","label":"已检索到【学生手册】相关规定","chunks":[{"preview":"第四十一条...","source":"学生手册"}]}

# Forum retrieval skipped (search_forum=false)

# Answer node streams
data: {"type":"token","token":"根据"}
data: {"type":"token","token":"学生手册"}
data: {"type":"token","token":"规定"}
data: {"type":"token","token":"","done":true}
```

## 2. Graph Changes

### New Node: `answer_node`

Added to `backend/app/graph/graph.py`. Responsible for generating the final answer using the chat LLM with retrieved context.

```
def answer_node(state: ChatState, chat_llm: ChatOpenAI) -> dict:
    # Build context-augmented messages from retrieved chunks
    augmented = build_context_messages(state)
    # invoke returns AIMessage; LangGraph astream(messages) captures chunks
    return {"messages": [chat_llm.invoke(augmented)]}
```

### Graph Topology Change

```
Current:                      New:
START → routing_node          START → routing_node
  → manual_retrieval_node       → manual_retrieval_node
  → forum_retrieval_node        → forum_retrieval_node
  → END (graph done)            → answer_node ← NEW
  (then separate astream)       → END
```

### State Schema Change

Add `search_query_manual` and `search_query_forum` fields:

```python
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    search_manual: bool
    search_forum: bool
    search_query_manual: str   # ← NEW: optimized query for student_manual
    search_query_forum: str    # ← NEW: optimized query for school_forum
    manual_chunks: list[str]
    forum_chunks: list[str]
```

### Execution: `graph.astream()` replaces `graph.invoke()`

In `chat_service.py`:

```python
async for event_type, event_data in self.graph.astream(
    initial_state,
    stream_mode=["updates", "messages"]
):
    if event_type == "updates":
        node_name = next(iter(event_data))
        node_output = event_data[node_name]
        sse_event = self._convert_update_to_sse(node_name, node_output)
        if sse_event:
            yield json.dumps(sse_event, ensure_ascii=False)
    elif event_type == "messages":
        msg_chunk, metadata = event_data
        if isinstance(msg_chunk, AIMessageChunk) and msg_chunk.content:
            yield json.dumps({"type": "token", "token": msg_chunk.content}, ensure_ascii=False)

# Terminal event
yield json.dumps({"type": "token", "token": "", "done": true})
```

## 3. Routing Prompt Optimization

### Current Prompt

```python
ROUTING_SYSTEM_PROMPT = (
    "You are a routing classifier for a campus assistant. "
    "Given a user's question, determine whether it requires knowledge from:\n"
    "1. student_manual — the school's student handbook (rules, policies, procedures)\n"
    "2. school_forum — the school's forum/bbs (campus life, events, gossip)\n"
    "Respond with valid JSON only: "
    '{"search_manual": true/false, "search_forum": true/false}. '
    "Set each field to true if the question is relevant to that knowledge source."
)
```

### New Prompt

```python
ROUTING_SYSTEM_PROMPT = (
    "You are a routing classifier for a campus assistant. "
    "Given a user's question, determine whether it requires knowledge from:\n"
    "1. student_manual — the school's student handbook (rules, policies, procedures)\n"
    "2. school_forum — the school's forum/bbs (campus life, events, gossip)\n\n"
    "For each knowledge source that is relevant, generate an optimized search query "
    "for vector retrieval. Extract key terms and reformulate specifically for that source.\n\n"
    "Respond with valid JSON only:\n"
    '{"search_manual": true/false, "search_forum": true/false,\n'
    ' "search_query_manual": "...", "search_query_forum": "..."}\n\n'
    "Examples:\n"
    '- "旷课会不会被处分"\n'
    '  → {"search_manual": true, "search_forum": false,\n'
    '     "search_query_manual": "旷课 处分 规定 节数",\n'
    '     "search_query_forum": ""}\n'
    '- "旷课了能去食堂吃饭吗"\n'
    '  → {"search_manual": true, "search_forum": true,\n'
    '     "search_query_manual": "旷课 处分 规定",\n'
    '     "search_query_forum": "食堂 吃饭 推荐"}\n'
    '- "今天天气怎么样"\n'
    '  → {"search_manual": false, "search_forum": false,\n'
    '     "search_query_manual": "", "search_query_forum": ""}'
)
```

### Retrieval Node Change

Retrieval nodes use `state["search_query_manual"]` / `state["search_query_forum"]` instead of the raw user message:

```python
def manual_retrieval_node(state, chroma):
    if not state["search_manual"]:
        return {"manual_chunks": []}
    query = state.get("search_query_manual") or ""
    if not query:
        return {"manual_chunks": []}
    return {"manual_chunks": chroma.retrieve(COLLECTION_MANUAL, query)}
```

## 4. Frontend Changes

### Extended `ChatMessage` Type

```typescript
type MessageRole = "user" | "assistant" | "system" | "status" | "retrieval" | "error";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  node?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  chunks?: RetrievalPreview[];
}

interface RetrievalPreview {
  preview: string;
  source: string;
}
```

### `useChat` Hook Changes

The SSE parser must handle the new `type` field:

```typescript
// On receiving SSE data:
if (payload.type === "status") {
  // Insert a status message before the assistant placeholder
  insertMessage({
    id: generateId(),
    role: "status",
    content: payload.label || "",
    timestamp: Date.now(),
    node: payload.node,
    decision: payload.decision,
  });
} else if (payload.type === "retrieval") {
  // Insert a retrieval message before the assistant placeholder
  insertMessage({
    id: generateId(),
    role: "retrieval",
    content: payload.label || "",
    timestamp: Date.now(),
    chunks: payload.chunks || [],
  });
} else if (payload.type === "token") {
  // Append token to last assistant message (existing behavior)
  appendToken(payload.token);
  if (payload.done) {
    finalizeAssistantMessage();
  }
} else if (payload.type === "error") {
  setError(payload.error);
  finalizeAssistantMessage();
}
```

Status and retrieval messages are inserted **before** the last message (the assistant streaming placeholder), maintaining chronological order:
- user → status → retrieval → assistant(streaming)

### Rendering: `ChatMessage.tsx`

| `role` | Style | Behavior |
|--------|-------|----------|
| `user` | Right-aligned blue bubble (unchanged) | — |
| `status` | Left-aligned, grey background, reduced text opacity, small node label | Pulsing dot or spinner icon |
| `retrieval` | Left-aligned, light green border, card-like container | Chunks shown as compact preview cards; click to expand full content |
| `assistant` | Left-aligned grey bubble with Markdown (unchanged) | — |
| `error` | Red border, error icon | Dismissable |

### Optional: Retrieval Card Expansion

Each chunk preview in a retrieval message should be clickable. On click, show the full chunk content in a modal or inline expansion. This satisfies the user requirement: "可以不用完全渲染出来，并且用户还可以方便用户点击查看详情具体的召回内容".

## 5. Error Handling

| Scenario | Behavior | SSE Output |
|----------|----------|------------|
| Routing node JSON parse fails | Default both `search_*` to false, skip retrieval, go to answer_node | `status: "无法判断需求，直接回答"` |
| ChromaDB query fails | Return empty chunks, proceed to answer_node | `retrieval: {chunks: []}` (empty) |
| Answer node LLM fails | Emit error event | `error: "生成回答失败，请重试"` |
| Graph-level exception | Catch, emit error | `error: "服务异常，请重试"` |
| User sends new message while streaming | Current behavior: ignored (isLoading guard) | — |

## 6. Files Changed

### Backend
| File | Change |
|------|--------|
| `backend/app/graph/graph.py` | Add `search_query_manual`/`search_query_forum` to state schema; add `answer_node`; update graph edges; update routing prompt |
| `backend/app/services/chat_service.py` | Replace `graph.invoke()` with `graph.astream()`; add SSE conversion logic; remove direct `ChatOpenAI.astream()` call |
| `backend/app/api/chat.py` | Minor: no functional change (event_generator stays the same, just receives richer events from stream_chat) |

### Frontend
| File | Change |
|------|--------|
| `frontend/src/types/chat.ts` | Extend `ChatMessage` with `role` union + optional fields; add `RetrievalPreview` type |
| `frontend/src/hooks/useChat.ts` | Parse SSE `type` field; handle `status`/`retrieval` events; insert messages before assistant placeholder |
| `frontend/src/components/ChatMessage.tsx` | Add rendering for `status` and `retrieval` roles |
| `frontend/src/components/` | Optional: new `RetrievalCard` or `ExpansionModal` component |

### Tests
| File | Change |
|------|--------|
| `backend/tests/test_graph.py` | Update for new state schema + answer_node |
| `backend/tests/test_chat_service.py` | Update streaming test for multi-stage output |
| `backend/tests/test_rag_graph.py` | Update for new routing output format |
| `frontend (tests)` | Update SSE handling tests |
