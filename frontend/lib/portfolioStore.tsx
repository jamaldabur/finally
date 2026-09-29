"use client";

/**
 * Portfolio context. `compute_portfolio_view()` on the backend is the sole
 * authority for cash, average cost, unrealized P&L and percent change
 * (D-04) — this store never derives, adjusts, or patches any of those
 * values locally, not even from a successful trade response. `refresh()`
 * (a `fetchPortfolio()` call) is the only way portfolio state ever
 * changes.
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
import { fetchPortfolio } from "./api";
import type { PortfolioResponse } from "./types";

// Keeps the server-authoritative unrealized_pnl/pct_change columns roughly
// current between trades, without polling on every 0.5s SSE tick (D-04,
// D-05 — the header's live total covers per-tick responsiveness instead).
const REFRESH_INTERVAL_MS = 5000;

type PortfolioStoreValue = {
  portfolio: PortfolioResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const PortfolioContext = createContext<PortfolioStoreValue | null>(null);

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Guards against the 5-second interval firing a second refresh() while
  // one is still in flight (e.g. a slow response overlapping the next tick)
  // — not React state, since it must be read synchronously inside the same
  // call, before any await.
  const isRefreshingRef = useRef(false);

  const refresh = useCallback(async () => {
    if (isRefreshingRef.current) return;
    isRefreshingRef.current = true;
    try {
      const next = await fetchPortfolio();
      setPortfolio(next);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
      isRefreshingRef.current = false;
    }
  }, []);

  // Mount-only fetch, written as its own inline effect (not a call to the
  // exported `refresh`) so the lint rule that flags "setState in effect"
  // sees a self-contained async fetch-and-set rather than a call through an
  // intermediate function reference. `refresh()` itself is the only way
  // portfolio state changes after mount (D-04) — this effect exists solely
  // to seed the initial load.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchPortfolio();
        if (cancelled) return;
        setPortfolio(next);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load portfolio");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Periodic refresh (Task 1, 02-03-PLAN.md): keeps unrealized_pnl/
  // pct_change roughly current between trades. 5s is deliberately far
  // slower than the 0.5s SSE cadence — polling GET /api/portfolio on every
  // tick would duplicate the header's live total (D-05).
  useEffect(() => {
    const interval = setInterval(() => {
      void refresh();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <PortfolioContext.Provider value={{ portfolio, loading, error, refresh }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio(): PortfolioStoreValue {
  const ctx = useContext(PortfolioContext);
  if (!ctx) {
    throw new Error("usePortfolio must be used within PortfolioProvider");
  }
  return ctx;
}
