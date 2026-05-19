# School Agent API Contract

> Version: 0.1.0
> Base URL: `http://localhost:8000`

## Overview

The School Agent API provides a single chat endpoint that accepts conversational messages and streams responses token-by-token via Server-Sent Events (SSE). It is compatible with OpenAI API-style LLM providers (default: DeepSeek).

## Endpoints

### `POST /api/chat` — Chat Completion

Main chat endpoint. Accepts a conversation history and returns a streaming SSE response.

#### Request

```
POST /api/chat
Content-Type: application/json
```

**Request Body (JSON):**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Explain Newton's first law of motion."
    }
  ],
  "stream": true
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | `array` | ✅ | Array of message objects representing the conversation history |
| `stream` | `boolean` | ❌ | Must be `true`. Non-streaming mode is not supported. Defaults to `true`. |

**Message Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | `string` | ✅ | One of: `"user"`, `"assistant"`, `"system"` |
| `content` | `string` | ✅ | Message text. Maximum **1000 characters**. |

**Constraints:**

- `messages` array must contain **at least 1 message**.
- Each message `content` must be **non-empty** and **≤ 1000 characters**.
- `stream` must be `true` (default).

#### Response (Success — 200)

Content-Type: `text/event-stream`

The response is a Server-Sent Events (SSE) stream. The client reads the stream as a sequence of `data:` lines terminated by `\n\n`.

**Stream Format:**

```
data: {"token": "Newton", "done": false}\n\n
data: {"token": "'s", "done": false}\n\n
data: {"token": " first", "done": false}\n\n
data: {"token": " law", "done": false}\n\n
data: {"token": " states", "done": false}\n\n
data: {"token": " that", "done": false}\n\n
data: {"token": " ...", "done": false}\n\n
data: {"token": "", "done": true}\n\n
```

**Chunk Object:**

| Field | Type | Description |
|-------|------|-------------|
| `token` | `string` | A single token or word from the LLM response. Empty string in the final/error chunk. |
| `done` | `boolean` | `false` for intermediate tokens, `true` for the final chunk or an error chunk. |
| `error` | `string` | Present only in error chunks. Contains a human-readable error message. |

**Chunk Types:**

- **Token chunk** (intermediate): `{"token": "<partial response>", "done": false}`
- **Final chunk** (end of stream): `{"token": "", "done": true}`
- **Error chunk** (stream abort): `{"error": "<error message>", "done": true}`

#### Error Responses

##### `400 Bad Request` — Validation Error

Returned when the request payload is malformed or violates constraints.

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "messages", 0, "content"],
      "msg": "String should have at most 1000 characters",
      "input": "..."
    }
  ]
}
```

**Triggered when:**
- `messages` array is empty
- A message `content` is empty string
- A message `content` exceeds 1000 characters
- `role` is not one of `"user"`, `"assistant"`, `"system"`
- Request body is not valid JSON

##### `422 Unprocessable Entity` — LLM/Provider Error

Returned when the LLM provider cannot fulfill the request.

```json
{
  "detail": {
    "error": "Invalid API key",
    "type": "authentication_error"
  }
}
```

**Triggered when:**
- API key is invalid, missing, or expired
- Requested model is unavailable or not found
- Provider rate limit is exceeded
- Provider returns a non-retryable error

##### `500 Internal Server Error`

Returned for unexpected server-side failures.

```json
{
  "detail": "Internal server error"
}
```

**Triggered when:**
- Unhandled exception during request processing
- Network timeout connecting to LLM provider
- Unexpected provider response format

## Client Integration Guide

### SSE Stream Consumption Pattern

The SSE endpoint uses `POST` with `fetch()` and `ReadableStream`. The standard `EventSource` API (which only supports `GET`) **cannot** be used.

**Required client behavior:**

1. Send a `POST` request with `fetch()`
2. Read the response body as a `ReadableStream`
3. Parse each `data: ...\n\n` line as it arrives
4. Handle connection errors gracefully (retry with exponential backoff)

### Example Flow

```
Client                          Server                          LLM Provider
  │                               │                                │
  │── POST /api/chat ────────────►│                                │
  │    {messages: [...],          │                                │
  │     stream: true}             │                                │
  │                               │── LLM API call ──────────────►│
  │                               │◄─ streamed tokens ────────────│
  │◄── data: {"token":"A","done":false} ──────────────────────────│
  │◄── data: {"token":"B","done":false} ──────────────────────────│
  │◄── data: {"token":"C","done":false} ──────────────────────────│
  │◄── data: {"token":"","done":true} ────────────────────────────│
```

## Multi-turn Conversation

The API is **stateless**. Each request must include the **full message history** so the LLM has context.

**Example — second turn:**

```json
{
  "messages": [
    {"role": "user", "content": "Explain Newton's first law."},
    {"role": "assistant", "content": "Newton's first law states that an object at rest stays at rest..."},
    {"role": "user", "content": "Can you give me a real-world example?"}
  ],
  "stream": true
}
```

## Environment Variables

The API relies on the following environment variables to configure the LLM provider:

| Variable | Description |
|----------|-------------|
| `DEEPSEEK_API_KEY` | API key for DeepSeek (or compatible provider) |
| `LLM_MODEL` | Model identifier (default: `deepseek-chat`) |
| `LLM_BASE_URL` | Base URL for the OpenAI-compatible API (default: `https://api.deepseek.com/v1`) |

## CORS

CORS is configured to allow all origins (`*`) for local development.

## Error Handling Strategy

| Error | Status | Recovery |
|-------|--------|----------|
| Empty request body | 400 | Fix payload |
| Content > 1000 chars | 400 | Truncate or split input |
| Invalid messages format | 400 | Fix role/format |
| Invalid/missing API key | 422 | Configure `.env` |
| Model unavailable | 422 | Check `LLM_MODEL` |
| Rate limited | 422 | Wait and retry |
| Network error (SSE) | N/A | Client retry with backoff |
| Internal error | 500 | Contact admin |
