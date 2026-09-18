"use client";

/**
 * The watchlist panel: every ticker GET /api/watchlist returns, each row
 * live from the single shared SSE connection (D-05). This panel opens no
 * EventSource and does no polling of its own — `fetchWatchlist()` runs once
 * on mount purely to learn which tickers the backend is tracking and to
 * seed a pre-stream price/direction for any ticker that hasn't ticked yet.
 *
 * `watchlistRevision` (from `useChat()`) is also in this effect's dependency
 * array: it bumps whenever an assistant-requested watchlist change executes
 * (Plan 03-04), re-running the same fetch so an AI-added/removed ticker
 * appears here without a reload. Without this dependency the panel would
 * only ever reflect the watchlist as it stood at mount, breaking the
 * "manage the watchlist through natural language" capability (root
 * PLAN.md §2). This makes WatchlistPanel a consumer of the chat store, so
 * ChatProvider must remain an ancestor of the page body (see layout.tsx).
 * The effect stays a self-contained async IIFE with its own `cancelled`
 * flag — not a call to an exported callback — for the same
 * eslint-plugin-react-hooks set-state-in-effect reason recorded in
 * STATE.md for portfolioStore.tsx.
 */

import { useEffect, useState } from "react";
import { fetchWatchlist } from "@/lib/api";
import { useChat } from "@/lib/chatStore";
import { WatchlistRow } from "./WatchlistRow";
import type { WatchlistEntry } from "@/lib/types";

export function WatchlistPanel() {
  const [entries, setEntries] = useState<WatchlistEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { watchlistRevision } = useChat();

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const { watchlist } = await fetchWatchlist();
        if (!cancelled) {
          setEntries(watchlist);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Failed to load watchlist",
          );
          setEntries([]);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [watchlistRevision]);

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

      {entries !== null && error && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      {entries !== null && !error && entries.length === 0 && (
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
