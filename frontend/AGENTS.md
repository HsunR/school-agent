# FRONTEND KNOWLEDGE BASE

**Generated:** 2026-05-20

**⚠️ This is NOT the Next.js you know.** Next.js 16.x has breaking changes. Read `node_modules/next/dist/docs/` before writing code.

## OVERVIEW
Next.js 16.2.6 + TypeScript (strict) + React 19 + Tailwind CSS v4. SSE streaming chat UI. App Router.

## STRUCTURE
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout (html/body + globals.css)
│   │   ├── page.tsx            # / — main chat interface ("use client")
│   │   ├── admin/page.tsx      # /admin — knowledge base management
│   │   └── api/chat/route.ts   # BFF proxy to backend (port 8000)
│   ├── components/
│   │   ├── ChatInput.tsx       # Message input with loading state
│   │   ├── ChatMessage.tsx     # Renders user/assistant bubbles
│   │   └── MarkdownRenderer.tsx# react-markdown + remark-gfm
│   ├── hooks/
│   │   └── useChat.ts          # SSE streaming via fetch() + ReadableStream
│   ├── types/
│   │   └── chat.ts             # ChatMessage, SSEPayload interfaces
│   └── __tests__/              # Vitest tests (co-located by src structure)
├── next.config.ts              # Rewrites /api/* → localhost:8000/api/*
├── vitest.config.ts            # jsdom env, @/ alias, @vitejs/plugin-react
├── eslint.config.mjs           # Flat config v9: next/core-web-vitals + typescript
├── postcss.config.mjs          # @tailwindcss/postcss (Tailwind v4)
└── package.json                # Scripts: dev (--webpack), build, start, test
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| Chat UI entry | `src/app/page.tsx` | Uses useChat hook, renders ChatInput + ChatMessage |
| Admin KB page | `src/app/admin/page.tsx` | File upload + data preview interface |
| SSE consumer | `src/hooks/useChat.ts` | Full client state: messages, loading, error |
| Message input | `src/components/ChatInput.tsx` | 1000-char limit, empty validation |
| Message bubble | `src/components/ChatMessage.tsx` | Markdown rendering, streaming indicator |
| Markdown | `src/components/MarkdownRenderer.tsx` | react-markdown + remark-gfm |
| API route handler | `src/app/api/chat/route.ts` | POST proxy to backend (ReadableStream pipe) |
| Chat types | `src/types/chat.ts` | ChatMessage interface, SSEPayload type |
| Tests | `src/__tests__/` | Vitest, @testing-library/react, jsdom |

## CONVENTIONS (frontend-specific)
- **"use client"**: Required on all interactive components (hooks, event handlers, state)
- **@/ alias**: Maps to `./src/` in both TypeScript (`tsconfig.json`) and Vitest (`vitest.config.ts`)
- **Tailwind v4**: CSS-based config via `@theme inline {}` in `globals.css`. No `tailwind.config.js`
- **SSE consumption**: `fetch()` + `ReadableStream.getReader()` + `TextDecoder`. NOT `EventSource` (POST-based SSE)
- **Imports order**: directive → React → third-party → `@/` internal → CSS
- **Components**: PascalCase files, default export, inline prop interface
- **Test structure**: `__tests__/` mirrors `src/` layout. `*.test.ts`/`*.test.tsx`
- **Error handling**: `catch (err: unknown)` with `instanceof` check
- **No Prettier / no .editorconfig**: Formatting via IDE defaults + ESLint only

## ANTI-PATTERNS
- `as any` / `@ts-ignore` / `@ts-expect-error` — NEVER allowed
- Importing with relative paths `../../` — use `@/` alias
- Using `EventSource` for SSE — must use `fetch()` + `ReadableStream` (POST-based)
- Using `any` type — always prefer `unknown` with type narrowing
