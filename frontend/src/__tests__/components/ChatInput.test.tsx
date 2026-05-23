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

  it("enables send button for long input", async () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(/type a message/i);
    fireEvent.change(textarea, { target: { value: "a".repeat(1001) } });

    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });
});
