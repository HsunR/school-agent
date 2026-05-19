export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

export interface SSEPayload {
  token: string;
  done: boolean;
  error?: string;
}
