"use client";

import { useState, useRef, useCallback, KeyboardEvent, ChangeEvent } from "react";

interface ChatInputProps {
  onSend: (content: string) => void;
  isLoading: boolean;
}

const MAX_CHARS = 1000;

export default function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value);
      adjustHeight();
    },
    [adjustHeight]
  );

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const charCount = text.length;
  const isOverLimit = charCount > MAX_CHARS;
  const canSend = charCount > 0 && charCount <= MAX_CHARS && !isLoading;

  return (
    <div className="flex items-end gap-3 border-t border-gray-200 bg-white px-4 py-3">
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={isLoading}
          maxLength={MAX_CHARS + 100}
          rows={1}
          className="w-full resize-none rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 pr-16 text-sm text-gray-900 placeholder-gray-400 outline-none transition-colors focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Message input"
        />
        <span
          data-testid="char-counter"
          className={`absolute bottom-3 right-3 text-xs tabular-nums ${
            isOverLimit
              ? "text-red-500"
              : charCount > 0
                ? "text-gray-400"
                : "text-gray-300"
          }`}
        >
          {charCount.toLocaleString()}/1,000
        </span>
      </div>
      <button
        type="button"
        onClick={handleSend}
        disabled={!canSend}
        aria-label="Send"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-5 w-5"
        >
          <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
        </svg>
      </button>
    </div>
  );
}
