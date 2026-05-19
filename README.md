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
├── frontend/            # Next.js frontend application
│   └── web/            # Main web application
├── backend/            # FastAPI backend service
├── pnpm-workspace.yaml # pnpm workspace configuration
├── package.json        # Root package.json with workspace scripts
└── .env.example        # Environment variable template
```

## Getting Started

### Prerequisites

- Node.js >= 18
- pnpm >= 8
- Python >= 3.10

### Installation

```bash
# Install frontend dependencies
pnpm install

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### Development

```bash
# Run all workspace projects in dev mode
pnpm dev

# Or run frontend only
cd frontend/web && pnpm dev

# Run backend
cd backend && uvicorn main:app --reload
```

### Build

```bash
pnpm build
```

### Test

```bash
pnpm test
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```
