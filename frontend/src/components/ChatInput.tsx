"use client";

import { useState, useRef, useCallback, useEffect, KeyboardEvent, ChangeEvent } from "react";
import type { RetrievalMode, RetrievalSettings } from "@/types/chat";

const RETRIEVAL_OPTIONS: { value: RetrievalMode; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "manual", label: "学生手册" },
  { value: "forum", label: "学校贴吧" },
  { value: "both", label: "都检索" },
  { value: "none", label: "不检索" },
];

interface ChatInputProps {
  onSend: (content: string) => void;
  isLoading: boolean;
  retrievalMode: RetrievalMode;
  onRetrievalModeChange: (mode: RetrievalMode) => void;
  settings: RetrievalSettings;
  onSettingsChange: (settings: RetrievalSettings) => void;
}

export default function ChatInput({
  onSend,
  isLoading,
  retrievalMode,
  onRetrievalModeChange,
  settings,
  onSettingsChange,
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!showSettings) return;
    const handleClick = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showSettings]);

  const canSend = text.trim().length > 0 && !isLoading;

  return (
    <div className="mx-auto w-full max-w-[700px] px-4 pb-4">
      <div className="rounded-2xl bg-bg-card px-5 py-5">
        {/* ── KB selector row ── */}
        <div className="relative mb-3 flex items-center gap-1.5">
          {RETRIEVAL_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onRetrievalModeChange(opt.value)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                retrievalMode === opt.value
                  ? "bg-brand text-white"
                  : "bg-bg-soft text-text-tertiary hover:bg-border-soft"
              }`}
            >
              {opt.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setShowSettings((prev) => !prev)}
            className="ml-auto flex h-7 w-7 items-center justify-center rounded-full text-text-tertiary transition-colors hover:bg-bg-soft hover:text-foreground"
            aria-label="Settings"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path fillRule="evenodd" d="M7.84 1.804A1 1 0 0 1 8.82 1h2.36a1 1 0 0 1 .98.804l.331 1.652a6.993 6.993 0 0 1 1.929 1.115l1.598-.54a1 1 0 0 1 1.186.447l1.18 2.044a1 1 0 0 1-.205 1.251l-1.267 1.113a7.047 7.047 0 0 1 0 2.228l1.267 1.113a1 1 0 0 1 .205 1.25l-1.18 2.045a1 1 0 0 1-1.187.447l-1.598-.54a6.993 6.993 0 0 1-1.929 1.115l-.33 1.652A1 1 0 0 1 11.18 19H8.82a1 1 0 0 1-.98-.804l-.331-1.652a6.993 6.993 0 0 1-1.929-1.115l-1.598.54a1 1 0 0 1-1.186-.447l-1.18-2.044a1 1 0 0 1 .205-1.251l1.267-1.113a7.05 7.05 0 0 1 0-2.228L1.82 7.593a1 1 0 0 1-.205-1.25l1.18-2.045a1 1 0 0 1 1.187-.447l1.598.54A6.993 6.993 0 0 1 7.51 3.456l.33-1.652Z" clipRule="evenodd" />
              <path d="M10 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
            </svg>
          </button>

          {/* ── Settings popover ── */}
          {showSettings && (
            <div ref={settingsRef} className="absolute bottom-full right-0 mb-2 w-64 rounded-xl border border-border-soft bg-white p-4 shadow-lg">
              <h3 className="mb-3 text-sm font-semibold text-foreground">RAG 检索设置</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-text-tertiary">学生手册 Top-K</label>
                  <input
                    type="number" min={1} max={20}
                    value={settings.top_k_manual}
                    onChange={(e) => onSettingsChange({ ...settings, top_k_manual: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border-soft px-3 py-1.5 text-sm outline-none focus:border-brand"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-tertiary">学校贴吧 Top-K</label>
                  <input
                    type="number" min={1} max={20}
                    value={settings.top_k_forum}
                    onChange={(e) => onSettingsChange({ ...settings, top_k_forum: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border-soft px-3 py-1.5 text-sm outline-none focus:border-brand"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-tertiary">评分筛选 Top-K</label>
                  <input
                    type="number" min={1} max={10}
                    value={settings.top_k_scored}
                    onChange={(e) => onSettingsChange({ ...settings, top_k_scored: Number(e.target.value) })}
                    className="w-full rounded-lg border border-border-soft px-3 py-1.5 text-sm outline-none focus:border-brand"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Input area (unchanged) ── */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="请输入..."
              disabled={isLoading}
              rows={1}
              className="w-full resize-none rounded-xl border border-border-soft bg-bg-soft px-5 py-3 text-sm text-foreground placeholder-text-tertiary outline-none transition-colors focus:border-brand focus:bg-white disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Message input"
            />
          </div>
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            aria-label="Send"
            className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-full bg-brand text-white transition-colors hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-40"
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
      </div>
    </div>
  );
}
