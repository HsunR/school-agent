"use client";

import { useState, useMemo } from "react";
import type { RetrievalPreview, SelectedChunk } from "@/types/chat";
import DetailModal from "@/components/DetailModal";

interface RetrievalCardProps {
  chunks: RetrievalPreview[];
  selectedChunks?: SelectedChunk[];
}

function isSelected(chunk: RetrievalPreview, selected: SelectedChunk[]): boolean {
  return selected.some((s) => s.source === chunk.source && chunk.preview.startsWith(s.preview));
}

export default function RetrievalCard({ chunks, selectedChunks = [] }: RetrievalCardProps) {
  const [modalIndex, setModalIndex] = useState<number | null>(null);

  const allScored = chunks.every((c) => c.score !== undefined);
  const sorted = useMemo(() => {
    if (!allScored) return chunks;
    return [...chunks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  }, [chunks, allScored]);

  if (chunks.length === 0) {
    return (
      <div className="rounded-xl bg-bg-soft px-4 py-3 text-sm text-text-tertiary shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
        无相关内容
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((chunk, i) => {
        const selected = isSelected(chunk, selectedChunks);
        return (
          <div
            key={i}
            className={`rounded-xl bg-bg-soft px-[18px] py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] ${
              selected ? "border-l-4 border-green-500" : ""
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className="shrink-0 rounded bg-brand-light px-1.5 py-0.5 text-xs font-medium text-brand">
                {chunk.source}
              </span>
              {chunk.score !== undefined ? (
                <span className="shrink-0 text-xs font-semibold text-brand">
                  score: {chunk.score}
                </span>
              ) : (
                <span className="shrink-0 animate-pulse text-xs text-text-tertiary">
                  评分中...
                </span>
              )}
              {selected && (
                <span className="ml-auto shrink-0 text-xs font-medium text-green-600">
                  ✓ 已用于回答
                </span>
              )}
            </div>
            <div className="mt-2 text-sm leading-relaxed text-text-body line-clamp-1">
              {chunk.preview.slice(0, 60)}...
            </div>
            <div className="mt-2">
              {chunk.score !== undefined && (
                <button
                  onClick={() => setModalIndex(i)}
                  className="text-xs font-medium text-brand hover:text-orange-700"
                >
                  详情 →
                </button>
              )}
            </div>
          </div>
        );
      })}
      {modalIndex !== null && (
        <DetailModal
          content={sorted[modalIndex].preview}
          source={sorted[modalIndex].source}
          onClose={() => setModalIndex(null)}
        />
      )}
    </div>
  );
}
