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

// Hex twins of the CSS-variable constants above (--color-terminal-border,
// --color-gain, --color-loss, --color-terminal-bg, --color-terminal-text).
// Both forms exist because a fill computed by interpolation cannot be a
// `var(...)` reference: mixing needs real channel values. Keep in sync with
// globals.css.
export const HEX_NEUTRAL = "#30363d";
export const HEX_GAIN = "#4ade80";
export const HEX_LOSS = "#f87171";
export const HEX_INK_DARK = "#0d1117";
export const HEX_INK_LIGHT = "#e6edf3";

// Heatmap colour saturates at +/- this many percent (root PLAN.md section 10).
export const HEATMAP_CAP_PCT = 10;

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Linear interpolation between two `#rrggbb` colours; `t` clamped to [0, 1]. */
export function mixColor(a: string, b: string, t: number): string {
  const k = Number.isFinite(t) ? Math.min(Math.max(t, 0), 1) : 0;
  const ca = hexToRgb(a);
  const cb = hexToRgb(b);
  const out = ca.map((c, i) => Math.round(c + (cb[i] - c) * k));
  return `#${out.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

export function heatmapIntensity(pctChange: number): number {
  if (!Number.isFinite(pctChange)) return 0;
  return Math.min(Math.abs(pctChange), HEATMAP_CAP_PCT) / HEATMAP_CAP_PCT;
}

export function divergingFill(pctChange: number): string {
  return mixColor(
    HEX_NEUTRAL,
    pctChange >= 0 ? HEX_GAIN : HEX_LOSS,
    heatmapIntensity(pctChange),
  );
}

/** Dark ink on vivid fills (intensity >= 0.5), light ink on pale ones. */
export function tileTextColor(pctChange: number): string {
  return heatmapIntensity(pctChange) >= 0.5 ? HEX_INK_DARK : HEX_INK_LIGHT;
}
