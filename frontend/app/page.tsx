"use client";

import { usePortfolio } from "@/lib/portfolioStore";
import { TradeBar } from "@/components/trade-bar/TradeBar";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { PositionsTable } from "@/components/positions/PositionsTable";
import { formatCurrency } from "@/lib/format";

// D-08 single-page shell: a full-width header band pinned at the top, a
// left column (watchlist above the trade bar), and a right/main column
// reserved for the positions table (Plan 02-03). Plan 02-01's single AAPL
// tracer readout is replaced here by the full WatchlistPanel (UI-01) — the
// panel is now the live-price surface for the left column.
export default function Home() {
  const { portfolio } = usePortfolio();

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
          <WatchlistPanel />
          <TradeBar />
        </div>

        <main className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel p-4">
          <PositionsTable />
        </main>
      </div>
    </div>
  );
}
