"use client";

import { useEffect, useCallback } from "react";

interface DetailModalProps {
  content: string;
  source: string;
  onClose: () => void;
}

export default function DetailModal({ content, source, onClose }: DetailModalProps) {
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
          <span className="rounded bg-brand-light px-2 py-1 text-xs font-medium text-brand">
            {source}
          </span>
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-sm text-text-tertiary transition-colors hover:bg-bg-soft hover:text-text-secondary"
            aria-label="Close"
          >
            关闭
          </button>
        </div>

        <div className="whitespace-pre-wrap text-sm leading-relaxed text-text-body">
          {content}
        </div>
      </div>
    </div>
  );
}
