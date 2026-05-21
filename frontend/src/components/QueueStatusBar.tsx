/* ── Admin queue status bar component ── */

"use client";

import type { QueueStatus } from "@/hooks/useQueueStatus";

interface QueueStatusBarProps {
  status: QueueStatus;
  onClear: () => void;
}

export function QueueStatusBar({ status, onClear }: QueueStatusBarProps) {
  const { busy, pending, current_task, progress, total } = status;
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;

  if (!busy && pending === 0) {
    return (
      <div className="mb-4 flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
        <span className="flex h-2 w-2 rounded-full bg-green-500" />
        队列空闲
      </div>
    );
  }

  return (
    <div className="mb-4 overflow-hidden rounded-xl border border-blue-200 bg-blue-50 shadow-sm">
      <div className="px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-blue-800">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            队列状态
          </div>
          <button
            onClick={onClear}
            className="rounded-lg border border-red-200 bg-white px-3 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-50"
          >
            终止清空队列
          </button>
        </div>
        <div className="mb-1.5 flex items-center justify-between text-xs text-blue-600">
          <span>处理中: {current_task ?? "..."}</span>
          <span>
            已完成 {progress}/{total} 个分块 · 排队中: {pending} 个任务
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-blue-200">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
