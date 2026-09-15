"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PortfolioSnapshot } from "@/lib/types";
import { formatCurrency } from "@/lib/format";

export default function PnLChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const points = snapshots.map((s) => ({
    time: new Date(s.recorded_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    value: s.total_value,
  }));

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-sm font-semibold text-foreground px-4 pt-3.5 pb-2">Portfolio value</h2>
      <div className="flex-1 min-h-0 px-2 pb-3">
        {points.length < 2 ? (
          <div className="flex items-center justify-center h-full text-muted text-sm">
            Not enough history yet — check back in a bit.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" stroke="var(--muted)" tick={{ fontSize: 11 }} minTickGap={40} />
              <YAxis
                domain={["auto", "auto"]}
                stroke="var(--muted)"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => formatCurrency(v)}
                width={80}
              />
              <Tooltip
                contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 10 }}
                formatter={(value) => formatCurrency(Number(value))}
              />
              <Line type="monotone" dataKey="value" stroke="var(--accent-yellow)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
