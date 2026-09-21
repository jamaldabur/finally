"use client";

/**
 * The single shared SSE connection for the whole app (D-05). Exactly one
 * `EventSource` is opened against `/api/stream/prices` here; every
 * price-dependent component (watchlist rows, header total, positions table)
 * reads from this context instead of constructing its own connection.
 *
 * The backend emits a *named* SSE event (`event: prices`, see
 * backend/app/routes/stream.py) rather than the default unnamed `message`
 * event, so subscription must use `addEventListener('prices', ...)` — the
 * default `onmessage` handler would never fire.
 *
 * `firstPrices` records the first price observed per ticker since page
 * load; it exists here (rather than being derived downstream) because this
 * store is the only place that sees every tick — a later watchlist
 * change-% column needs it (Plan 02-02).
 *
 * Connection status (D-06, completed in Plan 02-03): `onopen` and every
 * `prices` event set `'connected'` and clear any pending grace timer.
 * `onerror` sets `'reconnecting'` — the browser is already retrying on its
 * own, which is exactly why native `EventSource` was chosen (PLAN.md §6) —
 * then clears any existing grace timer and arms exactly one new 5-second
 * timer that sets `'disconnected'` only if the connection is still not
 * open when it fires. Clearing before arming keeps at most one timer
 * pending at a time, so a burst of interleaved error/recovery events can
 * never leave the dot red while the stream is actually live.
 */

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { PriceTick, PricesEvent } from "./types";

// Grace window before a lost connection is reported as fully disconnected
// (D-06 / A2 in 02-RESEARCH.md — a starting point, not a locked value).
const DISCONNECT_GRACE_MS = 5000;

// Per-ticker cap on the sparkline/chart history buffer. The buffer is
// ephemeral and per-session (rebuilt on every page load), so it is bounded to
// keep a long-running tab from growing memory without limit (UI-SPEC).
const PRICE_HISTORY_LIMIT = 500;

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export type PricePoint = { timestamp: string; price: number };

type PriceStoreValue = {
  prices: Map<string, PriceTick>;
  firstPrices: Map<string, number>;
  priceHistory: Map<string, PricePoint[]>;
  status: ConnectionStatus;
};

const PriceStoreContext = createContext<PriceStoreValue | null>(null);

export function PriceStoreProvider({ children }: { children: ReactNode }) {
  const [prices, setPrices] = useState<Map<string, PriceTick>>(new Map());
  const [firstPrices, setFirstPrices] = useState<Map<string, number>>(
    new Map(),
  );
  const [priceHistory, setPriceHistory] = useState<Map<string, PricePoint[]>>(
    new Map(),
  );
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");
  const graceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    const es = new EventSource(`${base}/api/stream/prices`);

    const clearGraceTimer = () => {
      if (graceTimer.current) {
        clearTimeout(graceTimer.current);
        graceTimer.current = null;
      }
    };

    es.addEventListener("prices", (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as PricesEvent;
      setPrices((prev) => {
        const next = new Map(prev);
        for (const tick of payload.ticks) next.set(tick.ticker, tick);
        return next;
      });
      setFirstPrices((prev) => {
        let changed = false;
        const next = new Map(prev);
        for (const tick of payload.ticks) {
          if (!next.has(tick.ticker)) {
            next.set(tick.ticker, tick.price);
            changed = true;
          }
        }
        return changed ? next : prev;
      });
      setPriceHistory((prev) => {
        let changed = false;
        const next = new Map(prev);
        for (const tick of payload.ticks) {
          const series = next.get(tick.ticker) ?? [];
          const last = series[series.length - 1];
          // Append only on a real change versus the last recorded point.
          // The tick's own prior-price field is unusable here.
          // The cache holds it steady across unchanged heartbeats.
          if (last === undefined || last.price !== tick.price) {
            const appended = [
              ...series,
              { timestamp: tick.timestamp, price: tick.price },
            ];
            next.set(
              tick.ticker,
              appended.length > PRICE_HISTORY_LIMIT
                ? appended.slice(appended.length - PRICE_HISTORY_LIMIT)
                : appended,
            );
            changed = true;
          }
        }
        return changed ? next : prev;
      });
      setStatus("connected");
      clearGraceTimer();
    });

    es.onopen = () => {
      setStatus("connected");
      clearGraceTimer();
    };

    es.onerror = () => {
      setStatus("reconnecting");
      clearGraceTimer();
      graceTimer.current = setTimeout(() => {
        if (es.readyState !== EventSource.OPEN) {
          setStatus("disconnected");
        }
      }, DISCONNECT_GRACE_MS);
    };

    return () => {
      clearGraceTimer();
      es.close();
    };
  }, []);

  return (
    <PriceStoreContext.Provider value={{ prices, firstPrices, priceHistory, status }}>
      {children}
    </PriceStoreContext.Provider>
  );
}

export function usePriceStore(): PriceStoreValue {
  const ctx = useContext(PriceStoreContext);
  if (!ctx) {
    throw new Error("usePriceStore must be used within PriceStoreProvider");
  }
  return ctx;
}
