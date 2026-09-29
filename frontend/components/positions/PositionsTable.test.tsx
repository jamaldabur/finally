/**
 * Positions table rendering tests (Phase 6, TEST-04), driven through the
 * real `PortfolioProvider` via `renderWithProviders`. Proves the table
 * displays the backend's `compute_portfolio_view()` figures verbatim in
 * every state, updates only the current-price cell on a live SSE tick, and
 * re-renders when the 5-second periodic refresh fires.
 *
 * Non-vacuity check performed for this task: temporarily changed
 * `PositionsRow.tsx`'s Unrealized P&L cell from `position.unrealized_pnl`
 * to `(price - position.avg_cost) * position.quantity` (recomputing P&L
 * from the live price). Result: the tracer case's post-tick assertion that
 * the P&L cell still reads `+$200.00` failed — the cell instead read
 * `+$250.00` (25 * 10 derived from the ticked price of 125). Restored the
 * original `position.unrealized_pnl` read; all tests passed again.
 * `PositionsRow.tsx` and `PositionsTable.tsx` are confirmed byte-identical
 * to `726046a` after restoration.
 */

import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { PositionsTable } from "@/components/positions/PositionsTable";
import { renderWithProviders } from "@/test-support/renderWithProviders";
import { stubFetch, deferred, type FetchReply } from "@/test-support/fetchStub";
import { StubEventSource } from "@/test-support/eventSourceStub";
import type { PortfolioResponse, PositionView } from "@/lib/types";

function position(
  overrides: Partial<PositionView> & Pick<PositionView, "ticker">,
): PositionView {
  return {
    quantity: 0,
    avg_cost: 0,
    current_price: null,
    market_value: 0,
    unrealized_pnl: 0,
    pct_change: 0,
    ...overrides,
  };
}

function portfolioWith(positions: PositionView[]): PortfolioResponse {
  return {
    cash_balance: 10000,
    positions,
    positions_value: 0,
    total_value: 10000,
    total_unrealized_pnl: 0,
  };
}

function tickFor(ticker: string, price: number) {
  return {
    ticker,
    price,
    previous_price: price - 1,
    timestamp: new Date().toISOString(),
    direction: "up" as const,
  };
}

const CSCO = position({
  ticker: "CSCO",
  quantity: 10,
  avg_cost: 100,
  current_price: 120,
  market_value: 1200,
  unrealized_pnl: 200,
  pct_change: 20,
});

const ORCL_LOSS = position({
  ticker: "ORCL",
  quantity: 6,
  avg_cost: 100,
  current_price: 80,
  market_value: 480,
  unrealized_pnl: -120,
  pct_change: -20,
});

afterEach(() => {
  vi.useRealTimers();
});

describe("PositionsTable", () => {
  it("tracer: renders the backend's figures verbatim and never recomputes P&L from a live tick", async () => {
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([CSCO]) } });

    renderWithProviders(<PositionsTable />);

    const row = await screen.findByRole("row", { name: /^CSCO/ });
    const cells = within(row).getAllByRole("cell");

    expect(cells[0]).toHaveTextContent("CSCO");
    expect(cells[1]).toHaveTextContent("10");
    expect(cells[2]).toHaveTextContent("$100.00");
    expect(cells[3]).toHaveTextContent("120.00");
    expect(cells[4]).toHaveTextContent("+$200.00");
    expect(cells[4]).toHaveClass("text-green-400");
    expect(cells[5]).toHaveTextContent("+20.00%");
    expect(cells[5]).toHaveClass("text-green-400");

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("CSCO", 125)]);
    });

    // Current-price cell updates from the tick...
    expect(cells[3]).toHaveTextContent("125.00");
    // ...but P&L and percent cells still show the server's original figures,
    // proving the frontend never recomputes P&L from the live price.
    expect(cells[4]).toHaveTextContent("+$200.00");
    expect(cells[5]).toHaveTextContent("+20.00%");
  });

  it("shows the loading state while the portfolio request is pending", async () => {
    const portfolioDeferred = deferred<FetchReply>();
    stubFetch({ "GET /api/portfolio": () => portfolioDeferred.promise });

    renderWithProviders(<PositionsTable />);

    expect(screen.getByText("Loading positions…")).toBeInTheDocument();

    await act(async () => {
      portfolioDeferred.resolve({ body: portfolioWith([]) });
      await portfolioDeferred.promise;
    });
  });

  it("shows the empty state when there are no positions", async () => {
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([]) } });

    renderWithProviders(<PositionsTable />);

    expect(
      await screen.findByText(
        "No positions held yet — place a trade from the trade bar to get started.",
      ),
    ).toBeInTheDocument();
  });

  it("shows the error state on a failed portfolio request", async () => {
    stubFetch({ "GET /api/portfolio": { status: 500 } });

    renderWithProviders(<PositionsTable />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("GET /api/portfolio failed: 500");
  });

  it("renders a loss with the loss colour", async () => {
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([ORCL_LOSS]) } });

    renderWithProviders(<PositionsTable />);

    const row = await screen.findByRole("row", { name: /^ORCL/ });
    const cells = within(row).getAllByRole("cell");

    expect(cells[4]).toHaveTextContent("-$120.00");
    expect(cells[4]).toHaveClass("text-red-400");
    expect(cells[5]).toHaveTextContent("-20.00%");
    expect(cells[5]).toHaveClass("text-red-400");
  });

  it("renders a flat position muted", async () => {
    const flat = position({
      ticker: "FLAT",
      quantity: 5,
      avg_cost: 50,
      current_price: 50,
      market_value: 250,
      unrealized_pnl: 0,
      pct_change: 0,
    });
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([flat]) } });

    renderWithProviders(<PositionsTable />);

    const row = await screen.findByRole("row", { name: /^FLAT/ });
    const cells = within(row).getAllByRole("cell");

    expect(cells[4]).toHaveTextContent("+$0.00");
    expect(cells[4]).toHaveClass("text-terminal-text-muted");
    expect(cells[5]).toHaveTextContent("+0.00%");
    expect(cells[5]).toHaveClass("text-terminal-text-muted");
  });

  it("renders an em-dash in the current-price cell when unpriced and no tick has arrived", async () => {
    const unpriced = position({
      ticker: "UNPR",
      quantity: 1,
      avg_cost: 10,
      current_price: null,
      market_value: 0,
      unrealized_pnl: 0,
      pct_change: 0,
    });
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([unpriced]) } });

    renderWithProviders(<PositionsTable />);

    const row = await screen.findByRole("row", { name: /^UNPR/ });
    const cells = within(row).getAllByRole("cell");
    expect(cells[3]).toHaveTextContent("—");
  });

  it("renders a fractional quantity verbatim", async () => {
    const fractional = position({
      ticker: "FRAC",
      quantity: 0.5,
      avg_cost: 10,
      current_price: 10,
      market_value: 5,
      unrealized_pnl: 0,
      pct_change: 0,
    });
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([fractional]) } });

    renderWithProviders(<PositionsTable />);

    const row = await screen.findByRole("row", { name: /^FRAC/ });
    const cells = within(row).getAllByRole("cell");
    expect(cells[1]).toHaveTextContent("0.5");
  });

  it("renders positions in the order the response lists them", async () => {
    stubFetch({
      "GET /api/portfolio": { body: portfolioWith([CSCO, ORCL_LOSS]) },
    });

    renderWithProviders(<PositionsTable />);

    await screen.findByRole("row", { name: /^CSCO/ });
    const rows = screen.getAllByRole("row");
    // rows[0] is the header row.
    expect(rows[1]).toHaveTextContent(/^CSCO/);
    expect(rows[2]).toHaveTextContent(/^ORCL/);
  });

  it("shows all six column headers", async () => {
    stubFetch({ "GET /api/portfolio": { body: portfolioWith([CSCO]) } });

    renderWithProviders(<PositionsTable />);
    await screen.findByRole("row", { name: /^CSCO/ });

    for (const header of [
      "Ticker",
      "Quantity",
      "Avg Cost",
      "Current Price",
      "Unrealized P&L",
      "Chg %",
    ]) {
      expect(screen.getByText(header)).toBeInTheDocument();
    }
  });

  it("re-renders from the periodic 5-second portfolio refresh", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });

    stubFetch({
      "GET /api/portfolio": [
        { body: portfolioWith([CSCO]) },
        {
          body: portfolioWith([
            position({
              ticker: "CSCO",
              quantity: 10,
              avg_cost: 100,
              current_price: 120,
              market_value: 1200,
              unrealized_pnl: 250,
              pct_change: 25,
            }),
          ]),
        },
      ],
    });

    renderWithProviders(<PositionsTable />);

    const row = await screen.findByRole("row", { name: /^CSCO/ });
    expect(within(row).getAllByRole("cell")[4]).toHaveTextContent("+$200.00");

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    await waitFor(() => {
      expect(within(row).getAllByRole("cell")[4]).toHaveTextContent("+$250.00");
    });
    expect(within(row).getAllByRole("cell")[5]).toHaveTextContent("+25.00%");
  });
});
