"use client";

/**
 * Portfolio value history context. This store requests a bounded,
 * most-recent window (HISTORY_POINT_LIMIT) rather than the entire recorded
 * table — a server-side window stops the response body itself from growing
 * without limit, which the never-pruned portfolio_snapshots table would
 * otherwise guarantee. What arrives within that window is still passed
 * through untouched: this store never sorts, filters, thins, or synthesises
 * points, and the backend still returns them oldest-first (ordered by
 * insertion order ascending). Polls every 30s, matching the backend's own
 * snapshot cadence, through one provider so only one poll exists. The
 * loading flag starts true and is cleared once, never raised again
 * (04-RESEARCH.md Pitfall 4).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fetchPortfolioHistory } from "./api";
import type { PortfolioHistoryResponse } from "./types";

const HISTORY_REFRESH_INTERVAL_MS = 30000;

// The Portfolio Value panel's plot area is roughly 190-430px wide; the main
// chart, which shares every style constant with this one (chartTheme.ts),
// reads cleanly at about 0.46 points per horizontal pixel. 180 points across
// that width is 0.42-0.94 points/px — the same regime, against the 5-11
// points/px that merged adjacent 2px strokes into an ink band several times
// their nominal weight (G-04-4 root cause). At the backend's 30-second
// recording cadence this is roughly the last ninety minutes of activity;
// PnlHistoryChart's time-scaled X axis makes that window self-evident from
// the tick labels, so no extra copy is needed to state it.
const HISTORY_POINT_LIMIT = 180;

type PortfolioHistoryStoreValue = {
  history: PortfolioHistoryResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const PortfolioHistoryContext =
  createContext<PortfolioHistoryStoreValue | null>(null);

export function PortfolioHistoryProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [history, setHistory] = useState<PortfolioHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Read synchronously before any await so a slow response cannot overlap
  // the next interval tick.
  const isRefreshingRef = useRef(false);

  const refresh = useCallback(async () => {
    if (isRefreshingRef.current) return;
    isRefreshingRef.current = true;
    try {
      const next = await fetchPortfolioHistory(HISTORY_POINT_LIMIT);
      setHistory(next);
      setError(null);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to load portfolio history",
      );
    } finally {
      setLoading(false);
      isRefreshingRef.current = false;
    }
  }, []);

  // Inline mount effect (not a call to `refresh`) so the "setState in
  // effect" lint rule sees a self-contained async fetch-and-set.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchPortfolioHistory(HISTORY_POINT_LIMIT);
        if (cancelled) return;
        setHistory(next);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(
          e instanceof Error ? e.message : "Failed to load portfolio history",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      void refresh();
    }, HISTORY_REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <PortfolioHistoryContext.Provider
      value={{ history, loading, error, refresh }}
    >
      {children}
    </PortfolioHistoryContext.Provider>
  );
}

export function usePortfolioHistory(): PortfolioHistoryStoreValue {
  const ctx = useContext(PortfolioHistoryContext);
  if (!ctx) {
    throw new Error(
      "usePortfolioHistory must be used within PortfolioHistoryProvider",
    );
  }
  return ctx;
}
