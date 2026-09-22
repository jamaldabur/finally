"use client";

/**
 * Portfolio treemap: one tile per position, sized by the server's
 * `market_value`, filled by the server's `pct_change` through the shared
 * diverging formula. Reads the shared portfolio store and issues no request;
 * the backend is the sole authority for every figure (D-04).
 */

import { ResponsiveContainer, Tooltip, Treemap } from "recharts";
import { formatPercent } from "@/lib/format";
import { usePortfolio } from "@/lib/portfolioStore";
import {
  CHART_ANIMATION_ACTIVE,
  HEATMAP_CAP_PCT,
  HEX_GAIN,
  HEX_LOSS,
  HEX_NEUTRAL,
  divergingFill,
  mixColor,
  tileTextColor,
} from "./chartTheme";

// Per-glyph advance estimates, measured live in this app at fontSize 10 /
// fontWeight 600 with this app's own font stack (getComputedTextLength() on
// real tile text, see .planning/debug/heatmap-tile-pct-label-missing.md T5).
// An uppercase ticker glyph advances 6.0-7.0px; a digit, sign or percent
// sign advances 5.1-5.7px. Each constant is pinned to the TOP of its
// measured range rather than the middle: an estimate that under-reports
// would let a label overflow its tile, and the UI-SPEC is explicit that
// text is never clipped, so erring high costs at most an occasional early
// drop while erring low produces the one outcome the spec forbids.
const TICKER_GLYPH_ADVANCE = 7;
const PCT_GLYPH_ADVANCE = 6;
const TICKER_MIN_HEIGHT = 26;
const PCT_MIN_HEIGHT = 42;
const TILE_INSET = 8;

/**
 * Whether `label` fits inside a tile of the given `width`, at the supplied
 * per-glyph advance. The drawn text starts one TILE_INSET in from the left;
 * doubling the inset here reserves the same margin on the right, which is
 * what keeps a label from running up against the tile's own 2px separator
 * stroke rather than actually reaching the tile's far edge.
 */
function labelFits(label: string, width: number, glyphAdvance: number): boolean {
  return width - 2 * TILE_INSET >= label.length * glyphAdvance;
}

const LEGEND_STEPS = 15;
// Left to right: full loss -> neutral -> full gain.
const LEGEND_COLORS = Array.from({ length: LEGEND_STEPS }, (_, i) => {
  const v = (i / (LEGEND_STEPS - 1)) * 2 - 1;
  return mixColor(HEX_NEUTRAL, v >= 0 ? HEX_GAIN : HEX_LOSS, Math.abs(v));
});

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
  const pctLabel = formatPercent(pct_change);
  const showTicker =
    labelFits(ticker, width, TICKER_GLYPH_ADVANCE) && height >= TICKER_MIN_HEIGHT;
  const showPct =
    labelFits(pctLabel, width, PCT_GLYPH_ADVANCE) && height >= PCT_MIN_HEIGHT;
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
      {showTicker && (
        <text
          x={x + TILE_INSET}
          y={y + TILE_INSET + 10}
          fontSize={10}
          fontWeight={600}
          fill={tileTextColor(pct_change)}
        >
          {ticker}
        </text>
      )}
      {showPct && (
        <text
          x={x + TILE_INSET}
          y={y + TILE_INSET + 24}
          fontSize={10}
          fontWeight={600}
          fill={tileTextColor(pct_change)}
        >
          {pctLabel}
        </text>
      )}
    </g>
  );
}

function Legend() {
  return (
    <div
      className="flex flex-col items-end gap-0.5"
      role="img"
      aria-label={`Colour scale: loss at -${HEATMAP_CAP_PCT}%, neutral at 0%, gain at +${HEATMAP_CAP_PCT}%`}
    >
      <div className="flex h-2 w-[120px] overflow-hidden rounded-sm" aria-hidden>
        {LEGEND_COLORS.map((c, i) => (
          <div key={i} className="flex-1" style={{ backgroundColor: c }} />
        ))}
      </div>
      <div
        className="flex w-[120px] justify-between text-xs text-terminal-text-muted"
        aria-hidden
      >
        <span>−10%</span>
        <span>0%</span>
        <span>+10%</span>
      </div>
    </div>
  );
}

export function PortfolioHeatmap() {
  const { portfolio, loading, error } = usePortfolio();
  const positions = portfolio?.positions ?? [];
  const data = positions.map((p) => ({
    ticker: p.ticker,
    market_value: p.market_value,
    pct_change: p.pct_change,
  }));
  // Share-of-total presentation of server-computed market values; not a new
  // financial figure.
  const total = data.reduce((sum, d) => sum + d.market_value, 0);

  // Branch order matters: the store lowers `loading` once and never raises it
  // again, so a refetch cannot send this panel back to loading copy. A
  // "partially populated position" is deliberately not a branch: the backend
  // always returns complete position rows.
  return (
    <section className="flex h-60 flex-col rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <div className="mb-2 flex items-start justify-between">
        <h2 className="text-sm font-medium text-terminal-text-muted">
          Portfolio Heatmap
        </h2>
        <Legend />
      </div>

      {loading && !portfolio && (
        <p className="text-sm text-terminal-text-muted">Loading portfolio&hellip;</p>
      )}

      {!loading && error && !portfolio && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      {portfolio && data.length === 0 && (
        <p className="text-sm text-terminal-text-muted">
          No positions to visualize — place a trade to see them here.
        </p>
      )}

      {data.length > 0 && (
        <div className="min-h-0 flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="market_value"
              isAnimationActive={CHART_ANIMATION_ACTIVE}
              content={<Tile />}
            >
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload || payload.length === 0) return null;
                  const d = payload[0].payload as {
                    ticker?: string;
                    market_value?: number;
                    pct_change?: number;
                  };
                  if (d.ticker === undefined || d.market_value === undefined) {
                    return null;
                  }
                  const weight = total > 0 ? (d.market_value / total) * 100 : 0;
                  return (
                    <div className="rounded border border-terminal-border bg-terminal-panel px-2 py-1 text-xs text-terminal-text">
                      <div className="font-semibold">{d.ticker}</div>
                      <div className="tabular-nums">
                        Weight {weight.toFixed(1)}%
                      </div>
                      <div className="tabular-nums">
                        Change {formatPercent(d.pct_change ?? 0)}
                      </div>
                    </div>
                  );
                }}
              />
            </Treemap>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
