export type MessageRole = "user" | "assistant" | "system" | "status" | "retrieval" | "error";

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
}

export interface SSEPayload {
  type: "status" | "retrieval" | "token" | "error";
  token?: string;
  done?: boolean;
  error?: string;
  node?: string;
  label?: string;
  decision?: { search_manual: boolean; search_forum: boolean };
  source?: string;
  chunks?: RetrievalPreview[];
}
