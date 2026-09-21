"use client";

import { Header } from "@/components/header/Header";
import { TradeBar } from "@/components/trade-bar/TradeBar";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { PositionsTable } from "@/components/positions/PositionsTable";
import { MainChart } from "@/components/charts/MainChart";
import { PortfolioHeatmap } from "@/components/charts/PortfolioHeatmap";
import { ChatPanel } from "@/components/chat/ChatPanel";

// D-08 three-column shell: a full-width header band pinned at the top, a
// left rail (watchlist above the trade bar), a center/main column holding
// the positions table, and a right rail holding the AI chat panel. The
// chat panel owns its own width (Plan 03-04) — full-size expanded, a
// narrow collapsed rail — so it renders here as a bare flex child with no
// wrapper div, unlike the left rail which has only one width. Plan
// 02-01's single AAPL tracer readout was replaced by the full
// WatchlistPanel (Plan 02-02); the header's own portfolio-total readout is
// now Header.tsx's live-recomputed total value (Plan 02-03, D-05).
export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-terminal-bg text-terminal-text">
      <Header />

      <div className="flex flex-1 gap-6 p-6">
        <div className="flex w-80 flex-shrink-0 flex-col gap-4">
          <WatchlistPanel />
          <TradeBar />
        </div>

        {/* The centre column is a stack of independently-bordered panels: main chart, a side-by-side panel row (heatmap), positions table. */}
        <main className="flex min-w-0 flex-1 flex-col gap-4">
          <MainChart />
          <div className="flex gap-4">
            <div className="flex-1"><PortfolioHeatmap /></div>
          </div>
          <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
            <PositionsTable />
          </section>
        </main>

        <ChatPanel />
      </div>
    </div>
  );
}
