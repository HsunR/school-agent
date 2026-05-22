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

  it("should allow messages over 1000 characters", async () => {
    const stream = createSSEStream('data: {"type":"token","token":"","done":true}\n\n');
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("a".repeat(1001));
    });

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
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

  it("should handle scoring events from multiple sources", async () => {
    const stream = createSSEStream(
      'data: {"type":"retrieval","source":"student_manual","label":"已检索到【学生手册】相关规定","chunks":[{"preview":"旷课处罚规定","source":"学生手册"},{"preview":"考试作弊处理","source":"学生手册"}]}\n\n',
      'data: {"type":"retrieval","source":"school_forum","label":"已检索到【学校贴吧】相关讨论","chunks":[{"preview":"宿舍管理费每学期500元","source":"学校贴吧"},{"preview":"食堂推荐窗口","source":"学校贴吧"}]}\n\n',
      'data: {"type":"scoring","source":"student_manual","index":0,"score":90,"compressed":"旷课处罚规定原文"}\n\n',
      'data: {"type":"scoring","source":"student_manual","index":1,"score":20,"compressed":"作弊"}\n\n',
      'data: {"type":"scoring","source":"school_forum","index":0,"score":85,"compressed":"宿舍管理费500元"}\n\n',
      'data: {"type":"scoring","source":"school_forum","index":1,"score":30,"compressed":"食堂"}\n\n',
      'data: {"type":"scoring","source":"done","done":true}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("旷课宿舍费");
    });

    const msgs = result.current.messages;
    const manualMsg = msgs.find((m) => m.role === "retrieval" && m.chunks?.[0]?.source === "学生手册");
    const forumMsg = msgs.find((m) => m.role === "retrieval" && m.chunks?.[0]?.source === "学校贴吧");
    expect(manualMsg).toBeDefined();
    expect(forumMsg).toBeDefined();
    // manual chunks
    expect(manualMsg!.chunks![0].score).toBe(90);
    expect(manualMsg!.chunks![0].compressed).toBe("旷课处罚规定原文");
    expect(manualMsg!.chunks![1].score).toBe(20);
    expect(manualMsg!.chunks![1].compressed).toBe("作弊");
    // forum chunks
    expect(forumMsg!.chunks![0].score).toBe(85);
    expect(forumMsg!.chunks![0].compressed).toBe("宿舍管理费500元");
    expect(forumMsg!.chunks![1].score).toBe(30);
    expect(forumMsg!.chunks![1].compressed).toBe("食堂");
  });

  it("should handle scoring events and update chunk scores", async () => {
    const stream = createSSEStream(
      'data: {"type":"retrieval","source":"school_forum","label":"已检索到【学校贴吧】相关讨论","chunks":[{"preview":"宿舍管理费每学期500元","source":"学校贴吧"},{"preview":"食堂推荐窗口","source":"学校贴吧"}]}\n\n',
      'data: {"type":"scoring","source":"school_forum","index":0,"score":85,"compressed":"宿舍管理费500元"}\n\n',
      'data: {"type":"scoring","source":"school_forum","index":1,"score":30,"compressed":"食堂"}\n\n',
      'data: {"type":"scoring","source":"done","done":true}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      body: stream,
    });

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("宿舍管理费");
    });

    const msgs = result.current.messages;
    const retrievalMsg = msgs.find((m) => m.role === "retrieval");
    expect(retrievalMsg).toBeDefined();
    expect(retrievalMsg!.chunks![0].score).toBe(85);
    expect(retrievalMsg!.chunks![0].compressed).toBe("宿舍管理费500元");
    expect(retrievalMsg!.chunks![1].score).toBe(30);
    expect(retrievalMsg!.chunks![1].compressed).toBe("食堂");
  });

  it("should handle intent event and display optimized query", async () => {
    const stream = createSSEStream(
      'data: {"type":"intent","optimized_query":"优化后的问题","compressed_context":"上下文摘要","label":"正在理解你的问题..."}\n\n',
      'data: {"type":"token","token":"","done":true}\n\n',
    );
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true, body: stream,
    });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.sendMessage("原始问题");
    });
    const intentMsg = result.current.messages.find((m) => m.role === "intent");
    expect(intentMsg).toBeDefined();
    expect(intentMsg!.optimizedQuery).toBe("优化后的问题");
  });

  it("should only send last 3 turns of history", async () => {
    const stream = createSSEStream('data: {"type":"token","token":"","done":true}\n\n');
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true, body: stream,
    });
    const { result } = renderHook(() => useChat());
    // Send 4 messages to build 4 turns of history
    for (let i = 0; i < 4; i++) {
      (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true, body: stream,
      });
      await act(async () => {
        await result.current.sendMessage(`msg${i}`);
      });
    }
    // Verify last request only has 3 turns = 6 messages
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    const lastCall = calls[calls.length - 1];
    const body = JSON.parse(lastCall[1].body);
    expect(body.messages.length).toBe(6);
  });
});
