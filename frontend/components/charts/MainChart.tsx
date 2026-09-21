"use client";

/**
 * Larger detailed line chart for the selected watchlist ticker. Reads the same
 * shared price-history buffer the sparklines read; it opens no stream and makes
 * no request (selection is synchronous client state, so there is nothing to
 * load and nothing that can fail).
 */

import { Line, LineChart, ResponsiveContainer } from "recharts";
import { useChartSelection } from "@/lib/chartSelection";
import { usePriceStore } from "@/lib/priceStore";
import {
  CHART_ANIMATION_ACTIVE,
  CHART_STROKE_WIDTH,
  trendDirection,
  trendStroke,
} from "./chartTheme";

export function MainChart() {
  const { selectedTicker } = useChartSelection();
  const { priceHistory, firstPrices } = usePriceStore();
  const series = selectedTicker ? (priceHistory.get(selectedTicker) ?? []) : [];

  return (
    <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <h2 className="text-sm font-medium text-terminal-text-muted">
        {selectedTicker ?? "Chart"}
      </h2>
      {selectedTicker === null || series.length < 2 ? (
        <p className="mt-3 text-sm text-terminal-text-muted">
          {selectedTicker === null
            ? "Select a ticker from the watchlist to view its chart."
            : "Waiting for price data…"}
        </p>
      ) : (
        <div className="mt-3 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series}>
              <Line
                type="linear"
                dataKey="price"
                dot={false}
                stroke={trendStroke(
                  trendDirection(
                    firstPrices.get(selectedTicker),
                    series[series.length - 1].price,
                  ),
                )}
                strokeWidth={CHART_STROKE_WIDTH}
                isAnimationActive={CHART_ANIMATION_ACTIVE}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
