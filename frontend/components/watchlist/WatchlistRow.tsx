"use client";

/**
 * One watchlist row: ticker symbol, live price (via the shared PriceCell),
 * and a change percentage computed client-side since the page was opened
 * (D-05, D-09). The backend's tick contract carries only `price` and
 * `previous_price` — no daily open/previous close — so a session-relative
 * change is the only figure derivable here; the column header in
 * WatchlistPanel labels it accordingly.
 */

import { usePriceStore } from "@/lib/priceStore";
import { Sparkline } from "@/components/charts/Sparkline";
import { PriceCell } from "@/components/ui/PriceCell";
import { formatPercent } from "@/lib/format";
import type { WatchlistEntry } from "@/lib/types";

export function WatchlistRow({ entry }: { entry: WatchlistEntry }) {
  const { prices, firstPrices } = usePriceStore();

  const tick = prices.get(entry.ticker);
  const price = tick?.price ?? entry.price;
  const direction = tick?.direction ?? entry.direction;
  const firstPrice = firstPrices.get(entry.ticker);

  const changePct =
    price !== null && firstPrice !== undefined && firstPrice !== 0
      ? ((price - firstPrice) / firstPrice) * 100
      : null;

  return (
    <div className="flex items-center justify-between border-b border-terminal-border py-1.5 text-sm last:border-b-0">
      <span className="font-medium text-terminal-text">{entry.ticker}</span>
      <div className="mx-3 h-5 min-w-0 flex-1">
        <Sparkline ticker={entry.ticker} />
      </div>
      <div className="flex gap-4 tabular-nums">
        <PriceCell price={price} direction={direction} />
        <span
          className={
            changePct === null
              ? "text-terminal-text-muted"
              : changePct >= 0
                ? "text-green-400"
                : "text-red-400"
          }
        >
          {changePct === null ? "—" : formatPercent(changePct)}
        </span>
      </div>
    </div>
  );
}
