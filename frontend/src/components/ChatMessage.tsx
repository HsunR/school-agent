"use client";

import { useState } from "react";
import type { ChatMessage as ChatMessageType, SelectedChunk } from "@/types/chat";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import RetrievalCard from "@/components/RetrievalCard";

interface ChatMessageProps {
  message: ChatMessageType;
  selectedChunks?: SelectedChunk[];
}

function BentoCard({
  children,
  className = "",
  bg = "bg-bg-card",
  padding = "p-6",
}: {
  children: React.ReactNode;
  className?: string;
  bg?: string;
  padding?: string;
}) {
  return (
    <div className={`rounded-2xl ${bg} ${padding} ${className}`}>
      {children}
    </div>
  );
}

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-bg-soft px-4 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
      {children}
    </div>
  );
}

function Heading({
  dotColor,
  children,
}: {
  dotColor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <div className={`h-2.5 w-2.5 rounded-full ${dotColor}`} />
      <span className="font-display text-base font-semibold text-black">
        {children}
      </span>
    </div>
  );
}

export default function ChatMessage({ message, selectedChunks = [] }: ChatMessageProps) {
  const isUser = message.role === "user";
  const timestamp = new Date(message.timestamp).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  if (message.role === "status") {
    return (
      <div data-testid="chat-message">
        <BentoCard className="flex flex-col gap-3">
          <Heading dotColor="bg-brand">
            {message.node === "routing" ? "系统分析" : "系统"}
          </Heading>
          <SectionCard>
            <div className="text-sm leading-relaxed text-text-body">
              {message.content}
            </div>
            {message.decision && (
              <div className="mt-1.5 text-xs text-text-tertiary">
                {message.decision.search_manual && "📖 需要查学生手册 "}
                {message.decision.search_forum && "💬 需要查学校贴吧 "}
                {!message.decision.search_manual &&
                  !message.decision.search_forum &&
                  "无需检索，直接回答"}
              </div>
            )}
          </SectionCard>
        </BentoCard>
      </div>
    );
  }

  if (message.role === "intent") {
    return (
      <div data-testid="chat-message">
        <BentoCard className="flex flex-col gap-3">
          <Heading dotColor="bg-brand">意图分析</Heading>
          <SectionCard>
            <div className="text-sm leading-relaxed text-text-body">
              {message.content}
            </div>
            {message.optimizedQuery && (
              <div className="mt-1.5 text-xs font-medium text-brand">
                优化后查询: {message.optimizedQuery}
              </div>
            )}
          </SectionCard>
        </BentoCard>
      </div>
    );
  }

  if (message.role === "retrieval") {
    const [expanded, setExpanded] = useState(false);
    return (
      <div data-testid="chat-message">
        <div className="rounded-2xl bg-bg-card p-6">
          <div className="flex flex-col gap-3.5">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="flex w-full items-center justify-between text-left"
            >
              <span className="font-display text-base font-semibold text-black">
                📄 {message.content}
              </span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className={`h-4 w-4 text-text-tertiary transition-transform ${expanded ? "rotate-180" : ""}`}
              >
                <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clipRule="evenodd" />
              </svg>
            </button>
            {expanded && message.chunks && (
              <RetrievalCard
                chunks={message.chunks}
                selectedChunks={selectedChunks}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div data-testid="chat-message" className="flex justify-end">
        <div className="w-fit max-w-[80%] rounded-2xl bg-bg-user px-7 py-6">
          <div className="font-display text-[15px] font-semibold text-[#5D4037]">
            🧑 You
          </div>
          <div className="mt-2 text-[15px] leading-relaxed text-[#5D4037]">
            {message.content}
          </div>
          <div className="mt-3 flex items-center justify-end gap-1">
            <span
              data-testid="message-timestamp"
              className="text-xs text-[#8D6E63]"
            >
              {timestamp}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="chat-message">
      <BentoCard className="flex flex-col gap-3.5">
        <span className="font-display text-[15px] font-semibold text-brand">
          🤖 广师大助手
        </span>
        <div className="prose prose-sm max-w-none text-sm leading-relaxed text-text-body">
          <MarkdownRenderer content={message.content} />
        </div>
        <div className="flex items-center justify-end gap-1">
          <span
            data-testid="message-timestamp"
            className="text-xs text-text-tertiary"
          >
            {timestamp}
          </span>
          {message.isStreaming && (
            <span
              data-testid="streaming-cursor"
              className="inline-block h-4 w-2 animate-pulse rounded-sm bg-text-tertiary"
            />
          )}
        </div>
      </BentoCard>
    </div>
  );
}
