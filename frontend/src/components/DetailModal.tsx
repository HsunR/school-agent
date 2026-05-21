"use client";

import { useEffect, useCallback, useState } from "react";

interface DetailModalProps {
  content: string;
  original?: string;
  source: string;
  onClose: () => void;
}

export default function DetailModal({ content, original, source, onClose }: DetailModalProps) {
  const [tab, setTab] = useState<"compressed" | "original">("compressed");
  const hasBoth = original && original !== content;

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

        {hasBoth && (
          <div className="mb-3 flex gap-2 border-b border-gray-200 pb-2">
            <button
              onClick={() => setTab("compressed")}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                tab === "compressed"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              提取后
            </button>
            <button
              onClick={() => setTab("original")}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                tab === "original"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              原文
            </button>
          </div>
        )}

        {tab === "compressed" ? (
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
            {content}
          </div>
        ) : (
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-500">
            {original}
          </div>
        )}
      </div>
    </div>
  );
}
