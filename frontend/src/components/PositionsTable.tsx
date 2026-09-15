import type { Position } from "@/lib/types";
import { formatCurrency, formatPercent, formatQuantity } from "@/lib/format";

export default function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <div className="h-full min-w-0 overflow-hidden flex flex-col">
      <div className="px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Positions</h2>
      </div>
      <div className="flex-1 min-w-0 overflow-y-auto overflow-x-auto">
        {positions.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted text-sm p-4">
            No open positions yet — place a trade to get started.
          </div>
        ) : (
          <table className="w-full min-w-[480px] text-sm">
            <thead className="sticky top-0 bg-surface text-muted text-xs">
              <tr>
                <th className="text-left px-4 py-2 font-medium border-b border-border">Ticker</th>
                <th className="text-right px-4 py-2 font-medium border-b border-border">Qty</th>
                <th className="text-right px-4 py-2 font-medium border-b border-border">Avg cost</th>
                <th className="text-right px-4 py-2 font-medium border-b border-border">Price</th>
                <th className="text-right px-4 py-2 font-medium border-b border-border">P&amp;L</th>
                <th className="text-right px-4 py-2 font-medium border-b border-border">%</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr
                  key={p.ticker}
                  data-testid={`position-row-${p.ticker}`}
                  className="border-b border-border/50 transition-colors hover:bg-surface-raised"
                >
                  <td className="px-4 py-2.5 font-semibold">{p.ticker}</td>
                  <td className="px-4 py-2.5 text-right font-tabular">{formatQuantity(p.quantity)}</td>
                  <td className="px-4 py-2.5 text-right font-tabular">{formatCurrency(p.avg_cost)}</td>
                  <td className="px-4 py-2.5 text-right font-tabular">{formatCurrency(p.current_price)}</td>
                  <td
                    className={`px-4 py-2.5 text-right font-tabular font-medium ${
                      p.unrealized_pnl > 0 ? "text-up" : p.unrealized_pnl < 0 ? "text-down" : "text-muted"
                    }`}
                  >
                    {formatCurrency(p.unrealized_pnl)}
                  </td>
                  <td
                    className={`px-4 py-2.5 text-right font-tabular font-medium ${
                      p.unrealized_pnl_pct > 0 ? "text-up" : p.unrealized_pnl_pct < 0 ? "text-down" : "text-muted"
                    }`}
                  >
                    {formatPercent(p.unrealized_pnl_pct * 100)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
