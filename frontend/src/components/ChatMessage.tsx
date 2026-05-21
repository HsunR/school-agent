"use client";

import type { ChatMessage as ChatMessageType } from "@/types/chat";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import RetrievalCard from "@/components/RetrievalCard";

interface ChatMessageProps {
  message: ChatMessageType;
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
      <div data-testid="chat-message" className="mb-4 flex justify-start">
        <div className="max-w-[80%] rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-gray-500">
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-gray-400">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-400" />
            {message.node === "routing" ? "系统分析" : "系统"}
          </div>
          <div className="text-sm">{message.content}</div>
          {message.decision && (
            <div className="mt-1 text-xs text-gray-400">
              {message.decision.search_manual && "📖 需要查学生手册 "}
              {message.decision.search_forum && "💬 需要查学校贴吧 "}
              {!message.decision.search_manual && !message.decision.search_forum && "无需检索，直接回答"}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (message.role === "retrieval") {
    return (
      <div data-testid="chat-message" className="mb-4 flex justify-start">
        <div className="max-w-[80%] rounded-2xl border border-green-200 bg-green-50 px-4 py-3">
          <div className="mb-2 text-xs font-semibold text-green-700">
            📄 {message.content}
          </div>
          {message.chunks && <RetrievalCard chunks={message.chunks} />}
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div data-testid="chat-message" className="mb-4 flex justify-end">
        <div className="max-w-[80%] rounded-2xl bg-blue-500 px-4 py-3 text-white">
          <div className="mb-1 text-xs font-semibold text-blue-100">You</div>
          <div className="text-sm leading-relaxed text-white">{message.content}</div>
          <div className="mt-1 flex items-center justify-end gap-1">
            <span data-testid="message-timestamp" className="text-xs text-blue-200">{timestamp}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="chat-message" className="mb-4 flex justify-start">
      <div className="max-w-[80%] rounded-2xl bg-gray-100 px-4 py-3 text-gray-900">
        <div className="mb-1 text-xs font-semibold text-gray-500">AI</div>
        <div className="prose prose-sm max-w-none text-sm leading-relaxed">
          <MarkdownRenderer content={message.content} />
        </div>
        <div className="mt-1 flex items-center justify-end gap-1">
          <span data-testid="message-timestamp" className="text-xs text-gray-400">{timestamp}</span>
          {message.isStreaming && (
            <span data-testid="streaming-cursor" className="inline-block h-4 w-2 animate-pulse rounded-sm bg-gray-500" />
          )}
        </div>
      </div>
    </div>
  );
}
