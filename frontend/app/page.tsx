"use client";

import { usePriceStore } from "@/lib/priceStore";
import { usePortfolio } from "@/lib/portfolioStore";
import { TradeBar } from "@/components/trade-bar/TradeBar";
import { formatCurrency } from "@/lib/format";

// D-08 single-page shell: a full-width header band pinned at the top, a
// left column (watchlist + trade bar — watchlist arrives in Plan 02-02),
// and a right/main column reserved for the positions table (Plan 02-03).
// Task 1 proved the live-price path with a single AAPL readout in the left
// column; Task 2 adds the trade bar beneath it and live cash/total value
// in the header, sourced from usePortfolio() (D-04) rather than computed
// here.
export default function Home() {
  const { prices } = usePriceStore();
  const { portfolio } = usePortfolio();
  const aapl = prices.get("AAPL");

  return (
    <div className="flex min-h-screen flex-col bg-terminal-bg text-terminal-text">
      <header className="flex w-full items-center justify-between border-b border-terminal-border bg-terminal-panel px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight text-accent-yellow">
          FinAlly
        </h1>
        <div className="flex gap-6 text-sm">
          <span className="text-terminal-text-muted">
            Total Value{" "}
            <span className="font-semibold text-terminal-text tabular-nums">
              {portfolio ? formatCurrency(portfolio.total_value) : "—"}
            </span>
          </span>
          <span className="text-terminal-text-muted">
            Cash{" "}
            <span className="font-semibold text-terminal-text tabular-nums">
              {portfolio ? formatCurrency(portfolio.cash_balance) : "—"}
            </span>
          </span>
        </div>
      </header>

      <div className="flex flex-1 gap-6 p-6">
        <div className="flex w-80 flex-shrink-0 flex-col gap-4">
          <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
            <h2 className="mb-2 text-sm font-medium text-terminal-text-muted">
              AAPL
            </h2>
            <p className="text-2xl font-semibold tabular-nums">
              {aapl ? aapl.price.toFixed(2) : "—"}
            </p>
          </section>
          <TradeBar />
        </div>

        <main className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel p-4" />
      </div>
    </div>
  );
}
