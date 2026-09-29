"use client";

/**
 * Larger detailed line chart for the selected watchlist ticker. Reads the same
 * shared price-history buffer the sparklines read; it opens no stream and makes
 * no request (selection is synchronous client state, so there is nothing to
 * load and nothing that can fail).
 *
 * This chart deliberately keeps Recharts' default keyboard-widget surface
 * (unlike Sparkline.tsx, which opts out — see that file's docblock). As a
 * standalone panel rather than a descendant of another control, its tab stop
 * steals nothing from anything else, and the arrow-key tooltip navigation
 * Recharts wires up here is the only keyboard route to this panel's plotted
 * values. Its focus ring is supplied by the single global
 * `.recharts-surface:focus-visible` rule in `app/globals.css`, not by any
 * per-component styling — so the correct implementation of "keeps the
 * default" is to pass nothing accessibility-related to the chart below.
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
import { useChartSelection } from "@/lib/chartSelection";
import { usePriceStore } from "@/lib/priceStore";
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
  second: "2-digit",
});

function formatTime(timestamp: string): string {
  const d = new Date(timestamp);
  return Number.isNaN(d.getTime()) ? "" : timeFormat.format(d);
}

export function MainChart() {
  const { selectedTicker } = useChartSelection();
  const { priceHistory, firstPrices } = usePriceStore();
  const series = selectedTicker ? (priceHistory.get(selectedTicker) ?? []) : [];

  const latest = series.length > 0 ? series[series.length - 1].price : undefined;
  const stroke = trendStroke(
    trendDirection(
      selectedTicker ? firstPrices.get(selectedTicker) : undefined,
      latest,
    ),
  );
  const lastIndex = series.length - 1;

  return (
    <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <h2 className="text-sm font-medium text-terminal-text-muted">
        {selectedTicker ?? "Chart"}
      </h2>
      {selectedTicker === null ? (
        <div className="mt-3">
          <p className="text-base font-semibold text-terminal-text">
            No ticker selected
          </p>
          <p className="mt-1 text-sm text-terminal-text-muted">
            Select a ticker from the watchlist to view its chart.
          </p>
        </div>
      ) : series.length < 2 ? (
        <p className="mt-3 text-sm text-terminal-text-muted">
          Waiting for price data…
        </p>
      ) : (
        <div className="mt-3 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 24, right: 16, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTime}
                tick={TICK_STYLE}
                axisLine={AXIS_LINE}
                tickLine={AXIS_LINE}
                minTickGap={48}
              />
              <YAxis
                domain={["auto", "auto"]}
                tickFormatter={(v: number) => formatCurrency(v)}
                tick={TICK_STYLE}
                className="tabular-nums"
                axisLine={AXIS_LINE}
                tickLine={AXIS_LINE}
                width={64}
              />
              <Tooltip
                cursor={{ stroke: CHART_NEUTRAL, strokeWidth: 1 }}
                content={({ active, payload }) => {
                  if (!active || !payload || payload.length === 0) return null;
                  const point = payload[0].payload as {
                    timestamp: string;
                    price: number;
                  };
                  return (
                    <div className="rounded border border-terminal-border bg-terminal-panel px-2 py-1 text-xs text-terminal-text">
                      <div className="text-terminal-text-muted">
                        {formatTime(point.timestamp)}
                      </div>
                      <div className="tabular-nums">
                        {formatCurrency(point.price)}
                      </div>
                    </div>
                  );
                }}
              />
              <Line
                type="linear"
                dataKey="price"
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
                        {formatCurrency(series[lastIndex].price)}
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
      )}
    </section>
  );
}
