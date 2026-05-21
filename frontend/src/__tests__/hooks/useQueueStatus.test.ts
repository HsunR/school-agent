import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useQueueStatus } from "@/hooks/useQueueStatus";

describe("useQueueStatus", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches status on mount", () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        busy: false,
        pending: 0,
        current_task: null,
        progress: 0,
        total: 0,
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    renderHook(() => useQueueStatus());

    expect(mockFetch).toHaveBeenCalledWith("/api/admin/queue");
  });

  it("polls every 2 seconds", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        busy: true,
        pending: 1,
        current_task: "doc.txt",
        progress: 5,
        total: 50,
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    renderHook(() => useQueueStatus());

    // Initial fetch
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Advance 2 seconds
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("stops polling when queue becomes idle", async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          busy: true,
          pending: 1,
          current_task: "doc.txt",
          progress: 5,
          total: 50,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          busy: false,
          pending: 0,
          current_task: null,
          progress: 0,
          total: 0,
        }),
      });
    vi.stubGlobal("fetch", mockFetch);

    renderHook(() => useQueueStatus());

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    // After idle, no more fetches
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("provides clearQueue function", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", mockFetch);

    const { result } = renderHook(() => useQueueStatus());

    await act(async () => {
      await result.current.clearQueue();
    });

    expect(mockFetch).toHaveBeenCalledWith("/api/admin/queue/clear", {
      method: "POST",
    });
  });

  it("provides onIdle callback option", async () => {
    const onIdle = vi.fn();
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          busy: true,
          pending: 1,
          current_task: "doc.txt",
          progress: 10,
          total: 50,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          busy: false,
          pending: 0,
          current_task: null,
          progress: 0,
          total: 0,
        }),
      });
    vi.stubGlobal("fetch", mockFetch);

    renderHook(() => useQueueStatus({ onIdle }));

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(onIdle).toHaveBeenCalledTimes(1);
  });
});
