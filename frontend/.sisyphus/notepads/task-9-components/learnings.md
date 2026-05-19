# Task 9 — Learnings

## Patterns
- `@testing-library/react` auto-cleanup is NOT enabled by default in Vitest. Must import `cleanup` and call it in `afterEach()` for each test file.
- `@testing-library/user-event` is a separate package not included with `@testing-library/react`. Added as devDependency.
- Tailwind v4 uses `@theme inline` directive for design tokens.
- Project uses Geist Sans + Geist Mono fonts via next/font/google.
- Vitest config has `@/` alias mapped to `./src` via vite resolve.alias.
- `@testing-library/jest-dom/vitest` is the correct import path for Vitest v4.

## ChatInput Component
- Auto-resizing textarea via `textareaRef` — reset to `auto` height then set to `scrollHeight`.
- Enter to send, Shift+Enter for newline — handled in `onKeyDown`.
- Char counter uses `toLocaleString()` for number formatting.
- Send button is an icon (paper plane SVG from Heroicons).
- `maxLength` set to 1100 (1000 + 100 buffer) to prevent insane input lengths.
- Character count turns red when over limit.

## ChatMessage Component
- `justify-end`/`justify-start` on flex container for alignment.
- User messages: `bg-blue-500 text-white`, Assistant: `bg-gray-100 text-gray-900`.
- AI messages rendered via `MarkdownRenderer` (react-markdown + remark-gfm).
- Streaming cursor: `animate-pulse` with `rounded-sm bg-gray-500`.
- Timestamp via `toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })`.
- Use `data-testid` attributes for stable test selectors.
