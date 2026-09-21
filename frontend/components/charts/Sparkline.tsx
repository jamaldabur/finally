"use client";

/**
 * Chromeless per-row mini line chart. Reads the shared price-history buffer
 * from the price store; it opens no stream and makes no request of its own.
 */

import { Line, LineChart, ResponsiveContainer } from "recharts";
import { usePriceStore } from "@/lib/priceStore";
import {
  CHART_ANIMATION_ACTIVE,
  CHART_STROKE_WIDTH,
  trendDirection,
  trendStroke,
} from "./chartTheme";

export function Sparkline({ ticker }: { ticker: string }) {
  const { priceHistory, firstPrices } = usePriceStore();
  const series = priceHistory.get(ticker) ?? [];

  if (series.length === 0) {
    return <div className="h-full w-full" />;
  }

  const latest = series[series.length - 1].price;
  const stroke = trendStroke(trendDirection(firstPrices.get(ticker), latest));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={series}
        margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
      >
        <Line
          type="linear"
          dataKey="price"
          stroke={stroke}
          strokeWidth={CHART_STROKE_WIDTH}
          dot={false}
          isAnimationActive={CHART_ANIMATION_ACTIVE}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
