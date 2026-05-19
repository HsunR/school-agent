import "@testing-library/jest-dom/vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import ChatInput from "@/components/ChatInput";

afterEach(() => {
  cleanup();
});

describe("ChatInput", () => {
  it("renders textarea and send button", () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    expect(
      screen.getByPlaceholderText(/type a message/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("button is disabled when input is empty", () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("button is enabled when input has text", async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "Hello");

    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });

  it("input and button are disabled when isLoading is true", () => {
    render(<ChatInput onSend={vi.fn()} isLoading={true} />);

    expect(screen.getByPlaceholderText(/type a message/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("calls onSend with input text on button click", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "Test message");

    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(onSend).toHaveBeenCalledWith("Test message");
  });

  it("calls onSend on Enter key (without Shift)", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "Enter message");

    await user.keyboard("{Enter}");

    expect(onSend).toHaveBeenCalledWith("Enter message");
  });

  it("does not call onSend on Shift+Enter", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "Shift enter");
    await user.keyboard("{Shift>}{Enter}{/Shift}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("shows character count correctly", async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "Hello");

    expect(screen.getByText(/5\/1,000/)).toBeInTheDocument();
  });

  it("does not call onSend for whitespace-only input on button click", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "   ");

    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not call onSend for whitespace-only input on Enter key", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    await user.type(textarea, "   ");
    await user.keyboard("{Enter}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables send button when input exceeds max length", async () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    fireEvent.change(textarea, { target: { value: "a".repeat(1001) } });

    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    // Character counter should show the count in red
    const counter = screen.getByTestId("char-counter");
    expect(counter).toHaveTextContent(/1,001\/1,000/);
    expect(counter.className).toContain("text-red-500");
  });

  it("enables send button at exactly 1000 characters", async () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    fireEvent.change(textarea, { target: { value: "a".repeat(1000) } });

    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
    const counter = screen.getByTestId("char-counter");
    expect(counter).toHaveTextContent(/1,000\/1,000/);
  });
});
