import "@testing-library/jest-dom/vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import ChatInput from "@/components/ChatInput";

const defaultProps = {
  onSend: vi.fn(),
  isLoading: false,
  retrievalMode: "auto" as const,
  onRetrievalModeChange: vi.fn(),
  settings: { top_k_manual: 6, top_k_forum: 6, top_k_scored: 3 },
  onSettingsChange: vi.fn(),
  skipIntent: false,
  onSkipIntentChange: vi.fn(),
};

afterEach(() => {
  cleanup();
});

describe("ChatInput", () => {
  it("renders textarea and send button", () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByPlaceholderText(/请输入/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("button is disabled when input is empty", () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("button is enabled when input has text", async () => {
    const user = userEvent.setup();
    render(<ChatInput {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    await user.type(textarea, "Hello");
    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });

  it("input and button are disabled when isLoading is true", () => {
    render(<ChatInput {...defaultProps} isLoading={true} />);
    expect(screen.getByPlaceholderText(/请输入/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("calls onSend with input text on button click", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput {...defaultProps} onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    await user.type(textarea, "Test message");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(onSend).toHaveBeenCalledWith("Test message");
  });

  it("calls onSend on Enter key (without Shift)", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput {...defaultProps} onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    await user.type(textarea, "Enter message");
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith("Enter message");
  });

  it("does not call onSend on Shift+Enter", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput {...defaultProps} onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    await user.type(textarea, "Shift enter");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not call onSend for whitespace-only input on button click", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput {...defaultProps} onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    await user.type(textarea, "   ");
    await user.click(screen.getByRole("button", { name: /send/i }));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not call onSend for whitespace-only input on Enter key", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput {...defaultProps} onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    await user.type(textarea, "   ");
    await user.keyboard("{Enter}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("enables send button for long input", async () => {
    render(<ChatInput {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(/请输入/i);
    fireEvent.change(textarea, { target: { value: "a".repeat(1001) } });
    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });
});

describe("ChatInput KB selector", () => {
  it("renders all KB options", () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByText("Auto")).toBeInTheDocument();
    expect(screen.getByText("学生手册")).toBeInTheDocument();
    expect(screen.getByText("学校贴吧")).toBeInTheDocument();
    expect(screen.getByText("都检索")).toBeInTheDocument();
    expect(screen.getByText("不检索")).toBeInTheDocument();
  });

  it("calls onRetrievalModeChange when a KB option is clicked", () => {
    const onRetrievalModeChange = vi.fn();
    render(<ChatInput {...defaultProps} onRetrievalModeChange={onRetrievalModeChange} />);
    fireEvent.click(screen.getByText("学生手册"));
    expect(onRetrievalModeChange).toHaveBeenCalledWith("manual");
  });

  it("highlights the active retrieval mode", () => {
    render(<ChatInput {...defaultProps} retrievalMode="forum" />);
    const btn = screen.getByText("学校贴吧");
    expect(btn.className).toContain("bg-brand");
  });

  it("opens settings popover on gear click", () => {
    render(<ChatInput {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Settings"));
    expect(screen.getByText("RAG 检索设置")).toBeInTheDocument();
  });
});
