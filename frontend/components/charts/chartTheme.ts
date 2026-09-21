/**
 * Shared chart constants and the single trend rule reused by every chart
 * surface in Phase 4 (sparkline, main chart, heatmap, P&L chart). Keeping one
 * trend rule and one set of mark constants here means four charts can never
 * disagree on what "up" looks like or how thick a line is (04-RESEARCH.md
 * Pattern 1). Pure constants and helpers — no React, no component logic.
 */

export const CHART_GAIN = "var(--color-gain)";
export const CHART_LOSS = "var(--color-loss)";
export const CHART_NEUTRAL = "var(--color-terminal-border)";
export const CHART_SURFACE = "var(--color-terminal-panel)";

export const CHART_STROKE_WIDTH = 2;
export const CHART_DOT_RADIUS = 4;
export const CHART_RING_WIDTH = 2;

// Prices tick roughly twice a second across ten rows; re-animating each
// series from empty on every data change is cost with no visual contract
// behind it (04-RESEARCH.md Pitfall 1).
export const CHART_ANIMATION_ACTIVE = false;

export type TrendDirection = "up" | "down";

/**
 * The UI-SPEC Trend/colour rule: "up" only when both values are known and the
 * latest is at or above the first observed price since page load.
 */
export function trendDirection(
  first: number | undefined,
  latest: number | undefined,
): TrendDirection {
  return first !== undefined && latest !== undefined && latest >= first
    ? "up"
    : "down";
}

export function trendStroke(direction: TrendDirection): string {
  return direction === "up" ? CHART_GAIN : CHART_LOSS;
}
