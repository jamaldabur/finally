/**
 * Header live-total and cash rendering tests (Phase 6, TEST-04), driven
 * through the real provider tree via `renderWithProviders`. Covers the
 * loading placeholders, the three-level current-price fallback chain
 * (streamed tick -> `current_price` -> `avg_cost`), live recompute on SSE
 * ticks, the connection label, and the float-noise precision contract.
 */

import { act, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Header } from "@/components/header/Header";
import { renderWithProviders } from "@/test-support/renderWithProviders";
import { stubFetch, deferred, type FetchReply } from "@/test-support/fetchStub";
import { StubEventSource } from "@/test-support/eventSourceStub";
import type { PortfolioResponse } from "@/lib/types";

const PORTFOLIO_FIXTURE: PortfolioResponse = {
  cash_balance: 9000,
  positions: [
    {
      ticker: "CSCO",
      quantity: 10,
      avg_cost: 100,
      current_price: 120,
      market_value: 1200,
      unrealized_pnl: 200,
      pct_change: 20,
    },
    {
      ticker: "ORCL",
      quantity: 2,
      avg_cost: 50,
      current_price: null,
      market_value: 100,
      unrealized_pnl: 0,
      pct_change: 0,
    },
  ],
  positions_value: 1300,
  total_value: 10300,
  total_unrealized_pnl: 200,
};

function tickFor(ticker: string, price: number) {
  return {
    ticker,
    price,
    previous_price: price - 1,
    timestamp: new Date().toISOString(),
    direction: "up" as const,
  };
}

describe("Header", () => {
  it("shows loading placeholders and a reconnecting dot while the portfolio request is pending", async () => {
    const portfolioDeferred = deferred<FetchReply>();
    stubFetch({ "GET /api/portfolio": () => portfolioDeferred.promise });

    renderWithProviders(<Header />);

    // Two "-" placeholders: Total Value and Cash.
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(screen.getByText("Reconnecting")).toBeInTheDocument();

    await act(async () => {
      portfolioDeferred.resolve({ body: PORTFOLIO_FIXTURE });
      await portfolioDeferred.promise;
    });
  });

  it("renders cash exactly as returned and the fallback-chain total, distinguishing the two figures", async () => {
    stubFetch({ "GET /api/portfolio": { body: PORTFOLIO_FIXTURE } });

    renderWithProviders(<Header />);

    await screen.findByText("$9000.00");
    expect(screen.getByText("$9000.00")).toBeInTheDocument();

    // CSCO priced at current_price (120 * 10 = 1200); ORCL has no
    // current_price so falls back to avg_cost (50 * 2 = 100).
    // Total: 9000 (cash) + 1200 + 100 = 10300.
    const totalLine = screen.getByText("Total Value").closest("span");
    expect(totalLine).toHaveTextContent("Total Value $10300.00");
  });

  it("shows Connected once the SSE connection opens", async () => {
    stubFetch({ "GET /api/portfolio": { body: PORTFOLIO_FIXTURE } });
    renderWithProviders(<Header />);
    await screen.findByText("$9000.00");

    act(() => {
      StubEventSource.latest().open();
    });

    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("recomputes the live total on a CSCO tick while cash stays fixed", async () => {
    stubFetch({ "GET /api/portfolio": { body: PORTFOLIO_FIXTURE } });
    renderWithProviders(<Header />);
    await screen.findByText("$9000.00");

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("CSCO", 130)]);
    });

    // 9000 + 130*10 + 100 (ORCL avg_cost fallback) = 10400.
    const totalLine = screen.getByText("Total Value").closest("span");
    expect(totalLine).toHaveTextContent("Total Value $10400.00");
    expect(screen.getByText("$9000.00")).toBeInTheDocument();
  });

  it("recomputes again on a subsequent ORCL tick", async () => {
    stubFetch({ "GET /api/portfolio": { body: PORTFOLIO_FIXTURE } });
    renderWithProviders(<Header />);
    await screen.findByText("$9000.00");

    act(() => {
      StubEventSource.latest().emitPrices([tickFor("CSCO", 130)]);
    });
    act(() => {
      StubEventSource.latest().emitPrices([tickFor("ORCL", 55)]);
    });

    // 9000 + 130*10 + 55*2 = 10410.
    const totalLine = screen.getByText("Total Value").closest("span");
    expect(totalLine).toHaveTextContent("Total Value $10410.00");
  });

  it("renders a float-noisy sum to the cent, never a float-noise string", async () => {
    const floatFixture: PortfolioResponse = {
      cash_balance: 9000.1,
      positions: [
        {
          ticker: "CSCO",
          quantity: 3,
          avg_cost: 0.1,
          current_price: 0.1,
          market_value: 0.3,
          unrealized_pnl: 0,
          pct_change: 0,
        },
      ],
      positions_value: 0.3,
      total_value: 9000.4,
      total_unrealized_pnl: 0,
    };
    stubFetch({ "GET /api/portfolio": { body: floatFixture } });

    renderWithProviders(<Header />);
    await screen.findByText("$9000.10");

    const totalLine = screen.getByText("Total Value").closest("span");
    expect(totalLine).toHaveTextContent("Total Value $9000.40");
  });
});
