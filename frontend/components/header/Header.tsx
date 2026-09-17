"use client";

/**
 * Full-width header band (D-08): app name, live total value, cash balance,
 * connection dot. `cash_balance` renders straight from `GET /api/portfolio`
 * unmodified. The total value is the one sanctioned client-side recompute
 * in this phase (D-05, T-02-09): `useLiveTotalValue` sums
 * `quantity * price` over positions using the same SSE-then-API-then-cost
 * fallback chain the positions table uses, plus cash — nothing else here is
 * derived. A visible `SIMULATED` marker (T-02-10) keeps the live-looking
 * dollar figures from reading as a funded brokerage account.
 */

import { useMemo } from "react";
import { usePriceStore } from "@/lib/priceStore";
import { usePortfolio } from "@/lib/portfolioStore";
import { ConnectionDot } from "@/components/ui/ConnectionDot";
import { formatCurrency } from "@/lib/format";
import type { PositionView } from "@/lib/types";

function useLiveTotalValue(
  positions: PositionView[],
  cashBalance: number,
): number {
  const { prices } = usePriceStore();

  return useMemo(() => {
    const positionsValue = positions.reduce((sum, position) => {
      const tick = prices.get(position.ticker);
      const price = tick?.price ?? position.current_price ?? position.avg_cost;
      return sum + position.quantity * price;
    }, 0);
    return cashBalance + positionsValue;
  }, [positions, cashBalance, prices]);
}

export function Header() {
  const { status } = usePriceStore();
  const { portfolio } = usePortfolio();

  const positions = portfolio?.positions ?? [];
  const cashBalance = portfolio?.cash_balance ?? 0;
  const liveTotalValue = useLiveTotalValue(positions, cashBalance);

  return (
    <header className="flex w-full items-center justify-between border-b border-terminal-border bg-terminal-panel px-6 py-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-lg font-semibold tracking-tight text-accent-yellow">
          FinAlly
        </h1>
        <span className="rounded border border-accent-yellow/60 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent-yellow">
          Simulated
        </span>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <span className="text-terminal-text-muted">
          Total Value{" "}
          <span className="font-semibold text-terminal-text tabular-nums">
            {portfolio ? formatCurrency(liveTotalValue) : "—"}
          </span>
        </span>
        <span className="text-terminal-text-muted">
          Cash{" "}
          <span className="font-semibold text-terminal-text tabular-nums">
            {portfolio ? formatCurrency(cashBalance) : "—"}
          </span>
        </span>
        <ConnectionDot status={status} />
      </div>
    </header>
  );
}
