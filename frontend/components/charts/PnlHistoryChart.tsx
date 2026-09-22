"use client";

/**
 * Portfolio Value line chart over recorded `portfolio_snapshots`.
 *
 * Contract facts this component depends on and does not own: the series it
 * receives is a bounded window of the most recent snapshots rather than the
 * whole recorded history — portfolioHistoryStore.tsx owns that bound
 * (HISTORY_POINT_LIMIT) and this component trusts it rather than trimming
 * again. The backend returns that window ascending by recorded time, and the
 * series is drawn exactly as recorded: it plots the points it was given and
 * nothing between them — no smoothing, no resampling, no gap-filling —
 * because every point on this line is a claim about what the portfolio was
 * actually worth at a recorded moment.
 *
 * The x position comes from a numeric projection of each row's own
 * `recorded_at` (`recorded_at_ms`, see below), so elapsed time between
 * points is drawn to scale and a gap in the record reads as a gap, rather
 * than every point being spaced evenly by index regardless of how much time
 * actually passed.
 *
 * This panel deliberately keeps Recharts' focusable chart surface, per the
 * decision recorded in Plan 04-05 (standalone chart panels keep the
 * keyboard tooltip navigation Recharts wires up by default), with its focus
 * ring supplied by the single global `.recharts-surface:focus-visible` rule
 * in `app/globals.css` — not by any prop on this component.
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

  // One-to-one projection of each row's own recorded_at into a numeric time
  // value used only for placement on the X axis — not a second source of
  // truth, and not a new data point: no row is added, removed or reordered.
  // No guard around a non-parseable timestamp: the backend's snapshot writer
  // is the only producer of these strings and it emits ISO-8601, so a value
  // that fails to parse means a corrupted row, and a chart that visibly
  // fails on one is a better outcome than one that quietly omits a recorded
  // portfolio value.
  const chartData = snapshots.map((s) => ({
    ...s,
    recorded_at_ms: Date.parse(s.recorded_at),
  }));

  function formatAxisTime(ms: number): string {
    return Number.isFinite(ms) ? timeFormat.format(new Date(ms)) : "";
  }

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
            data={chartData}
            margin={{ top: 20, right: 16, bottom: 0, left: 0 }}
          >
            <XAxis
              dataKey="recorded_at_ms"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={formatAxisTime}
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
