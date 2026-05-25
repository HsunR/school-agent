"use client";

import type { ChatMessage as ChatMessageType } from "@/types/chat";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import RetrievalCard from "@/components/RetrievalCard";

interface ChatMessageProps {
  message: ChatMessageType;
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

export default function ChatMessage({ message }: ChatMessageProps) {
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
    return (
      <div data-testid="chat-message">
        <BentoCard className="flex flex-col gap-3.5">
          <span className="font-display text-base font-semibold text-black">
            📄 {message.content}
          </span>
          {message.chunks && <RetrievalCard chunks={message.chunks} />}
        </BentoCard>
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
