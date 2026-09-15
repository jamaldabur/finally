"use client";

import { ResponsiveContainer, Treemap } from "recharts";
import type { Position } from "@/lib/types";
import { formatPercent } from "@/lib/format";

const PNL_CAP = 10; // % magnitude at which color intensity saturates
const NEUTRAL = { r: 35, g: 42, b: 53 }; // matches --border
const UP = { r: 63, g: 185, b: 80 };
const DOWN = { r: 229, g: 83, b: 75 };

function mix(a: typeof NEUTRAL, b: typeof NEUTRAL, t: number): string {
  const r = Math.round(a.r + (b.r - a.r) * t);
  const g = Math.round(a.g + (b.g - a.g) * t);
  const bl = Math.round(a.b + (b.b - a.b) * t);
  return `rgb(${r}, ${g}, ${bl})`;
}

export function pnlColor(pnlPercent: number): string {
  const intensity = Math.min(Math.abs(pnlPercent) / PNL_CAP, 1);
  return mix(NEUTRAL, pnlPercent >= 0 ? UP : DOWN, intensity);
}

interface HeatmapNode {
  name: string;
  size: number;
  pnlPercent: number;
  [key: string]: string | number;
}

function CellContent(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  pnlPercent?: number;
  depth?: number;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name, pnlPercent = 0, depth } = props;
  // Treemap always wraps the real leaf cells (depth 1) in a synthetic whole-area
  // root node (depth 0) and renders `content` for it too — same coordinates as
  // whichever leaf happens to size-match it, producing overlapping ghost text.
  if (depth === 0) return null;
  if (width < 2 || height < 2) return null;
  return (
    <g>
      <rect
        x={x + 2}
        y={y + 2}
        width={Math.max(width - 4, 0)}
        height={Math.max(height - 4, 0)}
        rx={8}
        fill={pnlColor(pnlPercent)}
      />
      {width > 50 && height > 30 && (
        <text
          x={x + width / 2}
          y={y + height / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={13}
          fontFamily="var(--font-mono)"
          stroke="rgba(0,0,0,0.45)"
          strokeWidth={3}
          paintOrder="stroke"
        >
          <tspan x={x + width / 2} dy="-0.4em" fontWeight={600}>
            {name}
          </tspan>
          <tspan x={x + width / 2} dy="1.2em">
            {formatPercent(pnlPercent)}
          </tspan>
        </text>
      )}
    </g>
  );
}

export default function PortfolioHeatmap({ positions }: { positions: Position[] }) {
  const totalValue = positions.reduce((sum, p) => sum + p.quantity * p.current_price, 0);

  if (positions.length === 0 || totalValue <= 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm text-center px-6">
        No open positions yet — buy something to see it here.
      </div>
    );
  }

  const data: HeatmapNode[] = positions.map((p) => ({
    name: p.ticker,
    size: Math.max(p.quantity * p.current_price, 0.01),
    pnlPercent: p.unrealized_pnl_pct * 100,
  }));

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-sm font-semibold text-foreground px-4 pt-3.5 pb-2">Positions heatmap</h2>
      <div className="flex-1 min-h-0 px-3 pb-3">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={data}
            dataKey="size"
            aspectRatio={4 / 3}
            stroke="var(--surface)"
            isAnimationActive={false}
            // Data-update transitions are a separate flag from the initial-mount one
            // above, defaulting to a 1.5s cross-fade; disabled to avoid mid-transition
            // flicker each time positions/prices refresh.
            isUpdateAnimationActive={false}
            content={<CellContent />}
          />
        </ResponsiveContainer>
      </div>
    </div>
  );
}
