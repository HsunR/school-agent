"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { ChatMessage, SSEPayload, RetrievalMode, RetrievalSettings } from "@/types/chat";

function generateId(): string {
  return Math.random().toString(36).slice(2, 11);
}

const STORAGE_KEY_MODE = "retrieval_mode";
const STORAGE_KEY_SETTINGS = "retrieval_settings";

const DEFAULT_SETTINGS: RetrievalSettings = {
  top_k_manual: 6,
  top_k_forum: 6,
  top_k_scored: 3,
};

function loadStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("auto");
  const [settings, setSettings] = useState<RetrievalSettings>(DEFAULT_SETTINGS);

  // Sync from localStorage after hydration to avoid SSR mismatch
  useEffect(() => {
    const storedMode = loadStorage<RetrievalMode>(STORAGE_KEY_MODE, "auto");
    if (storedMode !== "auto") setRetrievalMode(storedMode);
    const storedSettings = loadStorage<RetrievalSettings>(STORAGE_KEY_SETTINGS, DEFAULT_SETTINGS);
    if (storedSettings !== DEFAULT_SETTINGS) setSettings(storedSettings);
  }, []);

  const isLoadingRef = useRef(false);
  const messagesRef = useRef<ChatMessage[]>([]);
  const retrievalModeRef = useRef<RetrievalMode>(retrievalMode);
  const settingsRef = useRef<RetrievalSettings>(settings);

  // Keep refs in sync with current state
  messagesRef.current = messages;
  isLoadingRef.current = isLoading;
  retrievalModeRef.current = retrievalMode;
  settingsRef.current = settings;

  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim();

    if (!trimmed) {
      setError("Message cannot be empty");
      return;
    }

    if (isLoadingRef.current) return;

    setIsLoading(true);
    setError(null);

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: trimmed,
      timestamp: Date.now(),
    };

    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: "assistant",
      content: "",
      timestamp: Date.now(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    try {
      const historyMessages = messagesRef.current
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-6);
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...historyMessages, userMessage],
          retrieval_mode: retrievalModeRef.current,
          settings: settingsRef.current,
        }),
      });

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}`,
        );
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload: SSEPayload = JSON.parse(line.slice(6));

            if (payload.type === "status" && payload.label) {
              const statusMsg: ChatMessage = {
                id: `status-${generateId()}`,
                role: "status",
                content: payload.label,
                timestamp: Date.now(),
                node: payload.node,
                decision: payload.decision,
              };
              setMessages((prev) => {
                const updated = [...prev];
                updated.splice(updated.length - 1, 0, statusMsg);
                return updated;
              });
              continue;
            }

            if (payload.type === "intent") {
              const intentMsg: ChatMessage = {
                id: `intent-${generateId()}`,
                role: "intent",
                content: payload.label || "正在理解你的问题...",
                timestamp: Date.now(),
                optimizedQuery: payload.optimized_query,
              };
              setMessages((prev) => {
                const updated = [...prev];
                updated.splice(updated.length - 1, 0, intentMsg);
                return updated;
              });
              continue;
            }

            if (payload.type === "retrieval" && payload.label) {
              const retrievalMsg: ChatMessage = {
                id: `retrieval-${generateId()}`,
                role: "retrieval",
                content: payload.label,
                timestamp: Date.now(),
                chunks: payload.chunks || [],
              };
              setMessages((prev) => {
                const updated = [...prev];
                updated.splice(updated.length - 1, 0, retrievalMsg);
                return updated;
              });
              continue;
            }

            if (payload.type === "scoring" && payload.source === "done" && payload.done) {
              continue;
            }

            if (payload.type === "scoring" && payload.source && payload.index !== undefined) {
              setMessages((prev) => {
                const updated = [...prev];
                const sourceMap: Record<string, string> = {
                  school_forum: "学校贴吧",
                  student_manual: "学生手册",
                };
                const targetSource = sourceMap[payload.source!] || payload.source!;
                for (let j = updated.length - 1; j >= 0; j--) {
                  const msg = updated[j];
                  if (msg.role === "retrieval" && msg.chunks) {
                    const chunksFromSource = msg.chunks.filter(
                      (c) => c.source === targetSource,
                    );
                    if (chunksFromSource.length > 0) {
                      const newChunks = [...msg.chunks];
                      const localIdx = msg.chunks.indexOf(chunksFromSource[payload.index!]);
                      if (localIdx >= 0) {
                        newChunks[localIdx] = {
                          ...newChunks[localIdx],
                          score: payload.score,
                          compressed: payload.compressed,
                        };
                        updated[j] = { ...msg, chunks: newChunks };
                      }
                      break;
                    }
                  }
                }
                return updated;
              });
              continue;
            }

            if (payload.type === "token") {
              if (payload.token) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "assistant" && last.isStreaming) {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + payload.token,
                    };
                  }
                  return updated;
                });
              }
              if (payload.done) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "assistant") {
                    updated[updated.length - 1] = {
                      ...last,
                      isStreaming: false,
                    };
                  }
                  return updated;
                });
              }
              continue;
            }

            if (payload.type === "error") {
              setError(payload.error || "Unknown error");
              continue;
            }
          }
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const setRetrievalModeAndPersist = useCallback((mode: RetrievalMode) => {
    setRetrievalMode(mode);
    try { localStorage.setItem(STORAGE_KEY_MODE, JSON.stringify(mode)); } catch {}
  }, []);

  const setSettingsAndPersist = useCallback((s: RetrievalSettings) => {
    setSettings(s);
    try { localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(s)); } catch {}
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    clearError,
    retrievalMode,
    setRetrievalMode: setRetrievalModeAndPersist,
    settings,
    setSettings: setSettingsAndPersist,
  };
}
