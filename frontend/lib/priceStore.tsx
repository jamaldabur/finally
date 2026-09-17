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
 * Connection status: `onopen` and every `prices` event set `'connected'`.
 * For this slice, `onerror` sets `'reconnecting'` and nothing else — the
 * grace-window promotion to `'disconnected'` (D-06) is Plan 02-03's
 * connection-dot task, not this one.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { PriceTick, PricesEvent } from "./types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

type PriceStoreValue = {
  prices: Map<string, PriceTick>;
  firstPrices: Map<string, number>;
  status: ConnectionStatus;
};

const PriceStoreContext = createContext<PriceStoreValue | null>(null);

export function PriceStoreProvider({ children }: { children: ReactNode }) {
  const [prices, setPrices] = useState<Map<string, PriceTick>>(new Map());
  const [firstPrices, setFirstPrices] = useState<Map<string, number>>(
    new Map(),
  );
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    const es = new EventSource(`${base}/api/stream/prices`);

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
      setStatus("connected");
    });

    es.onopen = () => setStatus("connected");
    es.onerror = () => setStatus("reconnecting");

    return () => es.close();
  }, []);

  return (
    <PriceStoreContext.Provider value={{ prices, firstPrices, status }}>
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
