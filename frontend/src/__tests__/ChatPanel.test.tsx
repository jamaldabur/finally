import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ChatPanel from "@/components/ChatPanel";
import * as api from "@/lib/api";
import type { ChatStreamHandlers } from "@/lib/api";
import type { ChatMessage, ChatResponse } from "@/lib/types";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getChatHistory: vi.fn(), streamChatMessage: vi.fn() };
});

const mockGetHistory = vi.mocked(api.getChatHistory);
const mockStream = vi.mocked(api.streamChatMessage);

beforeEach(() => {
  vi.clearAllMocks();
});

// Drives the mocked streamChatMessage the same way the real one behaves: calls
// onDelta for each chunk, then onDone, then resolves.
function deferredStream() {
  let handlers!: ChatStreamHandlers;
  let resolve!: () => void;
  let reject!: (err: Error) => void;
  const started = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  mockStream.mockImplementation((_message, h) => {
    handlers = h;
    return started;
  });
  return {
    getHandlers: () => handlers,
    finishWithDelta: (chunk: string) => handlers.onDelta(chunk),
    finishWithDone: (result: ChatResponse) => handlers.onDone(result),
    resolve,
    reject,
  };
}

describe("ChatPanel", () => {
  it("hydrates prior conversation history on mount", async () => {
    const history: ChatMessage[] = [
      { id: "1", role: "user", content: "How is my portfolio doing?", actions: null, created_at: new Date().toISOString() },
      { id: "2", role: "assistant", content: "You're up 3% today.", actions: null, created_at: new Date().toISOString() },
    ];
    mockGetHistory.mockResolvedValue(history);

    render(<ChatPanel onActionExecuted={() => {}} />);

    expect(await screen.findByText("How is my portfolio doing?")).toBeInTheDocument();
    expect(screen.getByText("You're up 3% today.")).toBeInTheDocument();
  });

  it("shows typing dots, then streams the reply in incrementally as chunks arrive", async () => {
    mockGetHistory.mockResolvedValue([]);
    const stream = deferredStream();

    render(<ChatPanel onActionExecuted={() => {}} />);

    fireEvent.change(screen.getByPlaceholderText("Message FinAlly…"), { target: { value: "Buy 5 AAPL" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByText("Buy 5 AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();

    // First chunk arrives: dots are replaced by real (partial) text.
    stream.finishWithDelta("Done, ");
    await waitFor(() => expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument());
    expect(screen.getByText("Done,", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText("Done, bought 5 AAPL for you.")).not.toBeInTheDocument();

    // Second chunk appends onto the first rather than replacing it.
    stream.finishWithDelta("bought 5 AAPL for you.");
    await waitFor(() => expect(screen.getByText("Done, bought 5 AAPL for you.")).toBeInTheDocument());

    stream.finishWithDone({
      message: "Done, bought 5 AAPL for you.",
      trades: [{ ticker: "AAPL", side: "buy", quantity: 5, status: "executed", reason: null }],
      watchlist_changes: [],
    });
    stream.resolve();

    await waitFor(() => expect(screen.getByText("✓ Buy 5 AAPL")).toBeInTheDocument());
  });

  it("renders an error outcome badge distinctly from a success outcome", async () => {
    mockGetHistory.mockResolvedValue([]);
    const stream = deferredStream();

    render(<ChatPanel onActionExecuted={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Message FinAlly…"), { target: { value: "Buy 1000 TSLA" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    stream.finishWithDelta("Couldn't complete that trade.");
    stream.finishWithDone({
      message: "Couldn't complete that trade.",
      trades: [{ ticker: "TSLA", side: "buy", quantity: 1000, status: "error", reason: "Insufficient cash" }],
      watchlist_changes: [],
    });
    stream.resolve();

    expect(await screen.findByText("✗ Buy 1000 TSLA")).toBeInTheDocument();
  });

  it("shows partial text plus an interrupted notice when the stream ends without a done event", async () => {
    mockGetHistory.mockResolvedValue([]);
    const stream = deferredStream();

    render(<ChatPanel onActionExecuted={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Message FinAlly…"), { target: { value: "How am I doing?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    stream.finishWithDelta("Your portfolio is");
    await waitFor(() => expect(screen.getByText("Your portfolio is", { exact: false })).toBeInTheDocument());

    stream.reject(new Error("Chat stream ended before a response completed"));

    expect(await screen.findByText(/Connection interrupted/)).toBeInTheDocument();
    // The partial text that already arrived stays visible rather than being cleared.
    expect(screen.getByText("Your portfolio is", { exact: false })).toBeInTheDocument();
  });

  it("does not let a second send start while a reply is still streaming", async () => {
    mockGetHistory.mockResolvedValue([]);
    deferredStream();

    render(<ChatPanel onActionExecuted={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("Message FinAlly…"), { target: { value: "First" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(mockStream).toHaveBeenCalledTimes(1);
  });
});
