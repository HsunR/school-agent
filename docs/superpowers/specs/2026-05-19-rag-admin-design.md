# RAG Admin System — Design Spec

## Overview

Add a knowledge base management system to the existing school assistant chatbot. Users can upload student handbooks and school forum data, each stored in separate ChromaDB collections. The LangGraph pipeline is extended with routing and retrieval nodes, each configurable with independent LLM models via `.env`.

---

## 1. Architecture

```
frontend/src/app/
├── (chat)/              ← existing chat UI
└── admin/               ← knowledge base management
    ├── page.tsx          upload / stats overview
    └── preview/          data preview & delete

backend/app/
├── api/
│   ├── chat.py           ← existing
│   └── admin.py          ← NEW: upload / stats / preview / delete
├── graph/
│   └── graph.py          ← MODIFIED: multi-node LangGraph
├── rag/
│   ├── chroma_manager.py ← NEW: ChromaDB wrapper (dedup, CRUD)
│   └── embeddings.py     ← NEW: embedding client (OpenAI-compatible)
├── core/
│   └── settings.py       ← MODIFIED: per-node model config
├── schemas/
│   ├── chat.py           ← existing
│   └── admin.py          ← NEW: admin request/response models
└── services/
    ├── chat_service.py   ← MODIFIED: uses new graph
    └── admin_service.py  ← NEW: upload / dedup / clear logic
```

---

## 2. LangGraph Pipeline

```
User Input
    │
    ▼
┌──────────────────────────────┐
│       routing_node           │
│ 独立判断两个问题：             │
│ ① 需要查学生手册？→ manual   │
│ ② 需要查贴吧？    → forum    │
│ model: LLM_ROUTING_*         │
└──────┬───────────┬───────────┘
       │           │
   manual      forum
       │           │
       ▼           ▼
┌──────────┐ ┌──────────┐
│ manual_  │ │ forum_   │
│ retrieval│ │ retrieval│
│ _node    │ │ _node    │
│ ChromaDB │ │ ChromaDB │
│ "student_│ │ "school_ │
│  manual" │ │  forum"  │
│ top_k=3  │ │ top_k=3  │
└─────┬────┘ └─────┬────┘
       │           │
       └─────┬─────┘
             │
             ▼
┌──────────────────────────────┐
│        chat_node             │
│ 结合检索结果回答用户问题       │
│ model: LLM_CHAT_*            │
└──────────────────────────────┘
```

### Node Details

**routing_node**: Takes user question, outputs `{search_manual: bool, search_forum: bool}`. Uses a lightweight prompt to classify whether each knowledge base is relevant.

**manual_retrieval_node**: Only executes if `search_manual=true`. Queries ChromaDB collection `student_manual`, returns top-K text chunks.

**forum_retrieval_node**: Only executes if `search_forum=true`. Queries ChromaDB collection `school_forum`, returns top-K text chunks.

### Streaming Separation

**chat generation is NOT part of the graph.** The graph handles routing + retrieval (sync, no streaming needed). After the graph completes, the service layer (`chat_service.py`) takes the retrieved context and calls `llm.astream()` directly for the final answer — preserving the per-token SSE streaming already established in the current codebase.

```
Service flow:
  graph.run(messages)        →  routing + retrieval (sync)
  llm.astream(context)       →  per-token answer (async, SSE)
```

This avoids the sync `invoke()` buffering problem that was fixed previously.

---

## 3. Admin API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admin/upload` | Upload text, split by delimiter, dedup via hash, store to ChromaDB |
| GET | `/api/admin/data?category=xxx&page=1&size=20` | Paginated preview of stored chunks |
| DELETE | `/api/admin/data?category=xxx` | Clear data (omit category → clear all) |
| GET | `/api/admin/stats` | Overview: total chunks per category, last update time |

### Upload Flow

```
POST /api/admin/upload
{
  "content": "...",           // raw text
  "category": "student_manual" | "school_forum",
  "delimiter": "*****SPILIT_BY_HUSNR*****"
}
```

1. Split `content` by `delimiter` → chunks
2. For each chunk: compute SHA256 hash
3. Check hash against existing hashes in ChromaDB metadata
4. New chunks → embed + store; existing chunks → skip
5. Return: `{ inserted: n, skipped: m, total: k }`

---

## 4. Environment Configuration (`settings.py`)

```python
class Settings(BaseSettings):
    # ── Chat Node ──
    llm_chat_model: str = "deepseek-chat"
    llm_chat_base_url: str = "https://api.deepseek.com/v1"
    llm_chat_api_key: str = ""

    # ── Routing Node ──
    llm_routing_model: str = "deepseek-chat"
    llm_routing_base_url: str = "https://api.deepseek.com/v1"
    llm_routing_api_key: str = ""

    # ── Embedding (RAG, unified) ──
    llm_embedding_model: str = "text-embedding-ada-002"
    llm_embedding_base_url: str = "https://api.deepseek.com/v1"
    llm_embedding_api_key: str = ""

    # ── ChromaDB ──
    chroma_persist_dir: str = "./chroma_db"
    rag_top_k: int = 3
```

Corresponding `.env.example`:

```env
# Chat Node
LLM_CHAT_MODEL=deepseek-chat
LLM_CHAT_BASE_URL=https://api.deepseek.com/v1
LLM_CHAT_API_KEY=sk-your-key

# Routing Node
LLM_ROUTING_MODEL=deepseek-chat
LLM_ROUTING_BASE_URL=https://api.deepseek.com/v1
LLM_ROUTING_API_KEY=sk-your-key

# Embedding (OpenAI-compatible API)
LLM_EMBEDDING_MODEL=text-embedding-ada-002
LLM_EMBEDDING_BASE_URL=https://api.deepseek.com/v1
LLM_EMBEDDING_API_KEY=sk-your-key

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
RAG_TOP_K=3
```

**Developer configs** (hardcoded, not exposed to .env):
- System prompts for each node
- Chunk dedup strategy (SHA256)
- Similarity search threshold
- Internal LangGraph wiring

---

## 5. ChromaDB Schema

Two collections:
- `student_manual` — student handbook chunks
- `school_forum` — school forum/bbs chunks

Each document stores:
```python
{
    "id": "sha256_hash_of_content",
    "text": "chunk content",
    "metadata": {
        "category": "student_manual" | "school_forum",
        "hash": "sha256_hash",
        "created_at": "iso_timestamp"
    }
}
```

Dedup: before inserting, query by `hash` in metadata filter. If exists → skip.

---

## 6. Admin Frontend (`/admin`)

Three sections on a single page:

**Upload Section**
- Textarea for content input
- Category selector dropdown (学生手册 / 学校贴吧)
- Delimiter input (default: `*****SPILIT_BY_HUSNR*****`)
- Upload button
- Result feedback (inserted/skipped counts)

**Stats Overview**
- Per-category: total chunks count, last update time
- "Clear All" button with confirmation dialog

**Data Preview**
- Paginated table: content (truncated), category badge, hash, timestamp
- Filter by category
- Pagination controls

---

## 7. Dependencies to Add

```txt
# requirements.txt additions
chromadb>=1.10.0
```

---

## 8. Error Handling

- Upload: validate content not empty, delimiter not empty
- ChromaDB: persist errors return 500 with descriptive message
- Retrieval: if ChromaDB returns empty, chat_node answers without context
- Routing: if LLM call fails, default to `search_manual=false, search_forum=false` (fail-safe)
