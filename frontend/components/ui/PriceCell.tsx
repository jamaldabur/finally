"use client";

/**
 * The one shared flash-on-real-change price cell (D-12). Used by the
 * watchlist rows here and by Plan 02-03's positions table — there is
 * exactly one flash implementation in the codebase.
 *
 * Flash trigger correction (see 02-02-PLAN.md `<flash_trigger_correction>`):
 * `PriceCache.update()` (backend/app/market/cache.py) keeps the OLD
 * `previous_price` on an unchanged heartbeat, so `price !== previous_price`
 * on the tick itself stays true forever after the first real move and is
 * NOT a valid flash trigger. Instead this component tracks the price it
 * last rendered in a `useRef` and flashes only when the incoming `price`
 * differs from that ref — a comparison against this cell's own render
 * history, not against the tick's `previous_price` field.
 */

import { useEffect, useRef, useState } from "react";

type Direction = "up" | "down" | "unchanged" | null;

export function PriceCell({
  price,
  direction,
}: {
  price: number | null;
  direction: Direction;
}) {
  const [flashClass, setFlashClass] = useState("");
  const lastPrice = useRef<number | null>(null);

  useEffect(() => {
    if (price === null) return;

    if (lastPrice.current !== null && price !== lastPrice.current) {
      setFlashClass(direction === "up" ? "bg-green-500/30" : "bg-red-500/30");
      const timer = setTimeout(() => setFlashClass(""), 500);
      lastPrice.current = price;
      return () => clearTimeout(timer);
    }

    lastPrice.current = price;
  }, [price, direction]);

  return (
    <span className={`transition-colors duration-500 ${flashClass}`}>
      {price !== null ? price.toFixed(2) : "—"}
    </span>
  );
}
