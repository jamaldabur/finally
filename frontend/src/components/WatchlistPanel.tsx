"use client";

import { useState } from "react";
import { useMarketData } from "@/lib/marketData";
import { addToWatchlist, ApiError, removeFromWatchlist } from "@/lib/api";
import { formatCurrency, formatPercent, pctChange } from "@/lib/format";
import FlashPrice from "./FlashPrice";
import Sparkline from "./Sparkline";
import Skeleton from "./Skeleton";

interface WatchlistPanelProps {
  tickers: string[];
  selected: string | null;
  onSelect: (ticker: string) => void;
  onWatchlistChanged: (tickers: string[]) => void;
}

export default function WatchlistPanel({
  tickers,
  selected,
  onSelect,
  onWatchlistChanged,
}: WatchlistPanelProps) {
  const { prices, history } = useMarketData();
  const [newTicker, setNewTicker] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker) return;
    setPending(true);
    setError(null);
    try {
      await addToWatchlist(ticker);
      onWatchlistChanged([...tickers, ticker]);
      setNewTicker("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add ticker");
    } finally {
      setPending(false);
    }
  }

  async function handleRemove(ticker: string) {
    try {
      await removeFromWatchlist(ticker);
      onWatchlistChanged(tickers.filter((t) => t !== ticker));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove ticker");
    }
  }

  return (
    <div className="flex flex-col h-full min-w-0 overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-2">
        <h2 className="text-sm font-semibold text-foreground shrink-0">Watchlist</h2>
        <form onSubmit={handleAdd} className="flex gap-2 flex-1 min-w-0 max-w-xs ml-auto">
          <input
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value)}
            placeholder="Add ticker…"
            className="flex-1 min-w-0 bg-surface-raised border border-border rounded-lg px-3 py-1 text-sm uppercase transition-colors focus:outline-none focus:border-accent-blue focus-visible:ring-2 focus-visible:ring-accent-blue/40"
          />
          <button
            type="submit"
            disabled={pending}
            className="px-3 py-1 text-sm font-medium rounded-lg bg-accent-blue text-white transition-colors hover:bg-accent-blue/85 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            Add
          </button>
        </form>
      </div>
      {error && (
        <div className="mx-4 mb-1 px-3 py-1 rounded-lg bg-down/10 text-xs text-down" role="alert">
          {error}
        </div>
      )}

      <div className="flex-1 min-w-0 overflow-y-auto overflow-x-auto">
        <table className="w-full min-w-[360px] text-sm">
          <thead className="sticky top-0 bg-surface text-muted text-xs">
            <tr>
              <th className="text-left px-4 py-1.5 font-medium border-b border-border">Ticker</th>
              <th className="text-right px-4 py-1.5 font-medium border-b border-border">Price</th>
              <th className="text-right px-4 py-1.5 font-medium border-b border-border">Chg %</th>
              <th className="text-right px-4 py-1.5 font-medium border-b border-border">Trend</th>
              <th className="px-2 py-1.5 border-b border-border" />
            </tr>
          </thead>
          <tbody>
            {tickers.map((ticker) => {
              const tick = prices[ticker];
              const points = history[ticker] ?? [];
              const changePct =
                tick && tick.previous_price ? pctChange(tick.price, tick.previous_price) : 0;
              return (
                <tr
                  key={ticker}
                  onClick={() => onSelect(ticker)}
                  data-testid={`watchlist-row-${ticker}`}
                  className={`group cursor-pointer border-b border-l-[3px] border-border/60 transition-colors hover:bg-surface-raised ${
                    selected === ticker ? "border-l-accent-blue bg-accent-blue/[0.07]" : "border-l-transparent"
                  }`}
                >
                  <td className="px-4 py-1.5 font-semibold">{ticker}</td>
                  <td className="px-4 py-1.5 text-right font-tabular">
                    {tick ? (
                      <FlashPrice price={tick.price} direction={tick.direction} format={formatCurrency} />
                    ) : (
                      <Skeleton className="h-4 w-16" />
                    )}
                  </td>
                  <td
                    className={`px-4 py-1.5 text-right font-tabular font-medium ${
                      changePct > 0 ? "text-up" : changePct < 0 ? "text-down" : "text-muted"
                    }`}
                  >
                    {tick ? formatPercent(changePct) : <Skeleton className="h-4 w-10 ml-auto" />}
                  </td>
                  <td className="px-4 py-1.5">
                    {points.length >= 2 || tick ? (
                      <Sparkline data={points} direction={tick?.direction ?? "unchanged"} />
                    ) : (
                      <Skeleton className="h-4 w-16" />
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemove(ticker);
                      }}
                      aria-label={`Remove ${ticker}`}
                      className="opacity-40 group-hover:opacity-100 text-muted hover:text-down text-xs px-1.5 py-1 rounded-md transition focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-down"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
