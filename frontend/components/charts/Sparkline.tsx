"use client";

/**
 * Chromeless per-row mini line chart. Reads the shared price-history buffer
 * from the price store; it opens no stream and makes no request of its own.
 *
 * Two behavioural rules this component depends on but does not implement,
 * both owned by `priceStore.tsx`: equal consecutive prices merge into one
 * recorded point (so a flat line means the price genuinely held), and points
 * are rendered in arrival order and never re-sorted.
 *
 * States (UI-SPEC UI Considerations): no points -> flat muted baseline (the
 * deliberate "filling in progressively" look, not a loading state); one point
 * -> the end marker alone at that price; two or more -> the line plus the
 * end marker. No axes, tooltip, legend or text: the adjacent PriceCell is the
 * row's numeric readout.
 *
 * This is the only one of the app's four charts that opts out of Recharts'
 * accessibility layer (`accessibilityLayer={false}` below). Recharts 3.x
 * defaults every cartesian chart's root <svg> to `tabindex="0"
 * role="application"`, and this chart alone is rendered as a DOM descendant
 * of an already-focusable control (`WatchlistRow`'s `role="button"`), so
 * leaving the default on gives each row two tab stops instead of one. The
 * consequence was specific: one Tab from a selected row landed back inside
 * that same row's own sparkline, and Enter/Space there re-selected the
 * ticker that was already selected — a silent no-op the user read as
 * keyboard activation simply not working. While that surface held focus the
 * browser also painted its default ring tightly around the 20px-tall chart,
 * which is what the user separately reported as the mini graph being
 * broken. Opting out removes the stray tab stop and its ring; the wrapper's
 * `role="img"` and interpolated `aria-label` below keep the sparkline
 * described for assistive technology either way.
 */

import { Line, LineChart, ResponsiveContainer } from "recharts";
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

export function Sparkline({ ticker }: { ticker: string }) {
  const { priceHistory, firstPrices } = usePriceStore();
  const series = priceHistory.get(ticker) ?? [];

  if (series.length === 0) {
    // Full row height so the row does not reflow when the first point lands.
    return (
      <div className="flex h-full w-full items-center" aria-hidden="true">
        <div
          className="w-full"
          style={{ height: 1, backgroundColor: CHART_NEUTRAL }}
        />
      </div>
    );
  }

  const latest = series[series.length - 1].price;
  const direction = trendDirection(firstPrices.get(ticker), latest);
  const stroke = trendStroke(direction);
  const lastIndex = series.length - 1;

  return (
    <div
      className="h-full w-full"
      role="img"
      aria-label={`${ticker} trending ${direction}`}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={series}
          margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          // The end dot sits on the data extreme; let it overflow the 20px band
          // instead of being clipped by the SVG viewport.
          style={{ overflow: "visible" }}
          // See the module docblock: this chart is a descendant of the
          // already-focusable WatchlistRow, so it must not compete for the
          // next Tab stop.
          accessibilityLayer={false}
        >
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
                <circle
                  key={`dot-${index}`}
                  cx={cx}
                  cy={cy}
                  r={CHART_DOT_RADIUS}
                  fill={stroke}
                  stroke={CHART_SURFACE}
                  strokeWidth={CHART_RING_WIDTH}
                />
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
