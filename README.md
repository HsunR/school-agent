# School Agent

AI-powered educational assistant platform that leverages Large Language Models to provide intelligent tutoring, homework assistance, and personalized learning experiences.

## Tech Stack

### Frontend
- **Framework**: Next.js
- **Styling**: Tailwind CSS
- **Language**: TypeScript

### Backend
- **Framework**: FastAPI
- **AI Framework**: LangChain & LangGraph
- **Language**: Python

## Project Structure

```
school-agent/
├── frontend/            # Next.js frontend application (port 3000)
├── backend/             # FastAPI backend service (port 8000)
├── pnpm-workspace.yaml  # pnpm workspace configuration
├── package.json         # Root package.json with workspace scripts
└── .env.example         # Environment variable template
```

## Getting Started

### Prerequisites

- Node.js >= 18
- pnpm >= 8
- Python >= 3.10

### Installation

```bash
# Frontend
cd frontend && pnpm install

# Backend
cd backend && pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template and set your API key
cp .env.example .env
# Edit .env: set DEEPSEEK_API_KEY=your_key_here
```

### Development (two terminals)

**Terminal 1 - Backend** (port 8000):
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend** (port 3000, proxies /api/* to backend):
```bash
cd frontend && pnpm dev
```

Open **http://localhost:3000** in your browser.

### Test

```bash
# Backend tests (65+ tests)
cd backend && pytest tests/ -v

# Frontend tests (75+ tests)
cd frontend && npx vitest run
```

### API Test (curl)

```bash
curl -N -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hello in **bold**"}]}'
```

## Project Structure

```
school-agent/
├── frontend/             # Next.js 16 + TypeScript + Tailwind
│   └── src/
│       ├── app/          # App Router (main page)
│       ├── components/   # ChatInput, ChatMessage, MarkdownRenderer
│       ├── hooks/        # useChat (SSE streaming hook)
│       └── types/        # TypeScript definitions
├── backend/              # FastAPI + LangChain + LangGraph
│   └── app/
│       ├── api/          # SSE chat endpoint
│       ├── core/         # Settings (pydantic-settings)
│       ├── schemas/      # Request/response Pydantic models
│       ├── services/     # ChatService (LLM integration)
│       └── graph/        # LangGraph StateGraph
├── docs/
│   └── api.md            # Full API contract
├── pnpm-workspace.yaml
├── package.json
└── .env.example

### Environment Setup

Copy `.env.example` to `.env` at the project root and fill in your DeepSeek API key:

```bash
cp .env.example .env
```

Edit `.env` and set `DEEPSEEK_API_KEY` to your actual key.

### Development

Start the backend (terminal 1):

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Start the frontend (terminal 2):

```bash
cd frontend && pnpm dev
```

The frontend runs on http://localhost:3000 and proxies `/api/*` requests to the backend at http://localhost:8000.

### Build

```bash
pnpm build
```

### Test

```bash
pnpm test
```

## Environment Variables

| Variable           | Description              | Default                      |
|--------------------|--------------------------|------------------------------|
| `DEEPSEEK_API_KEY` | DeepSeek API key         | —                            |
| `LLM_MODEL`        | LLM model name           | `deepseek-chat`              |
| `LLM_BASE_URL`     | LLM API base URL         | `https://api.deepseek.com/v1`|
