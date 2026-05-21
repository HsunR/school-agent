"use client";

import { useEffect, useCallback } from "react";

interface DetailModalProps {
  content: string;
  original?: string;
  source: string;
  onClose: () => void;
}

export default function DetailModal({ content, original, source, onClose }: DetailModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const hasExtracted = original !== undefined && content !== original;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <span className="rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-700">
            {source}
          </span>
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            aria-label="Close"
          >
            关闭
          </button>
        </div>

        {hasExtracted && (
          <div className="mb-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-600">
              提取后内容
            </h3>
            <div className="whitespace-pre-wrap rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-sm leading-relaxed text-gray-700">
              {content}
            </div>
          </div>
        )}

        <div>
          {hasExtracted && (
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              原文
            </h3>
          )}
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
            {hasExtracted ? original : content}
          </div>
        </div>
      </div>
    </div>
  );
}
