## Task 12 - Backend Test Suite

- `AsyncMock.return_value` cannot be used for async generators — AsyncMock wraps return values in coroutines, breaking `async for`. Use plain callables instead.
- `AsyncMock.side_effect` with Exception classes also returns a coroutine, causing TypeError before the exception is raised. Define async generator functions for exception testing.