"use client";

/**
 * Ticker/quantity inputs, Buy and Sell buttons, inline error (D-01, D-02,
 * D-03). No confirmation dialog. No client-side pre-check of sufficient
 * cash/shares — `_apply_buy`/`_apply_sell` on the backend are the sole
 * validation authority (epsilon-tolerant float comparisons a duplicate
 * client check would drift from). The ticker is a free-text field, not a
 * dropdown, since `execute_trade()` accepts any ticker `is_valid_ticker()`
 * recognizes, not just watched ones.
 */

import { useState } from "react";
import { postTrade } from "@/lib/api";
import { usePortfolio } from "@/lib/portfolioStore";

type Side = "buy" | "sell";

export function TradeBar() {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { refresh } = usePortfolio();

  async function submit(side: Side) {
    if (isSubmitting) return;

    const normalizedTicker = ticker.trim().toUpperCase();
    const parsedQuantity = Number(quantity);

    setIsSubmitting(true);
    try {
      await postTrade({
        ticker: normalizedTicker,
        side,
        quantity: parsedQuantity,
      });
      setQuantity("");
      setError(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trade failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <h2 className="mb-2 text-sm font-medium text-terminal-text-muted">
        Trade
      </h2>
      <div className="flex flex-col gap-2">
        <label className="flex flex-col gap-1 text-xs text-terminal-text-muted">
          Ticker
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="AAPL"
            disabled={isSubmitting}
            className="rounded border border-terminal-border bg-terminal-bg px-2 py-1 text-sm text-terminal-text disabled:opacity-50"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-terminal-text-muted">
          Quantity
          <input
            type="number"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0"
            disabled={isSubmitting}
            className="rounded border border-terminal-border bg-terminal-bg px-2 py-1 text-sm text-terminal-text disabled:opacity-50"
          />
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => submit("buy")}
            disabled={isSubmitting}
            className="flex-1 rounded bg-accent-purple px-3 py-2 text-sm font-medium text-terminal-text disabled:opacity-50"
          >
            Buy
          </button>
          <button
            type="button"
            onClick={() => submit("sell")}
            disabled={isSubmitting}
            className="flex-1 rounded bg-accent-purple px-3 py-2 text-sm font-medium text-terminal-text disabled:opacity-50"
          >
            Sell
          </button>
        </div>
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-400" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
