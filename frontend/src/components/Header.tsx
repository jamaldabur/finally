import ConnectionDot from "./ConnectionDot";
import Skeleton from "./Skeleton";
import type { ConnectionStatus } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

interface HeaderProps {
  totalValue: number | null;
  cashBalance: number | null;
  status: ConnectionStatus;
}

export default function Header({ totalValue, cashBalance, status }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-border bg-surface">
      <div className="flex items-center gap-2.5">
        <span className="h-7 w-7 rounded-lg bg-accent-yellow flex items-center justify-center text-[13px] font-bold text-background" aria-hidden="true">
          F
        </span>
        <span className="text-base font-semibold tracking-tight text-foreground">FinAlly</span>
        <span className="text-xs text-muted hidden sm:inline">AI trading workstation</span>
      </div>
      <div className="flex items-center gap-7">
        <div className="text-right">
          <div className="text-xs text-muted">Portfolio value</div>
          <div className="font-tabular font-semibold text-base" data-testid="total-value">
            {totalValue === null ? <Skeleton className="h-4 w-24" /> : formatCurrency(totalValue)}
          </div>
        </div>
        <div className="text-right hidden md:block">
          <div className="text-xs text-muted">Cash</div>
          <div className="font-tabular font-semibold text-base" data-testid="cash-balance">
            {cashBalance === null ? <Skeleton className="h-4 w-24" /> : formatCurrency(cashBalance)}
          </div>
        </div>
        <ConnectionDot status={status} />
      </div>
    </header>
  );
}
