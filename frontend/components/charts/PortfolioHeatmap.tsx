"use client";

/**
 * Portfolio treemap: one tile per position, sized by the server's
 * `market_value`, filled by the server's `pct_change` through the shared
 * diverging formula. Reads the shared portfolio store and issues no request;
 * the backend is the sole authority for every figure (D-04).
 */

import { ResponsiveContainer, Treemap } from "recharts";
import { usePortfolio } from "@/lib/portfolioStore";
import { CHART_ANIMATION_ACTIVE, divergingFill, tileTextColor } from "./chartTheme";

type TileProps = {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  ticker?: string;
  pct_change?: number;
};

function Tile({ x = 0, y = 0, width = 0, height = 0, ticker, pct_change }: TileProps) {
  if (ticker === undefined || pct_change === undefined) return <g />;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={divergingFill(pct_change)}
        stroke="var(--color-terminal-panel)"
        strokeWidth={2}
      />
      {width > 40 && height > 20 && (
        <text
          x={x + 8}
          y={y + 8 + 10}
          fontSize={10}
          fontWeight={600}
          fill={tileTextColor(pct_change)}
        >
          {ticker}
        </text>
      )}
    </g>
  );
}

export function PortfolioHeatmap() {
  const { portfolio } = usePortfolio();
  const data = (portfolio?.positions ?? []).map((p) => ({
    ticker: p.ticker,
    market_value: p.market_value,
    pct_change: p.pct_change,
  }));

  return (
    <section className="flex h-60 flex-col rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <h2 className="mb-2 text-sm font-medium text-terminal-text-muted">
        Portfolio Heatmap
      </h2>
      {data.length > 0 && (
        <div className="min-h-0 flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="market_value"
              isAnimationActive={CHART_ANIMATION_ACTIVE}
              content={<Tile />}
            />
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
