"use client";

import { useRef, useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import ChatInput from "@/components/ChatInput";
import ChatMessage from "@/components/ChatMessage";

export default function Home() {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    clearError,
  } = useChat();

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const hasUserOrAssistantMessages = messages.some(
    (msg) => msg.role === "user" || msg.role === "assistant",
  );

  return (
    <div className="flex h-full flex-col">
      {/* Chat header with clear button */}
      {hasUserOrAssistantMessages && (
        <div className="flex items-center justify-end border-b border-gray-200 px-4 py-2">
          <button
            type="button"
            onClick={clearMessages}
            className="rounded-md px-3 py-1 text-xs text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
            aria-label="Clear chat"
          >
            Clear chat
          </button>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="mx-4 mt-2 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4 shrink-0"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM8.28 7.22a.75.75 0 0 0-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 1 0 1.06 1.06L10 11.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L11.06 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L10 8.94 8.28 7.22Z"
              clipRule="evenodd"
            />
          </svg>
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="shrink-0 text-red-500 transition-colors hover:text-red-700"
            aria-label="Dismiss error"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
            >
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-4">
          {/* Welcome message — always shown, independent of useChat state */}
          <ChatMessage
            message={{
              id: "welcome",
              role: "assistant",
              content:
                "你好呀！我是广师助手 🤗 有什么想问的尽管说——学习、生活、校园资讯，我都可以帮提供建议和意见",
              timestamp: Date.now(),
              isStreaming: false,
            }}
          />

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
