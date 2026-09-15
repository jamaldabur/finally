"use client";

import { useState } from "react";
import { ApiError, postTrade } from "@/lib/api";
import type { TradeSide } from "@/lib/types";

interface TradeBarProps {
  defaultTicker?: string | null;
  onTraded: () => void;
}

export default function TradeBar({ defaultTicker, onTraded }: TradeBarProps) {
  const [ticker, setTicker] = useState(defaultTicker ?? "");
  const [quantity, setQuantity] = useState("");
  const [pending, setPending] = useState<TradeSide | null>(null);
  const [feedback, setFeedback] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  async function handleTrade(side: TradeSide) {
    const qty = Number(quantity);
    const sym = ticker.trim().toUpperCase();
    if (!sym || !qty || qty <= 0) {
      setFeedback({ kind: "error", text: "Enter a ticker and a positive quantity" });
      return;
    }
    setPending(side);
    setFeedback(null);
    try {
      await postTrade({ ticker: sym, quantity: qty, side });
      setFeedback({ kind: "success", text: `${side === "buy" ? "Bought" : "Sold"} ${qty} ${sym}` });
      setQuantity("");
      onTraded();
    } catch (err) {
      setFeedback({ kind: "error", text: err instanceof ApiError ? err.message : "Trade failed" });
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-foreground">Trade</h2>
      <div className="flex flex-col gap-3">
        <div>
          <label htmlFor="trade-ticker" className="text-xs text-muted mb-1 block">
            Ticker
          </label>
          <input
            id="trade-ticker"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="AAPL"
            className="w-full bg-surface-raised border border-border rounded-lg px-3.5 py-2.5 text-sm uppercase transition-colors focus:outline-none focus:border-accent-blue focus-visible:ring-2 focus-visible:ring-accent-blue/40"
          />
        </div>
        <div>
          <label htmlFor="trade-qty" className="text-xs text-muted mb-1 block">
            Quantity
          </label>
          <input
            id="trade-qty"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0"
            type="number"
            min="0"
            step="any"
            className="w-full bg-surface-raised border border-border rounded-lg px-3.5 py-2.5 text-sm transition-colors focus:outline-none focus:border-accent-blue focus-visible:ring-2 focus-visible:ring-accent-blue/40"
          />
        </div>
        <div className="flex gap-2.5">
          <button
            onClick={() => handleTrade("buy")}
            disabled={pending !== null}
            className="flex-1 py-2.5 text-sm font-semibold rounded-lg bg-accent-purple text-white shadow-sm shadow-accent-purple/30 transition-colors hover:bg-accent-purple/90 disabled:opacity-50 disabled:hover:bg-accent-purple focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            Buy
          </button>
          <button
            onClick={() => handleTrade("sell")}
            disabled={pending !== null}
            className="flex-1 py-2.5 text-sm font-semibold rounded-lg border border-accent-purple text-accent-purple transition-colors hover:bg-accent-purple/10 disabled:opacity-50 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            Sell
          </button>
        </div>
      </div>
      {feedback && (
        <div
          className={`text-xs px-3 py-1.5 rounded-lg w-fit ${
            feedback.kind === "success" ? "bg-up/10 text-up" : "bg-down/10 text-down"
          }`}
          role="status"
        >
          {feedback.text}
        </div>
      )}
    </div>
  );
}
