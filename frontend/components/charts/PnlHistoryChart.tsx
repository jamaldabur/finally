"use client";

/**
 * Portfolio Value line chart over recorded `portfolio_snapshots`.
 *
 * Contract facts this component depends on and does not own: the backend
 * returns snapshots ascending by recorded time, and the series is drawn
 * exactly as recorded. It plots the points it was given and nothing between
 * them — no smoothing, no resampling, no gap-filling — because every point on
 * this line is a claim about what the portfolio was actually worth at a
 * recorded moment.
 */

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/format";
import { usePortfolioHistory } from "@/lib/portfolioHistoryStore";
import {
  CHART_ANIMATION_ACTIVE,
  CHART_DOT_RADIUS,
  CHART_NEUTRAL,
  CHART_RING_WIDTH,
  CHART_STROKE_WIDTH,
  CHART_SURFACE,
  trendDirection,
  trendStroke,
} from "./chartTheme";

const TICK_STYLE = { fontSize: 12, fill: "var(--color-terminal-text-muted)" };
const AXIS_LINE = { stroke: CHART_NEUTRAL, strokeWidth: 1 };
const timeFormat = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

function formatTime(timestamp: string): string {
  const d = new Date(timestamp);
  return Number.isNaN(d.getTime()) ? "" : timeFormat.format(d);
}

export function PnlHistoryChart() {
  const { history, loading, error } = usePortfolioHistory();
  const snapshots = history?.snapshots ?? [];
  const lastIndex = snapshots.length - 1;
  const stroke = trendStroke(
    trendDirection(
      snapshots[0]?.total_value,
      snapshots[lastIndex]?.total_value,
    ),
  );

  // Branches key on having no data, not on the loading flag alone, so a
  // periodic refresh can never return the panel to its loading copy.
  let body;
  if (history === null && loading) {
    body = (
      <p className="mt-3 text-sm text-terminal-text-muted">
        Loading portfolio history…
      </p>
    );
  } else if (history === null && error) {
    body = (
      <p role="alert" className="mt-3 text-sm text-red-400">
        {error}
      </p>
    );
  } else if (snapshots.length < 2) {
    // Zero and one snapshot share this copy: a line needs two points, and a
    // lone dot in an empty panel would read as a rendering bug.
    body = (
      <p className="mt-3 text-sm text-terminal-text-muted">
        Not enough history yet — check back after your first trade or ~30
        seconds of activity.
      </p>
    );
  } else {
    body = (
      <div className="mt-3 min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={snapshots}
            margin={{ top: 20, right: 16, bottom: 0, left: 0 }}
          >
            <XAxis
              dataKey="recorded_at"
              tickFormatter={formatTime}
              tick={TICK_STYLE}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              minTickGap={56}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => formatCurrency(v)}
              tick={TICK_STYLE}
              className="tabular-nums"
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              width={72}
            />
            <Tooltip
              cursor={{ stroke: CHART_NEUTRAL, strokeWidth: 1 }}
              content={({ active, payload }) => {
                if (!active || !payload || payload.length === 0) return null;
                const point = payload[0].payload as {
                  recorded_at: string;
                  total_value: number;
                };
                return (
                  <div className="rounded border border-terminal-border bg-terminal-panel px-2 py-1 text-xs text-terminal-text">
                    <div className="text-terminal-text-muted">
                      {formatTime(point.recorded_at)}
                    </div>
                    <div className="tabular-nums">
                      {formatCurrency(point.total_value)}
                    </div>
                  </div>
                );
              }}
            />
            <Line
              type="linear"
              dataKey="total_value"
              stroke={stroke}
              strokeWidth={CHART_STROKE_WIDTH}
              dot={(props: { cx?: number; cy?: number; index?: number }) => {
                const { cx, cy, index } = props;
                if (index !== lastIndex || cx === undefined || cy === undefined) {
                  return <g key={`dot-${index}`} />;
                }
                return (
                  <g key={`dot-${index}`}>
                    <circle
                      cx={cx}
                      cy={cy}
                      r={CHART_DOT_RADIUS}
                      fill={stroke}
                      stroke={CHART_SURFACE}
                      strokeWidth={CHART_RING_WIDTH}
                    />
                    <text
                      x={cx}
                      y={cy - 12}
                      textAnchor="end"
                      fontSize={12}
                      className="tabular-nums"
                      fill="var(--color-terminal-text)"
                    >
                      {formatCurrency(snapshots[lastIndex].total_value)}
                    </text>
                  </g>
                );
              }}
              activeDot={false}
              isAnimationActive={CHART_ANIMATION_ACTIVE}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <section className="flex h-60 flex-col rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <h2 className="text-sm font-medium text-terminal-text-muted">
        Portfolio Value
      </h2>
      {body}
    </section>
  );
}
