"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useMarketData } from "@/lib/marketData";
import { formatCurrency } from "@/lib/format";

export default function MainChart({ ticker }: { ticker: string | null }) {
  const { history, prices } = useMarketData();

  if (!ticker) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        Select a ticker from the watchlist to see its chart
      </div>
    );
  }

  const points = (history[ticker] ?? []).map((p) => ({
    time: new Date(p.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    price: p.price,
  }));
  const current = prices[ticker];

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-baseline justify-between px-4 pt-3.5 pb-2">
        <h2 className="text-sm font-semibold text-foreground">{ticker}</h2>
        {current && (
          <span className="font-tabular text-lg font-semibold text-accent-blue">{formatCurrency(current.price)}</span>
        )}
      </div>
      <div className="flex-1 min-h-0 px-2 pb-3">
        {points.length < 2 ? (
          <div className="flex items-center justify-center h-full text-muted text-sm">
            Waiting for price data…
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
              <Line type="monotone" dataKey="price" stroke="var(--accent-blue)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
