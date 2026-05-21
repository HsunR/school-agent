import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
import { QueueStatusBar } from "@/components/QueueStatusBar";
import type { QueueStatus } from "@/hooks/useQueueStatus";

describe("QueueStatusBar", () => {
  const idleStatus: QueueStatus = {
    busy: false,
    pending: 0,
    current_task: null,
    progress: 0,
    total: 0,
  };

  const busyStatus: QueueStatus = {
    busy: true,
    pending: 2,
    current_task: "manual.pdf",
    progress: 30,
    total: 50,
  };

  it("renders idle state", () => {
    render(<QueueStatusBar status={idleStatus} onClear={vi.fn()} />);
    expect(screen.getByText("队列空闲")).toBeDefined();
  });

  it("renders busy state with progress", () => {
    render(<QueueStatusBar status={busyStatus} onClear={vi.fn()} />);
    expect(screen.getByText("队列状态")).toBeDefined();
    expect(screen.getByText("处理中: manual.pdf")).toBeDefined();
    expect(screen.getByText("已完成 30/50 个分块 · 排队中: 2 个任务")).toBeDefined();
  });

  it("shows clear button in busy state", () => {
    render(<QueueStatusBar status={busyStatus} onClear={vi.fn()} />);
    expect(screen.getByText("终止清空队列")).toBeDefined();
  });

  it("calls onClear when clear button clicked", () => {
    const onClear = vi.fn();
    render(<QueueStatusBar status={busyStatus} onClear={onClear} />);
    fireEvent.click(screen.getByText("终止清空队列"));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("hides progress bar and clear button when idle", () => {
    render(<QueueStatusBar status={idleStatus} onClear={vi.fn()} />);
    expect(screen.queryByText("终止清空队列")).toBeNull();
    expect(screen.queryByText("处理中:")).toBeNull();
  });

  it("renders empty pending when 0", () => {
    const status: QueueStatus = {
      busy: true,
      pending: 0,
      current_task: "test.txt",
      progress: 5,
      total: 10,
    };
    render(<QueueStatusBar status={status} onClear={vi.fn()} />);
    expect(screen.getByText("已完成 5/10 个分块 · 排队中: 0 个任务")).toBeDefined();
  });

  it("renders without current_task name", () => {
    const status: QueueStatus = {
      busy: true,
      pending: 1,
      current_task: null,
      progress: 0,
      total: 0,
    };
    render(<QueueStatusBar status={status} onClear={vi.fn()} />);
    expect(screen.getByText("处理中: ...")).toBeDefined();
  });
});
