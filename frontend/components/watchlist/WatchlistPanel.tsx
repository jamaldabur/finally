"use client";

/**
 * The watchlist panel: every ticker GET /api/watchlist returns, each row
 * live from the single shared SSE connection (D-05). This panel opens no
 * EventSource and does no polling of its own — `fetchWatchlist()` runs once
 * on mount purely to learn which tickers the backend is tracking and to
 * seed a pre-stream price/direction for any ticker that hasn't ticked yet.
 */

import { useEffect, useState } from "react";
import { fetchWatchlist } from "@/lib/api";
import { WatchlistRow } from "./WatchlistRow";
import type { WatchlistEntry } from "@/lib/types";

export function WatchlistPanel() {
  const [entries, setEntries] = useState<WatchlistEntry[] | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const { watchlist } = await fetchWatchlist();
        if (!cancelled) setEntries(watchlist);
      } catch {
        if (!cancelled) setEntries([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <div className="mb-2 flex items-center justify-between text-sm font-medium text-terminal-text-muted">
        <h2>Watchlist</h2>
        <span className="text-xs">Chg. since open</span>
      </div>

      {entries === null && (
        <p className="text-sm text-terminal-text-muted">
          Loading watchlist&hellip;
        </p>
      )}

      {entries !== null && entries.length === 0 && (
        <p className="text-sm text-terminal-text-muted">
          No tickers on the watchlist.
        </p>
      )}

      {entries !== null && entries.length > 0 && (
        <div className="flex flex-col">
          {entries.map((entry) => (
            <WatchlistRow key={entry.ticker} entry={entry} />
          ))}
        </div>
      )}
    </section>
  );
}
