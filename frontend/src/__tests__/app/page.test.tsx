import "@testing-library/jest-dom/vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import Page from "@/app/page";

const mockUseChat = vi.fn();

vi.mock("@/hooks/useChat", () => ({
  useChat: (...args: unknown[]) => mockUseChat(...args),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function setupMockState(
  overrides: Partial<ReturnType<typeof import("@/hooks/useChat").useChat>> = {},
) {
  const defaults = {
    messages: [],
    isLoading: false,
    error: null,
    sendMessage: vi.fn(),
    clearMessages: vi.fn(),
    clearError: vi.fn(),
  };
  mockUseChat.mockReturnValue({ ...defaults, ...overrides });
}

describe("Chat Page", () => {
  it("renders chat input and welcome message", () => {
    setupMockState();

    render(<Page />);

    expect(
      screen.getByText((content) => content.includes("你好呀！我是广师助手")),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/请输入/i),
    ).toBeInTheDocument();
  });

  it("sending message shows user message in list", () => {
    const messages = [
      {
        id: "1",
        role: "user" as const,
        content: "Hello, how are you?",
        timestamp: Date.now(),
      },
    ];
    setupMockState({ messages });

    render(<Page />);

    const messageEls = screen.getAllByTestId("chat-message");
    expect(messageEls).toHaveLength(2);
    expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
  });

  it("error state displays error message", () => {
    setupMockState({ error: "Something went wrong" });

    render(<Page />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("error banner is dismissible", async () => {
    const clearError = vi.fn();
    setupMockState({ error: "An error occurred", clearError });

    render(<Page />);

    const dismissButton = screen.getByRole("button", { name: /dismiss/i });
    expect(dismissButton).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(dismissButton);
    expect(clearError).toHaveBeenCalledTimes(1);
  });

  it("clear chat button calls clearMessages", async () => {
    const clearMessages = vi.fn();
    setupMockState({ clearMessages });

    render(<Page />);

    const clearButton = screen.getByRole("button", { name: /clear chat/i });
    expect(clearButton).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(clearButton);
    expect(clearMessages).toHaveBeenCalledTimes(1);
  });

  it("loading state disables chat input", () => {
    setupMockState({ isLoading: true });

    render(<Page />);

    const textarea = screen.getByPlaceholderText(/请输入/i);
    expect(textarea).toBeDisabled();
  });

  it("still shows welcome message when user messages exist", () => {
    const messages = [
      {
        id: "1",
        role: "user" as const,
        content: "Hello",
        timestamp: Date.now(),
      },
    ];
    setupMockState({ messages });

    render(<Page />);

    expect(
      screen.getByText((content) => content.includes("你好呀！我是广师助手")),
    ).toBeInTheDocument();
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders assistant messages with markdown", () => {
    const messages = [
      {
        id: "1",
        role: "assistant" as const,
        content: "**bold** text",
        timestamp: Date.now(),
      },
    ];
    setupMockState({ messages });

    render(<Page />);

    const messageEls = screen.getAllByTestId("chat-message");
    expect(messageEls).toHaveLength(2);
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  it("sends message when user types in ChatInput and presses Enter", async () => {
    const sendMessage = vi.fn();
    setupMockState({ sendMessage });

    render(<Page />);

    const textarea = screen.getByPlaceholderText(/请输入/i);
    const user = userEvent.setup();
    await user.type(textarea, "Test from page");
    await user.keyboard("{Enter}");

    expect(sendMessage).toHaveBeenCalledWith("Test from page");
  });

  it("renders multiple messages in the list", () => {
    const messages = [
      {
        id: "1",
        role: "user" as const,
        content: "First",
        timestamp: Date.now(),
      },
      {
        id: "2",
        role: "assistant" as const,
        content: "Reply 1",
        timestamp: Date.now(),
      },
      {
        id: "3",
        role: "user" as const,
        content: "Second",
        timestamp: Date.now(),
      },
      {
        id: "4",
        role: "assistant" as const,
        content: "Reply 2",
        timestamp: Date.now(),
      },
    ];
    setupMockState({ messages });

    render(<Page />);

    const messageEls = screen.getAllByTestId("chat-message");
    expect(messageEls).toHaveLength(5);
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
    expect(screen.getByText("Reply 1")).toBeInTheDocument();
    expect(screen.getByText("Reply 2")).toBeInTheDocument();
  });

  it("shows error with icon and dismiss button", () => {
    setupMockState({ error: "Test error" });

    render(<Page />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent("Test error");
    expect(
      screen.getByRole("button", { name: /dismiss/i }),
    ).toBeInTheDocument();
  });

  it("does not render error banner when error is null", () => {
    setupMockState({ error: null });

    render(<Page />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
