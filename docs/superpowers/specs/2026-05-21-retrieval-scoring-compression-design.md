# Retrieval Scoring & Compression Design

**Date:** 2026-05-21
**Status:** Draft

## Overview

Add an LLM-based scoring and compression stage to the RAG pipeline. Each retrieved chunk is independently scored (0-100) for relevance to the user question, and irrelevant content is cropped out. The final answer uses only compressed content from high-scoring chunks.

## Motivation

Raw ChromaDB retrieval returns chunks based on vector similarity, which often includes irrelevant content. By scoring and compressing each chunk per-question, we improve:

- **Answer quality** — the LLM only sees relevant content
- **Context efficiency** — compressed chunks use fewer tokens
- **Transparency** — users see relevance scores and can judge result quality

## Architecture

### LLM Config

New 5th LLM tier in `Settings`:

```
llm_scoring_model      = "deepseek-chat"
llm_scoring_base_url   = "https://api.deepseek.com/v1"
llm_scoring_api_key    = ""
```

`ChatService.__init__` creates:

```python
self.scoring_llm = ChatOpenAI(
    model=settings.llm_scoring_model,
    base_url=settings.llm_scoring_base_url,
    api_key=settings.llm_scoring_api_key,
    streaming=False,
    timeout=15,
)
```

Injected into graph via `compile_graph(scoring_llm=self.scoring_llm)`.

### Data Model

#### ChatState (new field)

```python
scored_chunks: list[dict]  # [{"original": str, "source": str, "score": int, "compressed": str}, ...]
```

#### New SSE Event: `scoring`

```json
{
  "type": "scoring",
  "source": "student_manual",
  "index": 0,
  "score": 85,
  "compressed": "裁剪后保留的关键内容"
}
```

Frontend `ChatMessage` type gets a new role `"scoring"`.

### Graph Flow

```
START → routing_node
  ├─ (search_manual=true)  → manual_retrieval_node
  │     └─ (search_forum=true) → forum_retrieval_node
  │           └─ → scoring_node → answer_node → END
  └─ (search=false) → scoring_node (no-op) → answer_node → END
```

`scoring_node` receives all `manual_chunks` + `forum_chunks` (with source labels), iterates each chunk serially:

1. Call `scoring_llm` with prompt: user question + chunk
2. Parse JSON response: `{"score": int, "compressed": str}`
3. Emit SSE event `{"type":"scoring", ...}`
4. Collect into `scored_chunks` state

On LLM failure (timeout/parse error): score = 0, compressed = "".

After all chunks processed, emit a terminal event:
```json
{"type": "scoring", "source": "done", "done": true}
```

This signals the frontend that all chunks are scored, triggering the final re-sort.

### Scoring Prompt

```
你是一个校园助手的内容过滤器。你的任务：
1. 给你一段文本和一个用户问题
2. 判断文本是否与用户问题相关，打分 0-100
3. 裁剪掉完全无关的内容，保留与问题相关的部分
4. 如果文本中涉及日期等时间信息，务必保留
5. 如果整段文本与问题无关，打 0 分，压缩内容留空

输出必须是以下 JSON 格式，不要添加任何额外内容：
{"score": 85, "compressed": "保留的关键内容"}

用户问题：{user_question}
文本内容：{chunk}
```

### answer_node changes

Replace `manual_context` / `forum_context` construction to use `scored_chunks`:

```python
scored = state.get("scored_chunks", [])
if not scored:
    # fallback: use raw chunks (no search performed)
    manual_context = "\n\n".join(manual_chunks) or "（未检索到相关内容）"
    forum_context = "\n\n".join(forum_chunks) or "（未检索到相关内容）"
else:
    # use compressed content from scored chunks, truncated to 500 chars each
    manual_context = "\n\n".join(c["compressed"][:500] for c in scored if c["source"] == "学生手册" and c["score"] > 0 and c["compressed"])
    forum_context = "\n\n".join(c["compressed"][:500] for c in scored if c["source"] == "学校贴吧" and c["score"] > 0 and c["compressed"])
    if not manual_context:
        manual_context = "（未检索到相关内容）"
    if not forum_context:
        forum_context = "（未检索到相关内容）"
```

### Frontend Changes

#### SSE handling (useChat)
- Handle `type: "scoring"` events
- Find the corresponding retrieval message chunk by index + source
- Update its `score` and `compressed` fields
- After all chunks scored, trigger re-sort by score descending

#### RetrievalCard
- Show score badge for each chunk: `score: 85`
- Show pulsing "评分中..." while scoring in progress
- On `"scoring":{"done":true}` event, reorder chunks by score descending with CSS transition
- Click "详情" opens modal with compressed content (preferred over original)

#### Sorting Animation
- Use CSS `order` property: `style={{ order: -chunk.score }}`
- `transition-all duration-500` for smooth reorder

## SSE Event Sequence (full flow)

```
data: {"type":"status","node":"routing","label":"正在分析你的问题...","decision":{...}}
data: {"type":"retrieval","source":"school_forum","label":"已检索到【学校贴吧】相关讨论","chunks":[...]}
data: {"type":"scoring","source":"school_forum","index":0,"score":85,"compressed":"..."}
data: {"type":"scoring","source":"school_forum","index":1,"score":30,"compressed":"..."}
data: {"type":"scoring","source":"school_forum","index":2,"score":0,"compressed":""}
data: {"type":"scoring","source":"done","done":true}
data: {"type":"token","token":"最终回答..."}
data: {"type":"token","token":"","done":true}
```

## Files Changed

| File | Change |
|------|--------|
| `backend/app/core/settings.py` | Add `llm_scoring_*` fields |
| `backend/app/graph/graph.py` | Add `scoring_node`, `scored_chunks` state, update `should_retrieve` edge, update `answer_node` |
| `backend/app/graph/graph.py` | Update `compile_graph` to accept `scoring_llm` |
| `backend/app/services/chat_service.py` | Create `scoring_llm`, pass to `compile_graph` |
| `frontend/src/types/chat.ts` | Add `"scoring"` to `MessageRole`, update `SSEPayload` |
| `frontend/src/hooks/useChat.ts` | Handle `scoring` SSE event |
| `frontend/src/components/RetrievalCard.tsx` | Show score, sorting animation |
| `frontend/src/components/ChatMessage.tsx` | Optional: show scoring in retrieval section |

## Testing

### Backend
- `test_scoring_node_emits_scoring_events`: verify scoring node emits correct SSE events
- `test_scoring_node_scores_high_for_relevant_chunk`: mock LLM returns high score
- `test_scoring_node_scores_zero_for_irrelevant`: mock LLM returns low/zero score
- `test_scoring_node_fallback_on_llm_error`: verify graceful fallback
- `test_answer_node_uses_compressed_content`: verify answer_node uses `scored_chunks`
- `test_settings_scoring_config`: verify new env vars load correctly

### Frontend
- `RetrievalCard` tests: score display, sorting animation, "评分中" state
- `useChat` tests: scoring event handling, chunk update
