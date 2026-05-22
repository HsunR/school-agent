"use client";

import { useState, useCallback, useRef } from "react";
import type { ChatMessage, SSEPayload } from "@/types/chat";

function generateId(): string {
  return Math.random().toString(36).slice(2, 11);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLoadingRef = useRef(false);
  const messagesRef = useRef<ChatMessage[]>([]);

  // Keep refs in sync with current state
  messagesRef.current = messages;
  isLoadingRef.current = isLoading;

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

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    clearError,
  };
}
