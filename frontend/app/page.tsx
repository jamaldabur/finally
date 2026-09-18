"use client";

import { Header } from "@/components/header/Header";
import { TradeBar } from "@/components/trade-bar/TradeBar";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { PositionsTable } from "@/components/positions/PositionsTable";
import { ChatPanel } from "@/components/chat/ChatPanel";

// D-08 three-column shell: a full-width header band pinned at the top, a
// left rail (watchlist above the trade bar), a center/main column holding
// the positions table, and a right rail holding the AI chat panel (Plan
// 03-03) at the same w-80 width as the left rail, per 03-UI-SPEC.md's dock
// placement. Plan 02-01's single AAPL tracer readout was replaced by the
// full WatchlistPanel (Plan 02-02); the header's own portfolio-total
// readout is now Header.tsx's live-recomputed total value (Plan 02-03,
// D-05).
export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-terminal-bg text-terminal-text">
      <Header />

      <div className="flex flex-1 gap-6 p-6">
        <div className="flex w-80 flex-shrink-0 flex-col gap-4">
          <WatchlistPanel />
          <TradeBar />
        </div>

        <main className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel p-4">
          <PositionsTable />
        </main>

        <div className="w-80 flex-shrink-0">
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
