import "@testing-library/jest-dom/vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";
import ChatMessage from "@/components/ChatMessage";
import type { ChatMessage as ChatMessageType } from "@/types/chat";

afterEach(() => {
  cleanup();
});

describe("ChatMessage", () => {
  const baseMessage: ChatMessageType = {
    id: "1",
    role: "user",
    content: "Hello, world!",
    timestamp: 1700000000000,
  };

  it("renders user message with right alignment", () => {
    render(<ChatMessage message={baseMessage} />);

    const messageEl = screen.getByTestId("chat-message");
    expect(messageEl).toHaveClass("justify-end");
  });

  it("renders assistant message with left alignment", () => {
    const msg: ChatMessageType = { ...baseMessage, role: "assistant" };
    render(<ChatMessage message={msg} />);

    const messageEl = screen.getByTestId("chat-message");
    expect(messageEl).toHaveClass("justify-start");
  });

  it("shows 'You' label for user messages", () => {
    render(<ChatMessage message={baseMessage} />);
    expect(screen.getByText("You")).toBeInTheDocument();
  });

  it("shows 'AI' label for assistant messages", () => {
    const msg: ChatMessageType = { ...baseMessage, role: "assistant" };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("renders assistant message content via markdown", () => {
    const msg: ChatMessageType = {
      ...baseMessage,
      role: "assistant",
      content: "**bold text**",
    };
    render(<ChatMessage message={msg} />);

    expect(screen.getByText("bold text")).toBeInTheDocument();
  });

  it("shows blinking cursor when isStreaming is true", () => {
    const msg: ChatMessageType = {
      ...baseMessage,
      role: "assistant",
      isStreaming: true,
    };
    render(<ChatMessage message={msg} />);

    expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();
  });

  it("does not show blinking cursor when isStreaming is false", () => {
    render(<ChatMessage message={baseMessage} />);

    expect(screen.queryByTestId("streaming-cursor")).not.toBeInTheDocument();
  });

  it("shows timestamp in HH:MM format", () => {
    render(<ChatMessage message={baseMessage} />);

    const timeRegex = /^\d{2}:\d{2}$/;
    const timestampEl = screen.getByTestId("message-timestamp");
    expect(timestampEl).toBeInTheDocument();
    expect(timestampEl.textContent).toMatch(timeRegex);
  });

  it("renders long user content without breaking layout", () => {
    const longContent = "a".repeat(5000);
    const msg: ChatMessageType = { ...baseMessage, content: longContent };
    render(<ChatMessage message={msg} />);

    const messageEl = screen.getByTestId("chat-message");
    expect(messageEl).toBeInTheDocument();
    expect(screen.getByText(longContent)).toBeInTheDocument();
  });

  it("renders system messages with left alignment and AI label", () => {
    const msg: ChatMessageType = { ...baseMessage, role: "system" };
    render(<ChatMessage message={msg} />);

    const messageEl = screen.getByTestId("chat-message");
    expect(messageEl).toHaveClass("justify-start");
    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("renders empty assistant message without error", () => {
    const msg: ChatMessageType = {
      ...baseMessage,
      role: "assistant",
      content: "",
    };
    render(<ChatMessage message={msg} />);

    expect(screen.getByTestId("chat-message")).toBeInTheDocument();
    expect(screen.getByText("AI")).toBeInTheDocument();
  });
});
