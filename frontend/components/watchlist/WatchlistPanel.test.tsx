/**
 * Chat-driven watchlist CRUD and read-state tests (Phase 6, TEST-04, P-06).
 *
 * The frontend has no manual watchlist add/remove control (06-03-PLAN.md
 * P-06) — watchlist mutations reach the UI only through the chat copilot: an
 * executed change bumps `watchlistRevision` in `chatStore.tsx`, which is a
 * dependency of `WatchlistPanel`'s fetch effect. So "watchlist CRUD" here
 * means driving the real `ChatInput` with the D-07 trigger phrase and
 * asserting the resulting re-fetch, alongside every read state of the panel
 * itself (loading, rows, live price, empty, error).
 *
 * Every request goes through the real `api.ts` into `stubFetch` (D-05); no
 * app module is mocked and no test-id attribute is used.
 */

import { randomUUID } from "node:crypto";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WatchlistPanel } from "./WatchlistPanel";
import { ChatInput } from "@/components/chat/ChatInput";
import {
  stubFetch,
  deferred,
  type FetchReply,
} from "@/test-support/fetchStub";
import { renderWithProviders } from "@/test-support/renderWithProviders";
import { StubEventSource } from "@/test-support/eventSourceStub";
import type { ChatResponse, WatchlistAction, WatchlistEntry } from "@/lib/types";

function entry(ticker: string, price: number): WatchlistEntry {
  return {
    ticker,
    price,
    previous_price: price,
    direction: "unchanged",
    timestamp: "2026-09-28T00:00:00Z",
  };
}

function chatReply(changes: WatchlistAction[]): ChatResponse {
  return {
    message: "[LLM_MOCK] Requesting a watchlist change.",
    trades: [],
    watchlist_changes: changes,
  };
}

// jsdom's global `crypto` may not implement `randomUUID` (06-RESEARCH.md);
// chatStore.tsx's sendMessage() calls it on every send. Provide a
// delegating fallback only when needed, scoped to this test file — not a
// change to vitest.setup.ts, which 06-02 owns.
beforeEach(() => {
  if (
    typeof crypto === "undefined" ||
    typeof crypto.randomUUID !== "function"
  ) {
    vi.stubGlobal("crypto", { randomUUID });
  }
});

async function sendChatMessage(text: string): Promise<void> {
  const input = screen.getByPlaceholderText(/Ask about your portfolio/);
  fireEvent.change(input, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

describe("WatchlistPanel", () => {
  it("adds a ticker to the watchlist after the copilot executes an add (tracer)", async () => {
    const { callsTo } = stubFetch({
      "GET /api/watchlist": [
        { body: { watchlist: [entry("AAPL", 190)] } },
        { body: { watchlist: [entry("AAPL", 190), entry("PYPL", 78)] } },
      ],
      "POST /api/chat": {
        body: chatReply([
          { ticker: "PYPL", action: "add", outcome: "executed", reason: null },
        ]),
      },
    });

    renderWithProviders(
      <>
        <WatchlistPanel />
        <ChatInput />
      </>,
    );

    await screen.findByRole("button", { name: /^AAPL/ });

    await sendChatMessage("add PYPL to my watchlist");

    await screen.findByRole("button", { name: /^PYPL/ });

    expect(callsTo("GET /api/watchlist")).toHaveLength(2);
    expect(callsTo("POST /api/chat")[0]?.body).toEqual({
      message: "add PYPL to my watchlist",
    });
  });

  it("removes a ticker from the watchlist after the copilot executes a remove", async () => {
    const { callsTo } = stubFetch({
      "GET /api/watchlist": [
        { body: { watchlist: [entry("AAPL", 190), entry("PYPL", 78)] } },
        { body: { watchlist: [entry("AAPL", 190)] } },
      ],
      "POST /api/chat": {
        body: chatReply([
          {
            ticker: "PYPL",
            action: "remove",
            outcome: "executed",
            reason: null,
          },
        ]),
      },
    });

    renderWithProviders(
      <>
        <WatchlistPanel />
        <ChatInput />
      </>,
    );

    await screen.findByRole("button", { name: /^PYPL/ });

    await sendChatMessage("remove PYPL from my watchlist");

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: /^PYPL/ }),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /^AAPL/ })).toBeInTheDocument();
    expect(callsTo("GET /api/watchlist")).toHaveLength(2);
  });

  it("does not re-fetch the watchlist when the copilot's change is rejected", async () => {
    const { callsTo } = stubFetch({
      "GET /api/watchlist": { body: { watchlist: [entry("AAPL", 190)] } },
      "POST /api/chat": {
        body: chatReply([
          {
            ticker: "ZZZZ",
            action: "add",
            outcome: "error",
            reason: "Unknown ticker: ZZZZ",
          },
        ]),
      },
    });

    renderWithProviders(
      <>
        <WatchlistPanel />
        <ChatInput />
      </>,
    );

    await screen.findByRole("button", { name: /^AAPL/ });

    const input = screen.getByPlaceholderText(/Ask about your portfolio/);
    await sendChatMessage("add ZZZZ to my watchlist");

    await waitFor(() => {
      expect(input).toHaveValue("");
    });
    expect(callsTo("GET /api/watchlist")).toHaveLength(1);
  });

  it("shows the loading copy, then the rows once the request resolves", async () => {
    const held = deferred<FetchReply>();
    stubFetch({ "GET /api/watchlist": () => held.promise });

    renderWithProviders(<WatchlistPanel />);

    expect(screen.getByText(/Loading watchlist/)).toBeInTheDocument();

    await act(async () => {
      held.resolve({ body: { watchlist: [entry("AAPL", 190)] } });
      await held.promise;
    });

    expect(screen.queryByText(/Loading watchlist/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^AAPL/ })).toBeInTheDocument();
  });

  it("renders rows in the order the API returns, with the API-seeded prices before any tick", async () => {
    stubFetch({
      "GET /api/watchlist": {
        body: { watchlist: [entry("AAPL", 190), entry("MSFT", 420)] },
      },
    });

    renderWithProviders(<WatchlistPanel />);

    const rows = await screen.findAllByRole("button");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent(/^AAPL/);
    expect(rows[0]).toHaveTextContent("190.00");
    expect(rows[1]).toHaveTextContent(/^MSFT/);
    expect(rows[1]).toHaveTextContent("420.00");
    expect(screen.getByText("Chg. since open")).toBeInTheDocument();
  });

  it("shows the live SSE tick price over the API-seeded price once one arrives", async () => {
    stubFetch({
      "GET /api/watchlist": { body: { watchlist: [entry("AAPL", 190)] } },
    });

    renderWithProviders(<WatchlistPanel />);
    await screen.findByRole("button", { name: /^AAPL/ });

    act(() => {
      StubEventSource.latest().emitPrices([
        {
          ticker: "AAPL",
          price: 191.5,
          previous_price: 190,
          timestamp: "2026-09-28T00:00:01Z",
          direction: "up",
        },
      ]);
    });

    expect(
      screen.getByRole("button", { name: /^AAPL/ }),
    ).toHaveTextContent("191.50");
  });

  it("shows the empty-watchlist copy when the watchlist has no tickers", async () => {
    stubFetch({ "GET /api/watchlist": { body: { watchlist: [] } } });

    renderWithProviders(<WatchlistPanel />);

    await screen.findByText("No tickers on the watchlist.");
  });

  it("shows an alert with the fetch failure status on a failed request", async () => {
    stubFetch({
      "GET /api/watchlist": { status: 500, body: { detail: "boom" } },
    });

    renderWithProviders(<WatchlistPanel />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("GET /api/watchlist failed: 500");
  });
});
