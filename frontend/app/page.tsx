"use client";

import { usePriceStore } from "@/lib/priceStore";

// D-08 single-page shell: a full-width header band pinned at the top, a
// left column (watchlist + trade bar, filled in by Plans 02-02/02-03), and
// a right/main column reserved for the positions table (Plan 02-03). This
// slice (Plan 02-01 Task 1) only proves the live-price path end to end with
// a single AAPL readout in the left column.
export default function Home() {
  const { prices } = usePriceStore();
  const aapl = prices.get("AAPL");

  return (
    <div className="flex min-h-screen flex-col bg-terminal-bg text-terminal-text">
      <header className="w-full border-b border-terminal-border bg-terminal-panel px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight text-accent-yellow">
          FinAlly
        </h1>
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
        </div>

        <main className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel p-4" />
      </div>
    </div>
  );
}
