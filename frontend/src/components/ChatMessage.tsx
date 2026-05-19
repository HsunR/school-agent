"use client";

import type { ChatMessage as ChatMessageType } from "@/types/chat";
import MarkdownRenderer from "@/components/MarkdownRenderer";

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

  return (
    <div
      data-testid="chat-message"
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-500 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        <div
          className={`mb-1 text-xs font-semibold ${
            isUser ? "text-blue-100" : "text-gray-500"
          }`}
        >
          {isUser ? "You" : "AI"}
        </div>

        <div className={`text-sm leading-relaxed ${isUser ? "text-white" : "prose prose-sm max-w-none"}`}>
          {isUser ? (
            message.content
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        <div className="mt-1 flex items-center justify-end gap-1">
          <span
            data-testid="message-timestamp"
            className={`text-xs ${
              isUser ? "text-blue-200" : "text-gray-400"
            }`}
          >
            {timestamp}
          </span>
          {message.isStreaming && (
            <span
              data-testid="streaming-cursor"
              className="inline-block h-4 w-2 animate-pulse rounded-sm bg-gray-500"
            />
          )}
        </div>
      </div>
    </div>
  );
}
