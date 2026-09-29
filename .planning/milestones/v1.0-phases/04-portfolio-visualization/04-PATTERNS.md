# Phase 4: Portfolio Visualization - Pattern Map

**Mapped:** 2026-09-21
**Files analyzed:** 10 (new/modified, per 04-UI-SPEC.md + 04-RESEARCH.md)
**Analogs found:** 10 / 10 (all role-match or exact within this frontend-only phase; no prior charting code exists, so chart-rendering internals fall back to RESEARCH.md's Recharts code examples, noted per-file below)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `frontend/lib/priceStore.tsx` (MODIFIED — add `priceHistory`) | store/provider | event-driven (SSE) | itself (`frontend/lib/priceStore.tsx`) | exact — extend existing file in place |
| `frontend/lib/portfolioHistoryStore.tsx` (NEW) | store/provider | request-response (polling) | `frontend/lib/portfolioStore.tsx` | exact |
| `frontend/lib/chartSelection.tsx` (NEW, or state lifted into `page.tsx`) | provider/hook | event-driven (client state) | `frontend/lib/priceStore.tsx` (simplest context shape) | role-match |
| `frontend/lib/api.ts` (MODIFIED — add `fetchPortfolioHistory()`) | service | request-response | itself, pattern = `fetchPortfolio()` (lines 19-25) | exact |
| `frontend/lib/types.ts` (MODIFIED — add `PortfolioHistoryResponse`/`SnapshotResponse`) | model/type | transform | itself, pattern = existing `PortfolioResponse` type block (lines 30-36) | exact |
| `frontend/components/charts/chartTheme.ts` (NEW) | utility/config | transform | `frontend/lib/format.ts` (shared formatting constants/helpers) | role-match |
| `frontend/components/charts/Sparkline.tsx` (NEW) | component | streaming (client buffer render) | `frontend/components/ui/PriceCell.tsx` (flash/real-change pattern) + Recharts example in 04-RESEARCH.md Pattern 3 | role-match (component); no prior chart in repo |
| `frontend/components/charts/MainChart.tsx` (NEW) | component | streaming | `frontend/components/ui/PriceCell.tsx` + `frontend/components/positions/PositionsTable.tsx` (loading/empty/error state shell) | role-match |
| `frontend/components/charts/PortfolioHeatmap.tsx` (NEW) | component | CRUD (renders `usePortfolio()` snapshot) | `frontend/components/positions/PositionsTable.tsx` | role-match |
| `frontend/components/charts/PnlHistoryChart.tsx` (NEW) | component | request-response (polling) | `frontend/components/positions/PositionsTable.tsx` (state shell) + `frontend/lib/portfolioStore.tsx` (polling store) | role-match |
| `frontend/components/watchlist/WatchlistRow.tsx` (MODIFIED — embed `Sparkline`, add `onClick`) | component | event-driven (SSE + click) | itself (`frontend/components/watchlist/WatchlistRow.tsx`) | exact — extend existing file in place |
| `frontend/app/page.tsx` (MODIFIED — center column restructure) | route/layout | request-response (composition only) | itself (`frontend/app/page.tsx`) | exact — extend existing file in place |

All analog paths above were confirmed to exist on disk via `Read` during this session (git-tracked source under `frontend/`, not a gitignored mirror).

## Pattern Assignments

### `frontend/lib/priceStore.tsx` (store, event-driven) — MODIFY in place

**Analog:** itself, current state (lines 1-130)

**Provider state shape to extend** (lines 46-59):
```typescript
type PriceStoreValue = {
  prices: Map<string, PriceTick>;
  firstPrices: Map<string, number>;
  status: ConnectionStatus;
};
// ADD: priceHistory: Map<string, { timestamp: string; price: number }[]>;
```

**Where to append the new accumulation logic** — inside the existing `es.addEventListener("prices", ...)` handler (lines 73-93), alongside the existing `setPrices`/`setFirstPrices` calls, per 04-RESEARCH.md's "real change" append rule (Code Examples section):
```typescript
setPriceHistory((prev) => {
  const next = new Map(prev);
  for (const tick of payload.ticks) {
    const series = next.get(tick.ticker) ?? [];
    const last = series[series.length - 1];
    if (last === undefined || last.price !== tick.price) {
      const appended = [...series, { timestamp: tick.timestamp, price: tick.price }];
      next.set(
        tick.ticker,
        appended.length > 500 ? appended.slice(appended.length - 500) : appended,
      );
    }
  }
  return next;
});
```
Do **not** open a second `EventSource` — this must slot into the single shared connection (module docblock, lines 3-28, states the D-05 single-connection rule explicitly).

**Export update:** add `priceHistory` to the `<PriceStoreContext.Provider value={{ ... }}>` object (line 117) and to `usePriceStore()`'s return type.

---

### `frontend/lib/portfolioHistoryStore.tsx` (NEW store, request-response/polling)

**Analog:** `frontend/lib/portfolioStore.tsx` (full file, lines 1-114)

**Imports pattern** (lines 12-22):
```typescript
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fetchPortfolio } from "./api"; // -> replace with fetchPortfolioHistory
import type { PortfolioResponse } from "./types"; // -> replace with PortfolioHistoryResponse
```

**Interval constant + provider value shape** (lines 24-34): copy verbatim, renaming `REFRESH_INTERVAL_MS` to 30000 (30s, per UI-SPEC's Assumption, NOT the 5s used by `portfolioStore`), and `portfolio` → `history`.

**Critical "never reset loading to true" pattern** (Pitfall 4 in 04-RESEARCH.md, verified at lines 40, 69-98): `loading` starts `true`, is set `false` once inside the mount effect's `finally` block (lines 69-87), and the periodic `setInterval` effect (lines 93-98) calls only `void refresh()` — it must NEVER call `setLoading(true)` again. Copy this exact two-effect split (mount-effect + separate interval-effect) rather than merging them.

**In-flight guard** (lines 42-61, the `isRefreshingRef` pattern): copy verbatim to prevent overlapping 30s-interval fetches.

---

### `frontend/lib/chartSelection.tsx` (NEW, optional — executor may instead lift state into `page.tsx`)

**Analog:** `frontend/lib/priceStore.tsx`'s minimal context shape (lines 52-53, 116-129) — simplest analog for a bare `createContext`/`useContext` pair with no async logic:
```typescript
const SomeContext = createContext<T | null>(null);
export function useSomeStore(): T {
  const ctx = useContext(SomeContext);
  if (!ctx) throw new Error("useX must be used within XProvider");
  return ctx;
}
```
State needed: `selectedTicker: string | null` + a setter, per UI-SPEC's Layout & Interaction Contract point 2 (`null` on first load, no default selection).

---

### `frontend/lib/api.ts` (MODIFY — add `fetchPortfolioHistory()`)

**Analog:** itself, `fetchPortfolio()` (lines 19-25):
```typescript
export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE}/api/portfolio`);
  if (!res.ok) {
    throw new Error(`GET /api/portfolio failed: ${res.status}`);
  }
  return res.json();
}
```
New function follows this exactly (04-RESEARCH.md Code Examples, verbatim):
```typescript
export async function fetchPortfolioHistory(): Promise<PortfolioHistoryResponse> {
  const res = await fetch(`${BASE}/api/portfolio/history`);
  if (!res.ok) {
    throw new Error(`GET /api/portfolio/history failed: ${res.status}`);
  }
  return res.json();
}
```
Add `PortfolioHistoryResponse` to the top-of-file import block (line 7-15 pattern) once defined in `types.ts`.

---

### `frontend/lib/types.ts` (MODIFY — add `PortfolioHistoryResponse`/`SnapshotResponse`)

**Analog:** itself, `PortfolioResponse` block (lines 30-36):
```typescript
export type PortfolioResponse = {
  cash_balance: number;
  positions: PositionView[];
  positions_value: number;
  total_value: number;
  total_unrealized_pnl: number;
};
```
New types mirror the backend Pydantic models verbatim (backend/app/routes/portfolio.py:69-76, per 04-RESEARCH.md):
```typescript
export type SnapshotResponse = {
  total_value: number;
  recorded_at: string;
};

export type PortfolioHistoryResponse = {
  snapshots: SnapshotResponse[];
};
```
Follow the file's module docblock convention (lines 1-18) — keep snake_case wire-format keys, add a one-line source citation comment pointing at `backend/app/routes/portfolio.py`.

---

### `frontend/components/charts/chartTheme.ts` (NEW utility/config)

**Analog:** `frontend/lib/format.ts` — shared, imported-everywhere helper/constants module (role precedent for "one small file of pure functions/constants, no component logic").

**Contents to centralize** (per 04-RESEARCH.md Pattern 1 and Don't Hand-Roll table):
- Gain/loss color constants reading CSS custom properties: `var(--color-gain)`, `var(--color-loss)`, `var(--color-terminal-border)`, `var(--color-terminal-panel)`.
- A single `mix(a, b, t)` lerp helper (write once, used by both `PortfolioHeatmap` tile fill and its legend gradient strip — 04-RESEARCH.md explicitly warns against duplicating this math in three places).
- The trend rule as a shared function: `trendDirection(first: number, latest: number): "up" | "down"` — reused by `Sparkline`, `MainChart`, `PnlHistoryChart` (single source of truth per UI-SPEC's "Trend/color rule").
- Shared stroke/dot constants: `strokeWidth: 2`, `dotRadius: 4`, `isAnimationActive: false` (Pitfall 1, 04-RESEARCH.md — apply to every `<Line>` across all three high-frequency surfaces).

---

### `frontend/components/charts/Sparkline.tsx` (NEW component, streaming)

**Analog (data-flow/state-read pattern):** `frontend/components/ui/PriceCell.tsx` (full file, lines 1-50) — specifically the "real change" comparison philosophy (lines 8-16, 32-43) that `priceStore.tsx`'s new `priceHistory` buffer already encodes upstream; `Sparkline` itself is a pure read of `priceHistory[ticker]`, no local flash-tracking `useRef` needed (that logic now lives in the store).

**Analog (Recharts JSX shape):** 04-RESEARCH.md Pattern 3 code example (verbatim, cited from Recharts docs):
```tsx
<ResponsiveContainer width="100%" height={20}>
  <LineChart data={history}>
    <Line
      type="linear"
      dataKey="price"
      stroke={trend === "up" ? "var(--color-gain)" : "var(--color-loss)"}
      strokeWidth={2}
      dot={false}
      isAnimationActive={false}
    />
  </LineChart>
</ResponsiveContainer>
```
No `<XAxis>`/`<YAxis>`/`<Tooltip>` — omit entirely (UI-SPEC: sparkline gets no tooltip, no axes). Reads `usePriceStore().priceHistory.get(ticker)` and `usePriceStore().firstPrices.get(ticker)` for the trend comparison via `chartTheme.ts`'s `trendDirection()`.

---

### `frontend/components/charts/MainChart.tsx` (NEW component, streaming)

**Analog (state-shell — loading/empty/error branches):** `frontend/components/positions/PositionsTable.tsx` (lines 17-41) — the `loading && !data` / `error && !data` / `data.length === 0` / populated four-branch conditional-render structure:
```tsx
{loading && !portfolio && ( <p className="text-sm text-terminal-text-muted">Loading…</p> )}
{!loading && error && !portfolio && ( <p className="text-sm text-red-400" role="alert">{error}</p> )}
{portfolio && portfolio.positions.length === 0 && ( <p className="text-sm text-terminal-text-muted">...</p> )}
{portfolio && portfolio.positions.length > 0 && ( /* populated content */ )}
```
`MainChart` adapts this to its own three states (no-selection empty / <2-points waiting / populated) per UI-SPEC's Copywriting Contract and UI Considerations table.

**Analog (chart internals):** larger version of the `Sparkline` Recharts shape above, adding `<XAxis>`/`<YAxis>` (Label role, `--color-terminal-text-muted`), `<Tooltip>` (crosshair, styled per UI-SPEC's hover/tooltip block), end-dot with ring (`r>=4`, `stroke="var(--color-terminal-panel)"`, `strokeWidth={2}`), and an end-label using `tabular-nums`/`--font-numeric` colored `--color-terminal-text` (never the line color, per UI-SPEC's mark spec).

Reads `usePriceStore().priceHistory.get(selectedTicker)` — same buffer as `Sparkline`, no second accumulation loop (04-RESEARCH.md Anti-Patterns).

---

### `frontend/components/charts/PortfolioHeatmap.tsx` (NEW component, CRUD-read)

**Analog (state shell + data source):** `frontend/components/positions/PositionsTable.tsx` (full file) — reads `usePortfolio()` (loading/error/empty/populated branches, lines 17-41), never recomputes `market_value`/`pct_change` client-side (matches `PositionsTable`'s own doc comment, lines 4-9, on `compute_portfolio_view()` being sole authority).

**Analog (Recharts Treemap custom content):** 04-RESEARCH.md Pattern 2 code example (verbatim, adapted from Recharts' official `CustomContentTreemap` example plus the UI-SPEC's diverging-fill formula):
```tsx
function HeatmapTile(props: { x: number; y: number; width: number; height: number; ticker: string; pct_change: number; }) {
  const { x, y, width, height, ticker, pct_change } = props;
  const fill = divergingFill(pct_change);       // chartTheme.ts mix() helper
  const textColor = tileTextColor(pct_change);
  const canShowTicker = width > 40 && height > 20; // A2 in RESEARCH.md: illustrative, measure real glyph width
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill}
            stroke="var(--color-terminal-panel)" strokeWidth={2} />
      {canShowTicker && (
        <text x={x + 8} y={y + 16} fill={textColor} fontSize={10} fontWeight={600}>{ticker}</text>
      )}
    </g>
  );
}
<ResponsiveContainer width="100%" height={240}>
  <Treemap data={positions.map((p) => ({ ticker: p.ticker, market_value: p.market_value, pct_change: p.pct_change }))}
           dataKey="market_value" content={<HeatmapTile ticker="" pct_change={0} x={0} y={0} width={0} height={0} />} />
</ResponsiveContainer>
```
All tile content must be SVG (`<rect>`/`<text>`/`<g>`), never `<div>` — HTML elements inside Recharts' `Treemap` SVG tree trigger DOM warnings.

---

### `frontend/components/charts/PnlHistoryChart.tsx` (NEW component, request-response/polling)

**Analog (state shell):** `frontend/components/positions/PositionsTable.tsx` (lines 17-41), adapted to `portfolioHistoryStore`'s `history`/`loading`/`error` (0-or-1-snapshot empty state per UI-SPEC Copywriting Contract).

**Analog (chart internals):** same `LineChart`/`Tooltip`/end-dot/end-label shape as `MainChart.tsx` (line chart, not sparkline — has axes+tooltip), reading `portfolioHistoryStore`'s `history.snapshots` (`total_value`, `recorded_at`), trend colored via `chartTheme.ts`'s `trendDirection()` applied to first-vs-latest snapshot (UI-SPEC: "identical rule" as tickers, applied to `portfolio_snapshots`).

---

### `frontend/components/watchlist/WatchlistRow.tsx` (MODIFY in place)

**Analog:** itself, current full file (lines 1-49)

**Current structure to extend** (lines 30-48):
```tsx
<div className="flex items-center justify-between border-b border-terminal-border py-1.5 text-sm last:border-b-0">
  <span className="font-medium text-terminal-text">{entry.ticker}</span>
  <div className="flex gap-4 tabular-nums">
    <PriceCell price={price} direction={direction} />
    <span className={...}>{changePct === null ? "—" : formatPercent(changePct)}</span>
  </div>
</div>
```
Add: (1) `<Sparkline ticker={entry.ticker} />` between the ticker `<span>` and the `PriceCell`/`change%` div, wrapped `flex-1 min-w-0 h-5`; (2) promote the outer `<div>` to a click target — add `onClick={() => setSelectedTicker(entry.ticker)}`, `cursor-pointer`, `role="button"`, and conditional classes `bg-terminal-border/50` (selected) / `hover:bg-terminal-border/20` (unselected hover), reading/writing the new `chartSelection` context. Import pattern stays identical to the existing `usePriceStore` import at line 12.

---

### `frontend/app/page.tsx` (MODIFY — center column restructure)

**Analog:** itself, current full file (lines 1-37)

**Current `<main>` block to replace** (lines 29-31):
```tsx
<main className="flex-1 rounded-lg border border-terminal-border bg-terminal-panel p-4">
  <PositionsTable />
</main>
```
Replace with an unstyled `flex-1 flex flex-col gap-4` container holding four sibling panels (per UI-SPEC Layout & Interaction Contract): `MainChart` panel (`h-72`, full width) → `flex gap-4` row of `PortfolioHeatmap` (`h-60`, left) + `PnlHistoryChart` (`h-60`, right) → `PositionsTable` now wrapped in its own `rounded-lg border border-terminal-border bg-terminal-panel p-4` panel shell (previously inherited this border from `<main>` directly — `PositionsTable.tsx` itself needs no change). Import pattern for new components follows the existing top-of-file import block (lines 3-7) exactly — one import per component, no barrel file.

Also wrap the whole tree in the new `PriceHistoryProvider`/`chartSelection` provider(s) if implemented as separate contexts rather than folded into `priceStore.tsx`/lifted state — follow the nesting precedent of however `PriceStoreProvider`/`PortfolioProvider` are currently composed (check `app/layout.tsx` for the existing provider-wrapping location, not `page.tsx` itself, since `page.tsx` has no visible provider wrapping in the excerpt above — likely `layout.tsx` wraps `PriceStoreProvider`/`PortfolioProvider`; add any new provider there for consistency).

---

## Shared Patterns

### Real-change comparison (never `previous_price`)
**Source:** `frontend/components/ui/PriceCell.tsx` lines 8-16, 32-43 (doc comment + `useRef`-based comparison)
**Apply to:** `priceStore.tsx`'s new `priceHistory` accumulation, `Sparkline`, `MainChart` — any surface deciding whether a "real" price change occurred must compare against the last *rendered/recorded* value, never the tick's own `previous_price` field (which the backend cache holds steady on unchanged heartbeats).

### Loading-state never resets on periodic refresh
**Source:** `frontend/lib/portfolioStore.tsx` lines 40-41, 69-98 (mount-effect sets `loading=false` once; separate interval-effect never touches `loading`)
**Apply to:** `portfolioHistoryStore.tsx` (new) — must copy this exact two-effect split, per 04-RESEARCH.md Pitfall 4, to avoid the P&L chart/heatmap flashing loading copy every 30s/5s.

### Four-branch panel state shell (loading / error / empty / populated)
**Source:** `frontend/components/positions/PositionsTable.tsx` lines 17-64
**Apply to:** `MainChart`, `PortfolioHeatmap`, `PnlHistoryChart` — same `text-sm text-terminal-text-muted` (loading/empty) and `text-sm text-red-400 role="alert"` (error) conventions, same conditional-render ordering (loading-without-data, error-without-data, empty, populated).

### Sole-authority data rule (D-04)
**Source:** `frontend/lib/portfolioStore.tsx` lines 4-9 doc comment; `frontend/components/positions/PositionsTable.tsx` lines 4-9 doc comment
**Apply to:** `PortfolioHeatmap` — must read `market_value`/`pct_change`/`unrealized_pnl` from `usePortfolio()` as-is, never recompute from raw ticks client-side.

### Single shared SSE connection (D-05)
**Source:** `frontend/lib/priceStore.tsx` lines 3-28 doc comment
**Apply to:** the new `priceHistory` buffer — must be appended inside the existing `es.addEventListener("prices", ...)` handler, never a second `EventSource`.

## No Analog Found

None — every file in scope has at least a role-match analog in the existing codebase (frontend has no prior chart component, so chart-internals code for `Sparkline`/`MainChart`/`PortfolioHeatmap`/`PnlHistoryChart` falls back to the Recharts examples already vetted and cited in `04-RESEARCH.md`, which the planner should treat as equally authoritative to an in-repo analog for this phase only).

## Metadata

**Analog search scope:** `frontend/lib/`, `frontend/components/watchlist/`, `frontend/components/positions/`, `frontend/components/ui/`, `frontend/app/`
**Files scanned:** `priceStore.tsx`, `portfolioStore.tsx`, `api.ts`, `types.ts`, `WatchlistRow.tsx`, `PositionsTable.tsx`, `PriceCell.tsx`, `page.tsx` (all read in full this session)
**Pattern extraction date:** 2026-09-21
