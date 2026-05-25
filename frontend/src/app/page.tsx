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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-full flex-col bg-background">
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

      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-background pb-2 pt-4">
        <div className="mx-auto flex max-w-[700px] items-center justify-between rounded-2xl bg-bg-card px-7 py-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-5 w-5 text-white"
              >
                <path d="M11.7 2.805a.75.75 0 0 1 .6 0A60.65 60.65 0 0 1 22.83 8.72a.75.75 0 0 1-.231 1.337 49.948 49.948 0 0 0-9.902 3.912l-.003.002c-.114.06-.227.119-.34.18a.75.75 0 0 1-.707 0A50.88 50.88 0 0 0 7.5 12.173v-.224c0-.131.01-.262.03-.393l.028-.24a49.474 49.474 0 0 1-.494-1.043.75.75 0 0 1 .292-1.017 51.28 51.28 0 0 0 3.709-3.038.75.75 0 0 1 .937-.064 50.207 50.207 0 0 0 5.2 2.654.75.75 0 0 1-.582 1.383 28.979 28.979 0 0 1-2.218-.94v.733a49.93 49.93 0 0 1-2.51 1.3.75.75 0 0 1-.604 0 48.627 48.627 0 0 0-3.878-1.685 50.584 50.584 0 0 1-2.233-.9.75.75 0 0 1-.262-1.203 50.466 50.466 0 0 0 1.3-1.784 50.468 50.468 0 0 1 3.36-4.025A.75.75 0 0 1 11.7 2.805Z" />
              </svg>
            </div>
            <span className="font-display text-xl font-semibold text-black">
              广师大助手
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm text-text-tertiary">在线</span>
            </div>
            <button
              type="button"
              onClick={clearMessages}
              className="rounded-lg border border-brand bg-transparent px-4 py-1.5 text-sm text-brand transition-colors hover:bg-brand-light"
              aria-label="Clear chat"
            >
              清除对话
            </button>
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        <div className="mx-auto flex max-w-[700px] flex-col gap-3">
          {/* Welcome message */}
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
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
