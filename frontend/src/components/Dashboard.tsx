"use client";

import { useCallback, useEffect, useState } from "react";
import { MarketDataProvider, useMarketData } from "@/lib/marketData";
import { getPortfolio, getPortfolioHistory, getWatchlist } from "@/lib/api";
import type { Portfolio, PortfolioSnapshot } from "@/lib/types";
import Header from "./Header";
import WatchlistPanel from "./WatchlistPanel";
import MainChart from "./MainChart";
import PortfolioHeatmap from "./PortfolioHeatmap";
import PnLChart from "./PnLChart";
import PositionsTable from "./PositionsTable";
import TradeBar from "./TradeBar";
import ChatPanel from "./ChatPanel";

const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];
const PORTFOLIO_POLL_MS = 3000;
const HISTORY_POLL_MS = 10000;

function DashboardInner() {
  const { status } = useMarketData();
  // Seeded with the default watchlist (PLAN.md §7) so tickers render immediately;
  // replaced once GET /api/watchlist resolves.
  const [tickers, setTickers] = useState<string[]>(DEFAULT_TICKERS);
  const [selected, setSelected] = useState<string | null>(null);
  const effectiveSelected = selected ?? tickers[0] ?? null;
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);

  const refreshPortfolio = useCallback(() => {
    getPortfolio()
      .then(setPortfolio)
      .catch(() => {
        // /api/portfolio may not be deployed yet; keep last known state.
      });
  }, []);

  const refreshHistory = useCallback(() => {
    getPortfolioHistory()
      .then(setSnapshots)
      .catch(() => {
        // /api/portfolio/history may not be deployed yet.
      });
  }, []);

  useEffect(() => {
    getWatchlist()
      .then((entries) => {
        if (entries.length) setTickers(entries.map((e) => e.ticker));
      })
      .catch(() => {
        // /api/watchlist may not be deployed yet; keep the default seed list.
      });
  }, []);

  useEffect(() => {
    refreshPortfolio();
    refreshHistory();
    const portfolioTimer = setInterval(refreshPortfolio, PORTFOLIO_POLL_MS);
    const historyTimer = setInterval(refreshHistory, HISTORY_POLL_MS);
    return () => {
      clearInterval(portfolioTimer);
      clearInterval(historyTimer);
    };
  }, [refreshPortfolio, refreshHistory]);

  const handleTraded = useCallback(() => {
    refreshPortfolio();
    refreshHistory();
  }, [refreshPortfolio, refreshHistory]);

  return (
    <div className="workspace-shell">
      <Header
        totalValue={portfolio?.total_value ?? null}
        cashBalance={portfolio?.cash_balance ?? null}
        status={status}
      />
      {/* Desktop (≥1024px): a fixed one-screen workspace, no page scroll — every
          panel that can overflow (watchlist, chat, positions) scrolls internally
          instead. Below that: a normal stacked column that scrolls with the page,
          since a rigid one-screen layout would be illegibly cramped that narrow. */}
      <div className="workspace-body">
        <div className="workspace-watchlist panel">
          <WatchlistPanel
            tickers={tickers}
            selected={effectiveSelected}
            onSelect={setSelected}
            onWatchlistChanged={setTickers}
          />
        </div>

        <div className="workspace-chart panel">
          <MainChart ticker={effectiveSelected} />
        </div>

        <div className="workspace-pnl panel">
          <PnLChart snapshots={snapshots} />
        </div>

        <div className="workspace-heatmap panel">
          <PortfolioHeatmap positions={portfolio?.positions ?? []} />
        </div>

        <div className="workspace-tradepos panel flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x divide-border min-w-0">
          <div className="lg:w-[360px] lg:shrink-0">
            <TradeBar defaultTicker={effectiveSelected} onTraded={handleTraded} />
          </div>
          <div className="flex-1 min-h-0 min-w-0">
            <PositionsTable positions={portfolio?.positions ?? []} />
          </div>
        </div>

        <div className="workspace-chat panel">
          <ChatPanel onActionExecuted={handleTraded} />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <MarketDataProvider>
      <DashboardInner />
    </MarketDataProvider>
  );
}
