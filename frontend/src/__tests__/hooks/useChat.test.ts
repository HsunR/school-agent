import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useChat } from "@/hooks/useChat";

function createSSEStream(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe("useChat", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn();
  });

  it("should POST messages to /api/chat when sendMessage is called", async () => {
    const stream = createSSEStream('data: {"type":"token","token":"","done":true}\n\n');
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );

    const body = JSON.parse(
      (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
    );
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0].role).toBe("user");
    expect(body.messages[0].content).toBe("Hello");
    expect(body.stream).toBe(true);
  });

  it("should accumulate streaming tokens in the assistant message", async () => {
    const stream = createSSEStream(
      'data: {"type":"token","token":"Hello","done":false}\n\n',
      'data: {"type":"token","token":" World","done":false}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hi");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("Hi");
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toBe("Hello World");
  });

  it("should set isStreaming to false when done is received", async () => {
    const stream = createSSEStream(
      'data: {"type":"token","token":"Hi","done":false}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hey");
    });

    expect(result.current.messages[1].isStreaming).toBe(false);
  });

  it("should reject empty messages", async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("");
    });

    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("should reject messages over 1000 characters", async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("a".repeat(1001));
    });

    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("should set error state when fetch fails", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Network error"),
    );

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(result.current.error).toBe("Network error");
  });

  it("should prevent sending while isLoading", () => {
    // Use a deferred promise that never resolves to keep isLoading true
    let resolveFetch!: (value: unknown) => void;
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );

    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.sendMessage("First");
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.sendMessage("Second");
    });

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);

    // Resolve the deferred promise to clean up
    const stream = createSSEStream('data: {"type":"token","token":"","done":true}\n\n');
    act(() => {
      resolveFetch({ ok: true, body: stream });
    });
  });

  it("should clear messages with clearMessages", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
  });

  it("should clear error with clearError", () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it("should reject whitespace-only messages", async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(result.current.error).toBe("Message cannot be empty");
  });

  it("should handle HTTP error responses", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 429,
      statusText: "Too Many Requests",
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(result.current.error).toBe("HTTP 429: Too Many Requests");
    expect(result.current.isLoading).toBe(false);
  });

  it("should recover after fetch failure and retry successfully", async () => {
    // First call fails
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Network error"),
    );

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(result.current.error).toBe("Network error");
    expect(result.current.isLoading).toBe(false);

    // Second call succeeds
    const stream = createSSEStream(
      'data: {"type":"token","token":"Recovered","done":false}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    await act(async () => {
      await result.current.sendMessage("Retry");
    });

    // 2 messages from failed attempt + 2 from retry = 4 total
    expect(result.current.messages).toHaveLength(4);
    // Last assistant message should have recovered content
    expect(result.current.messages[3].content).toBe("Recovered");
    expect(result.current.error).toBeNull();
  });

  it("should handle multiple sequential messages", async () => {
    const stream1 = createSSEStream(
      'data: {"type":"token","token":"First reply","done":false}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    const stream2 = createSSEStream(
      'data: {"type":"token","token":"Second reply","done":false}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );

    (globalThis.fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, body: stream1 })
      .mockResolvedValueOnce({ ok: true, body: stream2 });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("First");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].content).toBe("First");
    expect(result.current.messages[1].content).toBe("First reply");

    await act(async () => {
      await result.current.sendMessage("Second");
    });

    expect(result.current.messages).toHaveLength(4);
    expect(result.current.messages[2].content).toBe("Second");
    expect(result.current.messages[3].content).toBe("Second reply");
  });

  it("should handle SSE streaming payload error", async () => {
    const stream = createSSEStream(
      'data: {"type":"error","error":"API quota exceeded","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hello");
    });

    expect(result.current.error).toBe("API quota exceeded");
    expect(result.current.isLoading).toBe(false);
  });
});
