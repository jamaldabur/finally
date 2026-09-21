"use client";

/**
 * Portfolio value history context. The backend returns `portfolio_snapshots`
 * oldest-first (ordered by recorded_at ascending); this store passes them
 * through untouched — it never sorts, filters, thins, or synthesises points.
 * Polls every 30s, matching the backend's own snapshot cadence, through one
 * provider so only one poll exists. The loading flag starts true and is
 * cleared once, never raised again (04-RESEARCH.md Pitfall 4).
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
      const next = await fetchPortfolioHistory();
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
        const next = await fetchPortfolioHistory();
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
