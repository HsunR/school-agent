"use client";

import { useState, useMemo } from "react";
import type { RetrievalPreview } from "@/types/chat";
import DetailModal from "@/components/DetailModal";

interface RetrievalCardProps {
  chunks: RetrievalPreview[];
}

export default function RetrievalCard({ chunks }: RetrievalCardProps) {
  const [modalIndex, setModalIndex] = useState<number | null>(null);

  const allScored = chunks.every((c) => c.score !== undefined);
  const sorted = useMemo(() => {
    if (!allScored) return chunks;
    return [...chunks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  }, [chunks, allScored]);

  if (chunks.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-400">
        无相关内容
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sorted.map((chunk, i) => (
        <div
          key={i}
          className="overflow-hidden rounded-lg border border-gray-200 transition-all duration-500"
        >
          <div className="flex w-full items-center gap-2 bg-white px-3 py-2 text-left text-sm">
            <span className="shrink-0 rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium text-green-700">
              {chunk.source}
            </span>
            {chunk.score !== undefined ? (
              <span className="shrink-0 text-xs font-semibold text-blue-600">
                score: {chunk.score}
              </span>
            ) : (
              <span className="shrink-0 animate-pulse text-xs text-gray-400">
                评分中...
              </span>
            )}
            <span className="line-clamp-1 min-w-0 flex-1 text-gray-500">
              {chunk.preview.slice(0, 60)}...
            </span>
            {chunk.score !== undefined && (
              <button
                onClick={() => setModalIndex(i)}
                className="shrink-0 text-xs text-blue-500 hover:text-blue-700"
              >
                详情
              </button>
            )}
          </div>
        </div>
      ))}
      {modalIndex !== null && (
        <DetailModal
          content={sorted[modalIndex].compressed || sorted[modalIndex].preview}
          source={sorted[modalIndex].source}
          onClose={() => setModalIndex(null)}
        />
      )}
    </div>
  );
}
