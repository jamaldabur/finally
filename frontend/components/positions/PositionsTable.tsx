"use client";

/**
 * The positions table: one row per held position (ticker, quantity, avg
 * cost, current price, unrealized P&L, % change — UI-06). Reads from the
 * same `PortfolioProvider` the trade bar refreshes after a fill (D-04); the
 * backend's `compute_portfolio_view()` is the sole authority for every
 * column except the live current-price cell.
 */

import { usePortfolio } from "@/lib/portfolioStore";
import { PositionsRow } from "./PositionsRow";

export function PositionsTable() {
  const { portfolio, loading, error } = usePortfolio();

  return (
    <section className="flex h-full flex-col">
      <h2 className="mb-2 text-sm font-medium text-terminal-text-muted">
        Positions
      </h2>

      {loading && !portfolio && (
        <p className="text-sm text-terminal-text-muted">
          Loading positions&hellip;
        </p>
      )}

      {!loading && error && !portfolio && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      {portfolio && portfolio.positions.length === 0 && (
        <p className="text-sm text-terminal-text-muted">
          No positions held yet — place a trade from the trade bar to get
          started.
        </p>
      )}

      {portfolio && portfolio.positions.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-terminal-border text-xs text-terminal-text-muted">
              <th className="py-1.5 text-left font-medium">Ticker</th>
              <th className="py-1.5 text-right font-medium">Quantity</th>
              <th className="py-1.5 text-right font-medium">Avg Cost</th>
              <th className="py-1.5 text-right font-medium">
                Current Price
              </th>
              <th className="py-1.5 text-right font-medium">
                Unrealized P&L
              </th>
              <th className="py-1.5 text-right font-medium">Chg %</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.positions.map((position) => (
              <PositionsRow key={position.ticker} position={position} />
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
