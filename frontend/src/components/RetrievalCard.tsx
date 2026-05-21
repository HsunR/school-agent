"use client";

import { useState } from "react";
import type { RetrievalPreview } from "@/types/chat";

interface RetrievalCardProps {
  chunks: RetrievalPreview[];
}

export default function RetrievalCard({ chunks }: RetrievalCardProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (chunks.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-400">
        无相关内容
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {chunks.map((chunk, i) => (
        <div key={i} className="overflow-hidden rounded-lg border border-gray-200">
          <button
            className="flex w-full items-center gap-2 bg-white px-3 py-2 text-left text-sm hover:bg-gray-50"
            onClick={() => setExpandedIndex(expandedIndex === i ? null : i)}
          >
            <span className="shrink-0 rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
              {chunk.source}
            </span>
            <span className="line-clamp-1 min-w-0 flex-1 text-gray-500">
              {chunk.preview.slice(0, 60)}...
            </span>
            <span className="shrink-0 text-xs text-blue-500">
              {expandedIndex === i ? "收起" : "详情"}
            </span>
          </button>
          {expandedIndex === i && (
            <div className="border-t border-gray-100 bg-gray-50 px-3 py-2 text-sm leading-relaxed text-gray-700">
              {chunk.preview}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
