export type MessageRole = "user" | "assistant" | "system" | "status" | "retrieval" | "scoring" | "intent" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  node?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  chunks?: RetrievalPreview[];
  optimizedQuery?: string;
}

export interface SelectedChunk {
  source: string;
  preview: string;
}

export interface RetrievalPreview {
  preview: string;
  source: string;
  score?: number;
  compressed?: string;
}

export type RetrievalMode = "auto" | "manual" | "forum" | "both" | "none";

export interface RetrievalSettings {
  top_k_manual: number;
  top_k_forum: number;
  top_k_scored: number;
}

export interface SSEPayload {
  type: "status" | "retrieval" | "scoring" | "token" | "intent" | "error" | "context_selected";
  token?: string;
  done?: boolean;
  error?: string;
  node?: string;
  label?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  source?: string;
  chunks?: RetrievalPreview[];
  selected?: SelectedChunk[];
  index?: number;
  score?: number;
  compressed?: string;
  optimized_query?: string;
  compressed_context?: string;
}
