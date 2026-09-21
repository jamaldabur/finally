"use client";

/**
 * Portfolio Value line chart over recorded snapshots.
 */

import { Line, LineChart, ResponsiveContainer } from "recharts";
import { usePortfolioHistory } from "@/lib/portfolioHistoryStore";
import {
  CHART_ANIMATION_ACTIVE,
  CHART_STROKE_WIDTH,
  trendDirection,
  trendStroke,
} from "./chartTheme";

export function PnlHistoryChart() {
  const { history } = usePortfolioHistory();
  const snapshots = history?.snapshots ?? [];
  const stroke = trendStroke(
    trendDirection(
      snapshots[0]?.total_value,
      snapshots[snapshots.length - 1]?.total_value,
    ),
  );

  return (
    <section className="flex h-60 flex-col rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <h2 className="text-sm font-medium text-terminal-text-muted">
        Portfolio Value
      </h2>
      <div className="min-h-0 flex-1">
        {snapshots.length >= 2 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={snapshots}>
              <Line
                type="linear"
                dataKey="total_value"
                stroke={stroke}
                strokeWidth={CHART_STROKE_WIDTH}
                dot={false}
                isAnimationActive={CHART_ANIMATION_ACTIVE}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : null}
      </div>
    </section>
  );
}
