/**
 * One inline outcome pill for a single LLM-requested trade or watchlist
 * change (03-UI-SPEC.md Copywriting Contract, CHAT-04). The badge's color,
 * glyph, and `role="alert"` are driven solely by `action.outcome` — the
 * field the backend computed from the real trade/watchlist result. Nothing
 * here reads, parses, or is influenced by the model's own `message` prose
 * (T-03-15), and `action.reason` is rendered as JSX children with no JS
 * string transformation applied (T-03-16) — it is the backend's own verbatim
 * text, not a rephrased or generic substitute.
 */

import type { TradeAction, WatchlistAction } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

type ActionBadgeProps =
  | { kind: "trade"; action: TradeAction }
  | { kind: "watchlist"; action: WatchlistAction };

export function ActionBadge(props: ActionBadgeProps) {
  const { action } = props;
  const executed = action.outcome === "executed";
  const glyph = executed ? "✓" : "✕";

  let label: string;
  if (props.kind === "trade") {
    const { side, quantity, ticker, price } = props.action;
    if (executed) {
      // price is expected non-null on an executed trade; the fallback
      // omits the fill-price suffix rather than ever rendering "null".
      const priceSuffix = price !== null ? ` @ ${formatCurrency(price)}` : "";
      label = `${glyph} ${side} ${quantity} ${ticker}${priceSuffix}`;
    } else {
      label = `${glyph} ${side} ${quantity} ${ticker}`;
    }
  } else {
    const { ticker, action: watchlistAction } = props.action;
    if (executed) {
      label =
        watchlistAction === "add"
          ? `${glyph} Added ${ticker} to watchlist`
          : `${glyph} Removed ${ticker} from watchlist`;
    } else {
      label =
        watchlistAction === "add"
          ? `${glyph} Add ${ticker}`
          : `${glyph} Remove ${ticker}`;
    }
  }

  const colorClasses = executed
    ? "text-gain bg-gain/10 border border-gain/30"
    : "text-red-400 bg-red-400/10 border border-red-400/30";

  return (
    <div
      className={`inline-flex max-w-full items-center gap-1 rounded-full px-2 py-0.5 ${colorClasses}`}
      role={executed ? undefined : "alert"}
    >
      {/* Label span keeps the full Micro/Badge treatment (10px/600/uppercase/
          tracking-wide, matching the Header's existing "Simulated" badge).
          Side is rendered lowercase in the string and appears uppercase only
          via this span's CSS text-transform — the value itself is never
          transformed. */}
      <span className="text-[10px] font-semibold uppercase tracking-wide">
        {label}
      </span>
      {!executed && action.reason !== null && (
        // Deliberate, documented refinement of the UI-SPEC's single
        // Micro/Badge role for this element: uppercasing a full verbatim
        // rejection sentence (e.g. a cash-sufficiency reason) would make the
        // one string the user most needs to read the least readable. The
        // UI-SPEC's own verbatim-reason requirement is the stronger
        // constraint here, so this segment renders normal-case at the same
        // size instead (03-04-PLAN.md planner_assumptions #1).
        <span className="max-w-full break-words text-[10px] font-normal normal-case">
          {" — "}
          {action.reason}
        </span>
      )}
    </div>
  );
}
