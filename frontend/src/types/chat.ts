export type MessageRole = "user" | "assistant" | "system" | "status" | "retrieval" | "scoring" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  node?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  chunks?: RetrievalPreview[];
}

export interface RetrievalPreview {
  preview: string;
  source: string;
  score?: number;
  compressed?: string;
}

export interface SSEPayload {
  type: "status" | "retrieval" | "scoring" | "token" | "error";
  token?: string;
  done?: boolean;
  error?: string;
  node?: string;
  label?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  source?: string;
  chunks?: RetrievalPreview[];
  index?: number;
  score?: number;
  compressed?: string;
}
