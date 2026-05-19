## Task 11 - Page Integration

- `scrollIntoView` is not available in jsdom - must mock it in setup.ts: `Element.prototype.scrollIntoView = vi.fn()`
- `vi` needs to be imported in setup files (not globally available like in test files): `import { vi } from "vitest"`
- For full-viewport layouts in Tailwind: html gets `h-full`, body gets `h-full flex flex-col`
- Tailwind v4 uses `@import "tailwindcss"` instead of `@tailwind base/components/utilities`

## Task 12 - Backend Test Suite (pytest)

- `AsyncMock` wraps return values in a coroutine — cannot use `return_value` for objects that need `async for` (async generators)
- Workaround: replace `stream_chat` with a plain callable (lambda) that returns the async generator directly: `mock.stream_chat = lambda msgs: async_gen(tokens)`
- For exception tests with async generators: define an `async def` with `yield` and `raise` before yield
- `pytest.mark.asyncio` is needed even for tests using `pytest-asyncio` with `asyncio_mode = "auto"` when the test is a method of a class (class-based tests don't auto-detect)
- `conftest.py` fixtures are auto-discovered — no imports needed in test files
- `httpx.ASGITransport` enables FastAPI testing without a running server
