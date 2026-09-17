"use client";

/**
 * One position row. Current price resolves through the same D-07 fallback
 * chain as the header's live total (shared SSE store first, the API's own
 * `current_price` for a ticker that hasn't streamed yet) and renders
 * through the shared `PriceCell` (D-12) so it flashes on the same rules as
 * the watchlist — no second flash implementation.
 *
 * `avg_cost`, `unrealized_pnl` and `pct_change` are passed straight to a
 * formatter with no arithmetic applied — `compute_portfolio_view()` already
 * rounded them to cent/basis-point precision server-side (D-04); recomputing
 * either here would leak float imprecision back in and drift from the
 * authoritative figure.
 */

import { usePriceStore } from "@/lib/priceStore";
import { PriceCell } from "@/components/ui/PriceCell";
import {
  formatCurrency,
  formatSignedCurrency,
  formatPercent,
} from "@/lib/format";
import type { PositionView } from "@/lib/types";

function gainLossClass(value: number): string {
  if (value > 0) return "text-green-400";
  if (value < 0) return "text-red-400";
  return "text-terminal-text-muted";
}

export function PositionsRow({ position }: { position: PositionView }) {
  const { prices } = usePriceStore();

  const tick = prices.get(position.ticker);
  const price = tick?.price ?? position.current_price;
  const direction = tick?.direction ?? null;

  return (
    <tr className="border-b border-terminal-border last:border-b-0">
      <td className="py-1.5 text-left font-medium text-terminal-text">
        {position.ticker}
      </td>
      <td className="py-1.5 text-right tabular-nums text-terminal-text">
        {position.quantity}
      </td>
      <td className="py-1.5 text-right tabular-nums text-terminal-text">
        {formatCurrency(position.avg_cost)}
      </td>
      <td className="py-1.5 text-right tabular-nums text-terminal-text">
        <PriceCell price={price} direction={direction} />
      </td>
      <td
        className={`py-1.5 text-right tabular-nums ${gainLossClass(position.unrealized_pnl)}`}
      >
        {formatSignedCurrency(position.unrealized_pnl)}
      </td>
      <td
        className={`py-1.5 text-right tabular-nums ${gainLossClass(position.pct_change)}`}
      >
        {formatPercent(position.pct_change)}
      </td>
    </tr>
  );
}
