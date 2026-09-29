/**
 * Chat hydrate, send, badge-order, loading and failure-rollback tests for
 * `ChatPanel` (Phase 6, TEST-04). Driven through the real provider tree via
 * `renderWithProviders`; every request goes through the real `api.ts` into
 * `stubFetch` (D-05). No app module is mocked.
 */

import { randomUUID } from "node:crypto";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";
import {
  stubFetch,
  deferred,
  type FetchReply,
} from "@/test-support/fetchStub";
import { renderWithProviders } from "@/test-support/renderWithProviders";
import type { ChatMessage, ChatResponse } from "@/lib/types";

// jsdom's global `crypto` may not implement `randomUUID` (06-RESEARCH.md);
// chatStore.tsx's sendMessage() calls it on every send. Provide a
// delegating fallback only when needed, scoped to this test file — not a
// change to vitest.setup.ts, which 06-02 owns (reused from Task 1's guard).
beforeEach(() => {
  if (
    typeof crypto === "undefined" ||
    typeof crypto.randomUUID !== "function"
  ) {
    vi.stubGlobal("crypto", { randomUUID });
  }
});

function historyMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "hist-1",
    role: "user",
    content: "buy 2 AAPL",
    trades: [],
    watchlist_changes: [],
    created_at: "2026-09-28T00:00:00Z",
    ...overrides,
  };
}

function executedTradeReply(): ChatResponse {
  return {
    message: "[LLM_MOCK] Requesting to buy 2.0 shares of AAPL.",
    trades: [
      {
        ticker: "AAPL",
        side: "buy",
        quantity: 2,
        price: 190,
        outcome: "executed",
        reason: null,
      },
    ],
    watchlist_changes: [],
  };
}

async function sendMessage(text: string): Promise<void> {
  const input = screen.getByPlaceholderText(/Ask about your portfolio/);
  fireEvent.change(input, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

describe("ChatPanel", () => {
  it("shows loading copy while hydrating, then the empty-state heading", async () => {
    const held = deferred<FetchReply>();
    stubFetch({ "GET /api/chat": () => held.promise });

    renderWithProviders(<ChatPanel />);

    expect(screen.getByText(/Loading conversation/)).toBeInTheDocument();

    await act(async () => {
      held.resolve({ body: { messages: [] } });
      await held.promise;
    });

    expect(screen.getByText("Ask FinAlly anything")).toBeInTheDocument();
  });

  it("renders prior history with badges, trade badge before watchlist badge", async () => {
    stubFetch({
      "GET /api/chat": {
        body: {
          messages: [
            historyMessage(),
            historyMessage({
              id: "hist-2",
              role: "assistant",
              content: "[LLM_MOCK] Requesting to buy 2.0 shares of AAPL.",
              trades: [
                {
                  ticker: "AAPL",
                  side: "buy",
                  quantity: 2,
                  price: 190,
                  outcome: "executed",
                  reason: null,
                },
              ],
              watchlist_changes: [
                {
                  ticker: "ZZZZ",
                  action: "add",
                  outcome: "error",
                  reason: "Unknown ticker: ZZZZ",
                },
              ],
            }),
          ],
        },
      },
    });

    renderWithProviders(<ChatPanel />);

    await screen.findByText("buy 2 AAPL");
    expect(
      screen.getByText("[LLM_MOCK] Requesting to buy 2.0 shares of AAPL."),
    ).toBeInTheDocument();

    const tradeBadge = screen.getByText("✓ buy 2 AAPL @ $190.00");
    const watchlistBadge = screen.getByText("✕ Add ZZZZ");
    expect(tradeBadge).toBeInTheDocument();
    expect(watchlistBadge).toBeInTheDocument();
    expect(
      tradeBadge.compareDocumentPosition(watchlistBadge) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("shows a hydrate-error alert while keeping the input usable", async () => {
    stubFetch({ "GET /api/chat": { status: 500, body: { detail: "boom" } } });

    renderWithProviders(<ChatPanel />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Failed to load conversation history.");

    const input = screen.getByPlaceholderText(/Ask about your portfolio/);
    expect(input).toBeEnabled();
  });

  it("shows the pending-send state, then resolves to the assistant bubble and badge", async () => {
    stubFetch({ "GET /api/chat": { body: { messages: [] } } });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    const held = deferred<FetchReply>();
    stubFetch({
      "GET /api/chat": { body: { messages: [] } },
      "POST /api/chat": () => held.promise,
    });

    await sendMessage("buy 2 AAPL");

    expect(screen.getByText("buy 2 AAPL")).toBeInTheDocument();
    expect(screen.getByText("FinAlly is thinking")).toBeInTheDocument();
    const input = screen.getByPlaceholderText(/Ask about your portfolio/);
    expect(input).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();

    await act(async () => {
      held.resolve({ body: executedTradeReply() });
      await held.promise;
    });

    await waitFor(() => {
      expect(
        screen.getByText("[LLM_MOCK] Requesting to buy 2.0 shares of AAPL."),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("✓ buy 2 AAPL @ $190.00")).toBeInTheDocument();
    expect(screen.queryByText("FinAlly is thinking")).not.toBeInTheDocument();
    expect(input).toBeEnabled();
    expect(input).toHaveValue("");
  });

  it("issues exactly one extra portfolio GET after an executed trade, none after an errored one", async () => {
    const { callsTo } = stubFetch({
      "GET /api/chat": { body: { messages: [] } },
      "POST /api/chat": { body: executedTradeReply() },
    });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    const before = callsTo("GET /api/portfolio").length;
    await sendMessage("buy 2 AAPL");
    await screen.findByText("✓ buy 2 AAPL @ $190.00");
    expect(callsTo("GET /api/portfolio")).toHaveLength(before + 1);
  });

  it("issues no extra portfolio GET when the only trade errored", async () => {
    const { callsTo } = stubFetch({
      "GET /api/chat": { body: { messages: [] } },
      "POST /api/chat": {
        body: {
          message: "[LLM_MOCK] Requesting to buy 1000.0 shares of AAPL.",
          trades: [
            {
              ticker: "AAPL",
              side: "buy",
              quantity: 1000,
              price: null,
              outcome: "error",
              reason: "Insufficient cash: need $190000.00, have $10000.00",
            },
          ],
          watchlist_changes: [],
        },
      },
    });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    const before = callsTo("GET /api/portfolio").length;
    await sendMessage("buy 1000 AAPL");
    await screen.findByText("✕ buy 1000 AAPL");
    expect(callsTo("GET /api/portfolio")).toHaveLength(before);
  });

  it("shows the backend's string error detail, rolls back the optimistic bubble, keeps the typed text", async () => {
    stubFetch({
      "GET /api/chat": { body: { messages: [] } },
      "POST /api/chat": {
        status: 502,
        body: { detail: "LLM provider unavailable" },
      },
    });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    await sendMessage("buy 2 AAPL");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("LLM provider unavailable");
    expect(screen.queryByText("buy 2 AAPL")).not.toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Ask about your portfolio/),
    ).toHaveValue("buy 2 AAPL");
  });

  it("joins a validation-array error detail with semicolons in the alert", async () => {
    stubFetch({
      "GET /api/chat": { body: { messages: [] } },
      "POST /api/chat": {
        status: 422,
        body: {
          detail: [
            { msg: "message: field required" },
            { msg: "message: must not be blank" },
          ],
        },
      },
    });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    await sendMessage("buy 2 AAPL");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "message: field required; message: must not be blank",
    );
  });

  it("sends the message when Enter is pressed", async () => {
    const { callsTo } = stubFetch({
      "GET /api/chat": { body: { messages: [] } },
      "POST /api/chat": { body: executedTradeReply() },
    });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    const input = screen.getByPlaceholderText(/Ask about your portfolio/);
    fireEvent.change(input, { target: { value: "buy 2 AAPL" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await screen.findByText("✓ buy 2 AAPL @ $190.00");
    expect(callsTo("POST /api/chat")).toHaveLength(1);
  });

  it("disables Send for an empty or whitespace-only input", async () => {
    stubFetch({ "GET /api/chat": { body: { messages: [] } } });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    const input = screen.getByPlaceholderText(/Ask about your portfolio/);
    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton).toBeDisabled();

    fireEvent.change(input, { target: { value: "   " } });
    expect(sendButton).toBeDisabled();
  });

  it("collapses to the rail and expands back to the full panel", async () => {
    stubFetch({ "GET /api/chat": { body: { messages: [] } } });
    renderWithProviders(<ChatPanel />);
    await screen.findByText("Ask FinAlly anything");

    fireEvent.click(screen.getByRole("button", { name: /Collapse/ }));

    const railButton = screen.getByRole("button", {
      name: "Expand chat panel",
    });
    expect(railButton).toBeInTheDocument();
    expect(screen.queryByText("AI Assistant")).not.toBeInTheDocument();

    fireEvent.click(railButton);

    expect(screen.getByText("AI Assistant")).toBeInTheDocument();
  });
});
