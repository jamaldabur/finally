# Phase 4: Portfolio Visualization - Research

**Researched:** 2026-09-21
**Domain:** React/Recharts charting (sparklines, line charts, treemap) over an existing SSE-driven price store and a pre-existing portfolio-history REST endpoint
**Confidence:** HIGH

## Summary

This phase is almost entirely frontend work. The backend surface it needs —
`GET /api/portfolio/history` returning `{ snapshots: [{total_value, recorded_at}] }` —
**already exists and is unmodified since Phase 1** [VERIFIED: backend/app/routes/portfolio.py:102-111]
(quoted in full below). No backend changes are required for this phase; `compute_portfolio_view()`
(`backend/app/portfolio/service.py:48-124`) already returns `market_value` on every `PositionView`,
which is what the treemap sizes tiles by.

All visual/interaction decisions (charting library = Recharts 3.x, color formulas, layout,
copy, state-management approach) are locked in `04-UI-SPEC.md` and are not re-litigated here.
This research fills the implementation gaps the UI-SPEC deliberately left to research/planning:
exact Recharts APIs for `Treemap`'s custom `content` renderer and for a minimal axis-less
`LineChart`, where to place the new client-side price-history buffer relative to the existing
`priceStore.tsx`, known `ResponsiveContainer`/SVG performance caveats at this app's update
cadence, and the closest existing store/hook precedent (`portfolioStore.tsx`) for the new
`fetchPortfolioHistory()` polling hook this phase needs.

**Primary recommendation:** Install `recharts@^3.10.1` (verified current, React 19-compatible,
clean legitimacy audit). Build one shared `ChartShell`-style pattern reused across the sparkline,
main chart, and P&L chart to avoid tooltip/axis/gridline duplication across three `LineChart`
usages. Accumulate the price-history buffer as new state living beside (not necessarily inside)
`priceStore.tsx`'s existing `PriceStoreProvider`, keyed by "real change" semantics identical to
`PriceCell`'s flash trigger — never `previous_price`. Add `fetchPortfolioHistory()` to `lib/api.ts`
following `fetchPortfolio()`'s exact pattern, and a new polling hook modeled directly on
`portfolioStore.tsx`'s mount-effect + `setInterval` structure (30s interval per the UI-SPEC's
assumption, not 5s).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Price-history buffer accumulation (sparkline + main chart data source) | Browser / Client | — | Ephemeral, in-memory, rebuilds every page load per UI-SPEC's Assumption — no backend storage exists or is needed for this per-session buffer |
| Sparkline rendering (UI-02) | Browser / Client | — | Pure presentational SVG render of client-accumulated data; no new network call |
| Main chart rendering + ticker selection (UI-03) | Browser / Client | — | Selection state is synchronous client state (UI-SPEC: "no fetch of its own"); chart reads the same client buffer as the sparkline |
| Portfolio heatmap sizing/coloring (UI-04) | Browser / Client | API / Backend | Client renders the `Treemap`; the weight (`market_value`) and pct_change values it sizes/colors by are computed server-side in `compute_portfolio_view()`, already served via `GET /api/portfolio` |
| P&L history chart (UI-05) | Browser / Client | API / Backend | Client renders the `LineChart`; the underlying time series is server-persisted (`portfolio_snapshots` table) and served via the pre-existing `GET /api/portfolio/history` |
| Portfolio-history polling/fetch | Browser / Client | API / Backend | New `fetchPortfolioHistory()` + polling hook is a thin client wrapper around an already-implemented backend endpoint — no new backend route |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| recharts | 3.10.1 (verified current on npm, published 2026-07-25) [VERIFIED: npm registry, cross-checked against `peerDependencies.react: '^16.8.0 \|\| ^17.0.0 \|\| ^18.0.0 \|\| ^19.0.0'`] | `LineChart`/`Line` for sparkline, main chart, P&L chart; `Treemap` for the heatmap | Already locked in `04-UI-SPEC.md` — one dependency covers all four chart-shaped surfaces this phase needs, is React 19-idiomatic (declarative JSX), and is one of the two libraries root `PLAN.md` §10 explicitly sanctions |

No other new runtime dependency is needed. `ResponsiveContainer`, `LineChart`, `Line`, `XAxis`,
`YAxis`, `Tooltip`, `Treemap` are all exported from the single `recharts` package — no separate
`@recharts/*` scoped sub-packages are required for this project's usage.

### Supporting
None — this phase introduces no new supporting/helper library. Existing `lib/format.ts`
(`formatCurrency`, `formatSignedCurrency`, `formatPercent`) [VERIFIED: frontend/lib/format.ts:9-21]
already covers every numeric formatting need for chart tooltips/end-labels; no new formatting
helper is required beyond a small timestamp formatter for chart tooltips (trivial, no library
needed — `Intl.DateTimeFormat` or a one-line `Date` format, executor's call).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts | Lightweight Charts (TradingView) | Already rejected in `04-UI-SPEC.md` — no treemap primitive, would require a second library for UI-04 alone |
| Recharts `Treemap` custom `content` | A hand-rolled CSS-grid/flexbox treemap | Reinvents a non-trivial squarified-treemap layout algorithm; see Don't Hand-Roll below |

**Installation:**
```bash
npm install recharts
```

**Version verification:** `npm view recharts version` → `3.10.1`, published 2026-07-25.
`npm view recharts peerDependencies` confirms `react: '^16.8.0 || ^17.0.0 || ^18.0.0 || ^19.0.0'`,
satisfying this project's `react@19.3.0` / `react-dom@19.3.0` [VERIFIED: frontend/package.json:13-15].
`npm view recharts scripts.postinstall` returned nothing (no postinstall script).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| recharts | npm | actively maintained (latest 3.10.1 published 2026-07-25) | 42,992,376/week | github.com/recharts/recharts | OK | Approved |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

`recharts` was named by `04-UI-SPEC.md` (an upstream design-contract artifact, not this
research session's own web search), so its provenance there is `[CITED: 04-UI-SPEC.md]`. This
research session independently re-verified it against the npm registry and confirmed the
verdict via the package-legitimacy gate — `[VERIFIED: npm registry]` for existence/version/
downloads/postinstall-absence, and `[VERIFIED: npm registry]` for the peer-dependency range.

## Architecture Patterns

### System Architecture Diagram

```
SSE stream (/api/stream/prices, existing)
        │
        ▼
priceStore.tsx (PriceStoreProvider, existing)
   ├─ prices: Map<ticker, PriceTick>        (existing)
   ├─ firstPrices: Map<ticker, number>       (existing — trend reference)
   └─ NEW: priceHistory: Map<ticker, {timestamp, price}[]>   ◄── this phase's new state
        │  (appended only on "real change", capped at 500 points/ticker)
        │
        ├──────────────► Sparkline (per WatchlistRow, reads priceHistory[ticker])
        │
        └──────────────► MainChart (reads priceHistory[selectedTicker])
                                 ▲
                                 │ selectedTicker: string | null
                                 │ (lifted state or small ChartSelectionProvider)
                          WatchlistRow onClick (existing row, new handler)

GET /api/portfolio (existing, polled every 5s by portfolioStore.tsx)
        │
        ▼
usePortfolio() ──────────────────► PortfolioHeatmap (Treemap, sizes by market_value,
                                     colors by pct_change per UI-SPEC diverging formula)

GET /api/portfolio/history (existing route, NEW client consumer)
        │
        ▼
NEW fetchPortfolioHistory() (lib/api.ts) ──► NEW polling hook (30s interval,
                                               modeled on portfolioStore.tsx)
        │
        ▼
   PnlHistoryChart (LineChart, colored by first-vs-latest snapshot trend)
```

### Recommended Project Structure
```
frontend/
├── components/
│   ├── charts/                       # NEW — shared chart-surface components
│   │   ├── Sparkline.tsx             # inline ~20px LineChart, no axes/tooltip
│   │   ├── MainChart.tsx             # larger LineChart, crosshair+tooltip, end-label
│   │   ├── PortfolioHeatmap.tsx      # Recharts Treemap + custom content renderer
│   │   ├── PnlHistoryChart.tsx       # LineChart over portfolio_snapshots
│   │   └── chartTheme.ts             # shared constants: stroke widths, colors from
│   │                                  # --color-gain/--color-loss/--color-terminal-border,
│   │                                  # tooltip wrapper styling — single source so the
│   │                                  # three LineChart surfaces don't hand-roll their
│   │                                  # own style objects independently
│   └── watchlist/
│       └── WatchlistRow.tsx          # MODIFIED — embeds <Sparkline>, gains onClick
├── lib/
│   ├── priceStore.tsx                # MODIFIED (or a new sibling context) — adds
│   │                                  # priceHistory buffer + accumulation logic
│   ├── portfolioHistoryStore.tsx     # NEW — 30s-polling store for GET /api/portfolio/history,
│   │                                  # modeled directly on portfolioStore.tsx
│   ├── chartSelection.tsx            # NEW (or state lifted into page.tsx) — selectedTicker
│   └── api.ts                        # MODIFIED — add fetchPortfolioHistory()
└── app/
    └── page.tsx                      # MODIFIED — center column restructured per UI-SPEC
                                        # Layout & Interaction Contract
```

### Pattern 1: Shared chart-surface component, not three independent LineCharts

**What:** Sparkline, MainChart, and PnlHistoryChart all wrap Recharts `LineChart`/`Line` but
differ in size, axes, and tooltip presence. Factor the parts that are genuinely identical
(stroke width, round linecap, end-dot with surface-color ring, gain/loss color selection per
the UI-SPEC's single trend rule) into shared constants/helpers in `chartTheme.ts` rather than
duplicating inline style objects three times. Do **not** try to force all three into one
generic `<TimeSeriesChart variant="sparkline|main|pnl">` component — the UI-SPEC's mark spec
differs meaningfully per surface (sparkline has zero axes/tooltip/end-label; main and P&L both
have crosshair+tooltip+end-label) enough that three small, purpose-built components reading
shared constants is clearer than one component branching on a variant prop.

**When to use:** Any time two chart surfaces share a mark spec but differ in chrome (axes,
tooltip, size) — share the *styling constants*, not the *component tree*.

### Pattern 2: Recharts `Treemap` custom `content` renderer

**What:** `Treemap`'s `content` prop accepts a React element/function that receives `x`, `y`,
`width`, `height`, `index`, `name`, `value`, `root` (and `depth` for nested treemaps — not
needed here since positions are a flat, single-level dataset). The renderer draws its own
`<rect>` (or Recharts' `<Rectangle>` helper) at the given coordinates/size and any `<text>`
labels, giving full control over per-tile fill color (the diverging formula) and conditional
label rendering (drop pct_change first, then the ticker symbol, per the UI-SPEC's overflow
resolution) [CITED: recharts.github.io/en-US/examples/CustomContentTreemap/]. HTML elements
(`<div>`) are invalid inside the Treemap's SVG tree and will trigger React DOM warnings — all
tile content must be SVG elements (`<rect>`/`<Rectangle>`, `<text>`, `<g>`)
[CITED: recharts.github.io/en-US/examples/CustomContentTreemap/, WebSearch summary of same page].

**When to use:** UI-04's `PortfolioHeatmap` — this is the only way to apply the ±10%-capped
diverging fill formula per tile; Recharts' default `Treemap` fill only supports a flat/scalar
color, not a per-datum computed fill.

**Example (adapted pattern, not verbatim from any single source — Recharts' official custom-content
example plus this project's own diverging-color formula from `04-UI-SPEC.md`):**
```tsx
// Source pattern: recharts.github.io/en-US/examples/CustomContentTreemap/
// Colors/formula: 04-UI-SPEC.md "Heatmap diverging fill — exact formula"
import { Treemap, ResponsiveContainer } from "recharts";

type TreemapDatum = {
  ticker: string;
  market_value: number; // sizes the tile — Treemap's dataKey
  pct_change: number;   // drives fill via the diverging formula
};

function HeatmapTile(props: {
  x: number; y: number; width: number; height: number;
  ticker: string; pct_change: number;
}) {
  const { x, y, width, height, ticker, pct_change } = props;
  const fill = divergingFill(pct_change); // implements the UI-SPEC formula
  const textColor = tileTextColor(pct_change);
  const canShowTicker = width > 40 && height > 20; // overflow rule: drop label first
  return (
    <g>
      <rect
        x={x} y={y} width={width} height={height}
        fill={fill}
        stroke="var(--color-terminal-panel)" // 2px surface-color tile gap
        strokeWidth={2}
      />
      {canShowTicker && (
        <text x={x + 8} y={y + 16} fill={textColor} fontSize={10} fontWeight={600}>
          {ticker}
        </text>
      )}
    </g>
  );
}

<ResponsiveContainer width="100%" height={240}>
  <Treemap
    data={positions.map((p) => ({ ticker: p.ticker, market_value: p.market_value, pct_change: p.pct_change }))}
    dataKey="market_value"
    content={<HeatmapTile ticker="" pct_change={0} x={0} y={0} width={0} height={0} />}
  />
</ResponsiveContainer>
```
Recharts injects the real `x`/`y`/`width`/`height`/`payload` at render time regardless of the
placeholder props passed to the element — this is the documented pattern for a JSX-element
(not function) `content` prop.

### Pattern 3: Minimal axis-less `LineChart` for the sparkline

**What:** Set `hide` on both `XAxis` and `YAxis` (or omit them from the tree entirely — for a
truly chromeless sparkline, omitting the axis components is simpler than rendering-then-hiding
them) and omit `<Tooltip>`/`<Legend>` altogether, per the UI-SPEC's explicit dismissal of a
sparkline tooltip. Constrain the container to the row's `h-5` (20px) height via
`ResponsiveContainer`.

**Example:**
```tsx
// Source pattern: WebSearch summary of Recharts LineChart hide-axis usage
// (recharts.github.io/en-US/api/CartesianAxis "hide" prop)
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
`isAnimationActive={false}` is a deliberate addition beyond what the UI-SPEC specifies — see
Common Pitfalls below for why animation should be disabled on all three high-frequency chart
surfaces, not just the sparkline.

### Anti-Patterns to Avoid
- **Re-fetching or re-deriving portfolio P&L client-side:** `compute_portfolio_view()` is the
  sole authority for `market_value`/`unrealized_pnl`/`pct_change` (root D-04, already enforced
  in `portfolioStore.tsx`'s doc comment) — the heatmap must read these fields as-is, never
  recompute them from raw prices client-side.
- **A second SSE-tick accumulation loop:** Both `Sparkline` and `MainChart` must read the *same*
  `priceHistory` buffer (UI-SPEC's explicit DRY requirement) — do not give `MainChart` its own
  `useEffect` subscribing to `usePriceStore().prices` and building a parallel array.
- **Animating on every tick:** see Pitfall 1 below.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Treemap squarified-layout algorithm (rectangle sizing/positioning by weight) | A custom recursive rectangle-packing function | Recharts' `Treemap` component (layout only; supply a custom `content` renderer for fill/labels) | Squarified treemap layout is a non-trivial algorithm (Bruls/Huizing/van Wijk) with edge cases at very small/very large weight ratios; Recharts already implements and tests it — only the per-tile *paint* needs to be custom, not the *layout* |
| SVG line-chart rendering, crosshair hit-testing, tooltip positioning | Hand-rolled `<svg>` + `d3-scale`/`d3-shape` for the sparkline/main/P&L charts | Recharts `LineChart`/`Tooltip` | Already the UI-SPEC's locked decision; re-litigating would fork the four-surface single-dependency plan the UI-SPEC deliberately chose |
| Diverging-color interpolation (`mix(a, b, t)`) | A hand-rolled RGB lerp with off-by-one/clamping bugs | A tiny, tested lerp helper (a few lines is fine — this is *not* a "don't hand-roll, use a library" case, just a "write it once in `chartTheme.ts`, test it, don't inline it three times" case) | The UI-SPEC's formula is simple enough that no library is warranted, but duplicating the inline math per-tile risks divergent implementations between the tile fill and the legend gradient strip |

**Key insight:** The one genuinely complex algorithm this phase touches (treemap layout) is
fully delegated to Recharts. Everything else this phase needs (a lerp function, a trend
comparison, a capped-array push) is simple enough that a library would be over-engineering —
the risk here is process duplication (writing the same 5-line trend rule three times), not
algorithmic complexity, and the fix is a shared module, not a new dependency.

## Common Pitfalls

### Pitfall 1: `ResponsiveContainer` / SVG re-render cost at ~2 ticks/second
**What goes wrong:** Every SSE tick (root PLAN.md §6: ~500ms cadence) that changes a watched
ticker's price triggers a `priceStore` state update; if `Sparkline`/`MainChart` re-render their
full Recharts tree (including animation) on every such update across up to 10 watchlist rows,
the cumulative SVG diffing/animation cost can visibly degrade frame rate, since Recharts'
default `Line` renders with `isAnimationActive: true` and animates from empty on each data change.
**Why it happens:** Recharts is a general-purpose charting library; it does not assume
sub-second-cadence live-updating data by default, and community reports (GitHub issues, blog
posts) confirm performance degrades once dozens–hundreds of DOM/SVG nodes update on every
render cycle [CITED: WebSearch summary of recharts/recharts GitHub issues #172/#2831/#3658
and community guidance, general/non-project-specific — LOW-MEDIUM confidence, no single
authoritative source measured this project's exact cadence].
**How to avoid:** Set `isAnimationActive={false}` on every `<Line>` across all three
high-frequency surfaces (sparkline, main chart, P&L chart is lower-frequency at 30s but keep it
consistent). This is a one-line prop change with no visual-contract conflict — the UI-SPEC's
mark spec describes the *static* rendered appearance (stroke, dot, ring), not an animation
requirement. Additionally, cap `priceHistory` at 500 points (already the UI-SPEC's own
Assumption) so array length, not just update frequency, stays bounded.
**Warning signs:** Visible jank/flicker on the watchlist panel once several tickers are ticking
simultaneously; browser DevTools Performance tab showing long SVG-layout frames correlated with
SSE message arrival.

### Pitfall 2: `ResponsiveContainer` collapsing to zero height
**What goes wrong:** `ResponsiveContainer` measures its *parent* element's size; if the parent
has no explicit height (e.g., relies on content to determine height, or a flex child without
`flex-basis`/explicit height), the chart silently renders at 0×0 and appears blank
[CITED: WebSearch summary of recharts/recharts GitHub issues #135/#2831, official/semi-official
project issue reports — MEDIUM confidence, a well-documented, frequently-reported issue].
**Why it happens:** `ResponsiveContainer` uses a `ResizeObserver`/percentage-based sizing
strategy that requires a definite ancestor size to resolve against.
**How to avoid:** The UI-SPEC already specifies explicit fixed heights for every chart panel
(`h-72` main chart, `h-60` heatmap/P&L panels, `h-5` sparkline row) — as long as the executor
gives `ResponsiveContainer`'s *direct DOM parent* one of these explicit heights (not just the
outer panel `<section>`), this pitfall is avoided. Verify in the browser after first
implementing each chart, not just by reading the JSX.
**Warning signs:** A chart panel renders its heading/empty-state text correctly but the chart
area is visually blank with no console error.

### Pitfall 3: Chart container height excluding axis-label band (dataviz skill anti-pattern)
**What goes wrong:** A fixed-height chart container (e.g. `h-72`) sized only for the plot area,
not the axis tick-label band beneath it, causes the x-axis labels to be clipped or force a tiny
internal scrollbar.
**Why it happens:** `ResponsiveContainer height={N}` sizes the *whole* `LineChart` including its
axes — if the container's CSS height was chosen by eyeballing just the plot, the axis band has
nowhere to render.
**How to avoid:** Budget the axis-tick-label height (roughly 20-24px for a single row of Label-role
12px text) inside the panel's declared `h-72`/`h-60`, not as extra space on top of it. This is a
layout-arithmetic note for whoever implements `MainChart`/`PnlHistoryChart`, not a contradiction
of the UI-SPEC's height values.

### Pitfall 4: Refetch flash on the 30s portfolio-history poll and 5s portfolio poll
**What goes wrong:** If the new `portfolioHistoryStore` (or the heatmap reading `usePortfolio()`)
resets to a loading/null state on every periodic refetch, the P&L chart and heatmap will flash
their loading copy every 30s/5s even though they already have data to show.
**Why it happens:** A naive polling hook sets `loading = true` at the start of every fetch, not
just the first one.
**How to avoid:** Follow `portfolioStore.tsx`'s existing precedent exactly — `loading` starts
`true`, is set `false` once in the `finally` block, and is **never reset to `true`** by the
periodic-refresh effect (only the initial mount-effect touches it)
[VERIFIED: frontend/lib/portfolioStore.tsx:40-98, quoted: `const [loading, setLoading] = useState(true);` ... periodic effect calls only `void refresh()` inside `setInterval`, and `refresh()`'s own `finally` sets `setLoading(false)` unconditionally but `loading` is never set back to `true` after the first successful load]. The new `portfolioHistoryStore` must copy this pattern, not re-derive it.
**Warning signs:** The P&L chart or heatmap visibly blanks/reflows every 30s/5s in normal use.

## Code Examples

### `fetchPortfolioHistory()` — new `lib/api.ts` function, following the exact existing pattern
```typescript
// Source: existing pattern verified in frontend/lib/api.ts:19-25 (fetchPortfolio)
export async function fetchPortfolioHistory(): Promise<PortfolioHistoryResponse> {
  const res = await fetch(`${BASE}/api/portfolio/history`);
  if (!res.ok) {
    throw new Error(`GET /api/portfolio/history failed: ${res.status}`);
  }
  return res.json();
}
```
The response type must be added to `frontend/lib/types.ts`, mirroring the backend's
`PortfolioHistoryResponse`/`SnapshotResponse` Pydantic models verbatim
[VERIFIED: backend/app/routes/portfolio.py:69-76, quoted below]:
```python
class SnapshotResponse(BaseModel):
    total_value: float
    recorded_at: str

class PortfolioHistoryResponse(BaseModel):
    snapshots: list[SnapshotResponse]
```
No `PortfolioHistoryResponse`/`SnapshotResponse` TypeScript type currently exists in
`frontend/lib/types.ts` [VERIFIED: frontend/lib/types.ts, full file read — types present are
`PositionView`, `PortfolioResponse`, `TradeRequest`, `TradeResponse`, `WatchlistEntry`,
`PriceTick`, `PricesEvent`, `ActionOutcome`, `TradeAction`, `WatchlistAction`, `ChatMessage`,
`ChatResponse`, `ChatRequest` — no portfolio-history type among them] — this phase must add it.

### Price-history buffer accumulation — "real change" append rule
```typescript
// Pattern to follow: the same "real change" semantics PriceCell already uses
// for its flash trigger (frontend/components/ui/PriceCell.tsx:35, quoted:
// "if (lastPrice.current !== null && price !== lastPrice.current)"),
// NOT previous_price (see PriceCell.tsx's own comment on why previous_price
// is not a valid trigger — PriceCache.update() holds it steady on unchanged
// heartbeats).
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
This slots into the same `es.addEventListener("prices", ...)` handler `priceStore.tsx` already
has [VERIFIED: frontend/lib/priceStore.tsx:73-93, quoted: `es.addEventListener("prices", (event: MessageEvent<string>) => { const payload = JSON.parse(event.data) as PricesEvent; setPrices((prev) => { ... }); setFirstPrices((prev) => { ... }); ... });`] — alongside the existing `setPrices`/`setFirstPrices` calls, not a second `EventSource` subscription (D-05's single-shared-connection rule).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Recharts 2.x class-component-heavy API | Recharts 3.x (this project installs 3.10.1) | Recharts 3.0 (2025) | 3.x's peer range explicitly includes React 19; some 2.x-era blog posts/StackOverflow answers reference APIs (e.g. certain `Treemap` prop shapes) that may differ slightly — prefer the official `recharts.github.io` examples (already version-pinned to the docs site's current release) over older blog content when in doubt |

**Deprecated/outdated:** None specific to this phase's usage surface identified.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `isAnimationActive={false}` should be applied to all three high-frequency `<Line>` surfaces to avoid re-render cost at SSE cadence | Common Pitfalls, Pitfall 1 | If wrong (Recharts' animation cost turns out negligible at this project's scale — ≤10 tickers, ~2 ticks/sec), the only cost of following this assumption anyway is losing a cosmetic fade-in transition on data updates, which the UI-SPEC never required in the first place — low risk either way |
| A2 | A tile's canShowTicker threshold of `width > 40 && height > 20` (illustrative in the code example) approximates the UI-SPEC's overflow rule ("pct_change label drops first; if the ticker symbol still doesn't fit, no inline text") | Architecture Patterns, Pattern 2 | The exact pixel thresholds are unverified against real rendered text metrics — the executor should measure actual `10px/600` glyph width rather than trust these illustrative numbers verbatim |
| A3 | Placing new chart components under a new `components/charts/` directory (rather than e.g. `components/portfolio/`) is a reasonable convention extension | Architecture Patterns, Recommended Project Structure | Purely organizational; if wrong, a trivial rename with no functional impact |

## Open Questions

1. **Should `priceHistory` live inside `PriceStoreProvider` itself, or a new sibling
   `PriceHistoryProvider` inside the same provider tree?**
   - What we know: The UI-SPEC explicitly defers this to the executor ("extends `priceStore.tsx`
     or a new sibling context... executor's call"), with the only hard constraint being that it
     stays inside the `PriceStoreProvider` tree so it sees every tick.
   - What's unclear: Whether adding a third piece of state (`prices`, `firstPrices`,
     `priceHistory`) to the existing context risks over-broad re-renders for consumers that only
     need one of the three maps.
   - Recommendation: Given this app's scale (≤10 tickers, single page), the re-render cost
     difference between one enriched context and two nested contexts is negligible — extending
     `priceStore.tsx` directly (Option A in the UI-SPEC's own phrasing) is simpler and keeps all
     SSE-tick-derived state in one file. The planner should pick one explicitly rather than leave
     it for the executor to decide ad hoc, so all three chart components agree on the import path.

2. **Exact axis-tick-label height budget for `MainChart`/`PnlHistoryChart`.**
   - What we know: The UI-SPEC assigns `h-72` (288px) and `h-60` (240px) container heights, and
     specifies Label-role (12px) axis tick text.
   - What's unclear: No prior chart panel exists in this codebase to measure real axis-band
     height against — this is a genuinely new UI surface for the project.
   - Recommendation: Implement first, verify visually per Pitfall 3 above; not a blocker to
     planning, just a verification step to include in the phase's task list.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | Frontend build/dev | ✓ | v22.13.0 | — |
| npm | Package install (`npm install recharts`) | ✓ | 11.0.0 | — |
| recharts (to be installed) | UI-02..05 chart rendering | not yet installed, confirmed installable | 3.10.1 on registry | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — `recharts` is not yet in `package.json` but is
confirmed available and compatible; installing it is this phase's own first task, not a gap.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | **None configured in `frontend/`** — no `jest`, `vitest`, `@testing-library/react`, or similar appears in `frontend/package.json` devDependencies, and no `*.test.*`/`*.spec.*` files exist outside `node_modules` [VERIFIED: frontend/package.json:1-27 (full file read, only deps are `next`/`react`/`react-dom` and lint/typecheck/tailwind tooling), and a repo-wide glob for `frontend/**/*.test.*` and `frontend/**/*.spec.*` returned only `node_modules` matches] |
| Config file | none |
| Quick run command | `npm run lint && npm run typecheck` (both scripts exist: `eslint` and `tsc --noEmit`) [VERIFIED: frontend/package.json:9-10] |
| Full suite command | same as quick run — no component/unit test suite exists yet |
| Backend framework (unaffected by this phase) | pytest 8.0+, `backend/tests/` — this phase makes no backend changes, so no backend test obligation |

**This is consistent with existing project precedent, not a gap unique to this phase:** Phase 2
and Phase 3 (both frontend-heavy) also shipped with no frontend test files
[VERIFIED: repo-wide glob for `frontend/**/*.test.*` / `frontend/**/*.spec.*` returned zero
matches outside `node_modules`]. `TEST-04` ("Frontend unit tests cover price flash animation
triggering, watchlist CRUD, portfolio display calculations, and chat rendering/loading state")
is explicitly scoped to **Phase 6**, not this phase, per `REQUIREMENTS.md`'s traceability table
[VERIFIED: .planning/REQUIREMENTS.md:137-141, quoted: `| TEST-04 | Phase 6 | Pending |`].

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| UI-02 | Sparkline accumulates and renders progressively from SSE ticks | manual-only (no frontend test framework this phase — see above) | `npm run lint && npm run typecheck` (structural check only) | ❌ — no frontend test infra exists; deferred to Phase 6 (TEST-04) |
| UI-03 | Clicking a watchlist row renders that ticker's larger chart | manual-only | `npm run lint && npm run typecheck` | ❌ — same as above |
| UI-04 | Heatmap tiles sized by weight, colored/saturated by pct_change capped ±10% | manual-only | `npm run lint && npm run typecheck` | ❌ — same as above |
| UI-05 | P&L line chart renders `portfolio_snapshots` history | manual-only | `npm run lint && npm run typecheck` | ❌ — same as above |

**Justification for manual-only:** No frontend test framework exists in this project yet
(verified above), and introducing one (choosing/configuring Vitest or Jest + React Testing
Library, writing fixtures for `EventSource`/SSE mocking, etc.) is itself a substantial scope
addition beyond this phase's UI-02..05 success criteria. `TEST-04` already exists in the roadmap
as the dedicated phase for this work (Phase 6). Adding partial, ad-hoc test infra now would
duplicate/conflict with that phase's eventual, more complete setup. This phase's own
verification is `/gsd-verify-work` conversational UAT against the four success criteria in
`ROADMAP.md`, consistent with how Phase 2 and Phase 3 were verified.

### Sampling Rate
- **Per task commit:** `npm run lint && npm run typecheck` (existing scripts; catches type/lint
  regressions in every new chart component)
- **Per wave merge:** same, plus a manual dev-server visual check against the UI-SPEC's four
  success criteria
- **Phase gate:** `/gsd-verify-work` conversational UAT (no automated full suite exists to gate on)

### Wave 0 Gaps
- None requiring new test infrastructure setup this phase — deliberately deferred to Phase 6
  (TEST-04) per the justification above. If the planner disagrees with this deferral, it should
  be raised as an explicit phase-scope decision (introducing Vitest/RTL a phase and a half
  early), not silently added mid-plan.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | No | Project has no auth (single hardcoded `user_id="default"`, out of scope per `REQUIREMENTS.md` "Out of Scope") — unaffected by this phase |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | Same as above |
| V5 Input Validation | Marginal — no new user-text-entry surface | This phase adds a click handler (ticker selection) and reads server-controlled data (ticker symbols, prices, `pct_change`) into SVG `<text>` elements. React's JSX rendering (`{ticker}` inside `<text>`) auto-escapes text content — no `dangerouslySetInnerHTML` or raw DOM string insertion is introduced anywhere in the recommended patterns above. Ticker symbols are additionally constrained server-side to the simulator's fixed universe (root `PLAN.md` §6, already the basis of `04-UI-SPEC.md`'s "long-text" dismissal for heatmap tile labels) |
| V6 Cryptography | No | Not applicable — no new secrets/crypto surface |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| SVG `<text>`/tooltip content built from untrusted string concatenation (e.g. `innerHTML` with ticker/timestamp data) | Tampering / Information Disclosure (stored-XSS-adjacent, even though this app has no persistence of user-authored strings) | Render all chart text via React JSX (`{value}`) or Recharts' own prop-driven text rendering, never `dangerouslySetInnerHTML` or manual DOM string building for tooltip/label content — the dataviz skill's own "Labels are untrusted data — use `textContent`" rule applies even though, in this specific app, ticker/price data originates server-side from a closed, validated universe rather than genuine end-user input |
| None else identified specific to this phase's surface | — | This phase adds no new backend route, no new user-text input field, and no new external-data ingestion — its only new "input" is a `Treemap`/`LineChart` render of data the app already fetches and already trusts (root D-04's `compute_portfolio_view()` authority) |

## Sources

### Primary (HIGH confidence)
- `backend/app/routes/portfolio.py` (read in full this session) — confirms `GET /api/portfolio/history` already exists, exact response shape
- `backend/app/db/portfolio_snapshots.py`, `backend/app/portfolio/service.py` (read in full this session) — confirms `portfolio_snapshots` schema and `compute_portfolio_view()`'s `market_value`/`pct_change` fields
- `frontend/lib/priceStore.tsx`, `frontend/lib/portfolioStore.tsx`, `frontend/lib/api.ts`, `frontend/lib/types.ts`, `frontend/lib/format.ts`, `frontend/app/globals.css`, `frontend/components/ui/PriceCell.tsx`, `frontend/components/watchlist/WatchlistRow.tsx`, `frontend/components/watchlist/WatchlistPanel.tsx`, `frontend/components/positions/PositionsTable.tsx`, `frontend/app/page.tsx`, `frontend/package.json` (all read in full this session) — existing frontend conventions and exact current state
- npm registry (`npm view recharts version|peerDependencies|scripts.postinstall`) — package legitimacy and React 19 compatibility

### Secondary (MEDIUM confidence)
- recharts.github.io official examples/API docs (`CustomContentTreemap`, `Treemap` API, `CartesianAxis` `hide` prop) — fetched via WebSearch/WebFetch summary, official first-party documentation

### Tertiary (LOW confidence)
- GitHub issues (recharts/recharts #172, #2831, #3658, #135) and general blog/community
  commentary on `ResponsiveContainer` sizing and animation performance at high update
  frequency — real, but not authoritative benchmarks for this project's specific scale (≤10
  tickers, ~2 ticks/sec); treated as directional guidance (hence `isAnimationActive={false}`
  recommended as a low-cost precaution, not asserted as measured-necessary for this app)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - recharts version/compatibility directly verified against npm registry this session, not training-data recall
- Architecture: HIGH - all patterns grounded in either official Recharts docs or this project's own already-read source files
- Pitfalls: MEDIUM - the two `ResponsiveContainer` GitHub-issue-sourced pitfalls are real and well-documented community reports, but not independently reproduced against this specific app's data volumes this session

**Research date:** 2026-09-21
**Valid until:** 2026-10-21 (30 days — Recharts is a stable, slow-moving library at this project's usage depth; re-verify the npm version if planning is delayed significantly past this window)
