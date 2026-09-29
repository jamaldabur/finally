# Phase 04 — UI Review

**Audited:** 2026-09-22  
**Baseline:** UI-SPEC.md (Design Contract)  
**Screenshots:** Captured (desktop 1440×900, mobile 375×812)  
**Methodology:** 6-pillar adversarial audit against design contract — assume deviations until proven otherwise

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All copy matches UI-SPEC exactly; no generic labels or deviations |
| 2. Visuals | 3/4 | Excellent hierarchy and component placement; one tooltip weight inconsistency |
| 3. Color | 4/4 | Perfect adherence to diverging-fill formula, token usage, and semantic colors |
| 4. Typography | 2/4 | **Two blocker issues**: oversized empty-state heading, overstyled tooltip ticker label |
| 5. Spacing | 4/4 | All spacing tokens (xs–lg) used correctly per UI-SPEC scale |
| 6. Experience Design | 3/4 | Four-state shell coverage complete; keyboard focus visible but not optimal |

**Overall: 20/24** — Strong implementation with two typography violations that must be fixed before shipping.

---

## Top 3 Priority Fixes

### 1. BLOCKER: Fix "No ticker selected" empty-state heading typography
**File:** `frontend/components/charts/MainChart.tsx:76`  
**Issue:** Heading uses `text-base font-semibold` (16px/600) instead of spec'd Heading role (14px/500)  
**Current:** `<p className="text-base font-semibold text-terminal-text">No ticker selected</p>`  
**Fix:** `<p className="text-sm font-medium text-terminal-text">No ticker selected</p>`  
**Impact:** Empty state heading is 2px oversized and overweighted, breaks typography contract and visual hierarchy consistency  
**Requirement:** UI-SPEC Typography — Heading role must be 14/500

### 2. BLOCKER: Remove semibold emphasis from heatmap tooltip ticker label
**File:** `frontend/components/charts/PortfolioHeatmap.tsx:214`  
**Issue:** Tooltip ticker uses `font-semibold` (600) instead of spec'd Label role (400)  
**Current:** `<div className="font-semibold">{d.ticker}</div>`  
**Fix:** `<div>{d.ticker}</div>`  
**Impact:** Ticker label stands out incorrectly in tooltip; inconsistent with Label role definition  
**Requirement:** UI-SPEC Typography — Label role must be 12/400

### 3. ENHANCEMENT: Verify keyboard focus ring visibility on chart panels
**File:** `frontend/app/globals.css:62–64`  
**Issue:** Focus ring uses CSS outline; Tailwind ring classes may provide better visual feedback  
**Current:** `.recharts-surface:focus-visible { outline: 2px solid var(--color-terminal-text); outline-offset: 2px; }`  
**Assessment:** Current approach is valid per CSS spec, but consider testing visibility on dark theme with live user input  
**User Impact:** Keyboard navigation (Tab to MainChart, Tab to PnlHistoryChart) should show clear focus indicator  
**Requirement:** UI-SPEC Layout & Interaction Contract — keyboard affordance must be visible

---

## Detailed Findings

### Pillar 1: Copywriting (4/4) ✓ PASS

All UI text matches the design contract exactly — no deviations, no generic labels, no backfilled copy.

**Verified copy:**
- Main Chart empty state: "No ticker selected" + "Select a ticker from the watchlist to view its chart." ✓
- Main Chart loading state: "Waiting for price data…" ✓
- Panel headings: "Chart" (when selected), "Portfolio Heatmap", "Portfolio Value" ✓
- Portfolio Heatmap empty: "No positions to visualize — place a trade to see them here." ✓
- Portfolio Heatmap loading: "Loading portfolio…" ✓
- Portfolio Heatmap error: Passes through backend error text via `role="alert"` ✓
- PnL History empty: "Not enough history yet — check back after your first trade or ~30 seconds of activity." ✓
- PnL History loading: "Loading portfolio history…" ✓
- All error states render with `text-red-400 role="alert"` ✓

**Verification:** Grep audit across all chart component files confirms exact string matches to UI-SPEC Copywriting Contract table (lines 200–221 of UI-SPEC.md).

**Edge case verification:**
- Main Chart heading dynamically reads selected ticker symbol vs. literal "Chart" when null ✓
- Error text passthrough does not introduce unsanitized HTML ✓

---

### Pillar 2: Visuals (3/4) — Good with One Consistency Issue

Component architecture establishes clear visual hierarchy and focal points. Watchlist rows with embedded sparklines flow naturally into the main chart drill-down, which anchors a balanced two-column layout below. All interactive surfaces (charts, buttons, rows) have clear affordances.

**Strengths:**
- Sparklines embedded in every watchlist row at fixed 20px height (h-5), not collapsing rows on first data point ✓
- Main Chart panel positioned top-center, making it the primary drill-down focus ✓
- Portfolio Heatmap and Portfolio Value panels side-by-side at equal widths (flex-1), balanced visual weight ✓
- All line charts show end-of-line marker with surface-color ring (2px stroke) ✓
- Heatmap legend strip (15-step gradient with −10% / 0% / +10% labels) positioned header-right, legible and compact ✓
- Positions Table anchors the bottom of the center column, maintaining the Phase 2 structure ✓
- All four state branches (loading/error/empty/populated) render distinct copy, never a confusing blank panel ✓

**Issue identified:**
- Heatmap tooltip ticker label uses `font-semibold` (600 weight), causing it to stand out incorrectly compared to Weight/Change rows below it
- Should all render at Label role weight (400) per UI-SPEC
- **See Priority Fix #2 above**

**Verification:** Screenshot shows dense but scannable layout; no elements overlap or clip. Tooltip styling is consistent across MainChart and PnlHistoryChart but breaks on PortfolioHeatmap due to weight inconsistency.

---

### Pillar 3: Color (4/4) ✓ PASS

Color implementation is exemplary. All semantic tokens are respected, diverging-fill formula is mathematically correct, and no accent colors are misused.

**Token usage verified:**
- Dominant (60%) — `--color-terminal-bg` (#0d1117): Page background ✓
- Secondary (30%) — `--color-terminal-panel` (#1a1a2e): Chart panel surfaces, tooltip backgrounds ✓
- Neutral midpoint — `--color-terminal-border` (#30363d): Gridlines, axes, heatmap tiles at 0% ✓
- Gain — `--color-gain` (#4ade80, green): Uptrend lines, positive heatmap tiles ✓
- Loss — `--color-loss` (#f87171, red): Downtrend lines, negative heatmap tiles ✓
- Text — `--color-terminal-text` (#e6edf3): Primary, `--color-terminal-text-muted` (#8b949e): secondary ✓

**Diverging-fill formula (chartTheme.ts:70–80):**
```typescript
export function divergingFill(pctChange: number): string {
  return mixColor(
    HEX_NEUTRAL,
    pctChange >= 0 ? HEX_GAIN : HEX_LOSS,
    heatmapIntensity(pctChange),  // clamped to ±10%
  );
}
```
Verified: Uses `heatmapIntensity()` which clamps to `min(abs(pctChange), 10) / 10` ✓  
Saturation at ±10%: A +40% position renders identically to +10% ✓

**Tile text contrast:**
```typescript
export function tileTextColor(pctChange: number): string {
  return heatmapIntensity(pctChange) >= 0.5 ? HEX_INK_DARK : HEX_INK_LIGHT;
}
```
Dark ink on saturated fills (intensity ≥ 0.5), light ink on pale fills ✓

**Accent color reservation:**
- Yellow (#ecad0a): Only used on FinAlly wordmark and "SIMULATED" badge — not touched by charts ✓
- Purple (#753991): Only used on CTA buttons — not touched by charts ✓
- Blue (#209dd7): Only used on chat panel accent — not touched by charts ✓

**No hardcoded colors:** All chart colors are CSS variables or derived from the token palette via `mixColor()` ✓

---

### Pillar 4: Typography (2/4) — Two Blocker Issues

Typography deviates from the UI-SPEC contract in two places. Both are fixable one-line changes.

**Correct usage (verified via grep across all chart files):**
- Panel headings (MainChart, PortfolioHeatmap, PnlHistoryChart): `text-sm font-medium` (14px/500, Heading role) ✓
- Body copy (empty/loading/error state text): `text-sm` (14px/400, Body role) ✓
- Axis tick labels: `text-xs` (12px, Label role) ✓
- Numeric values: `tabular-nums` class applied ✓
- Heatmap tile labels (ticker/percent): fontSize 10, fontWeight 600 in SVG (10px/600, Micro/Badge role) ✓

**Issue 1: MainChart.tsx:76 — Oversized empty-state heading**
```typescript
// WRONG: 16px/600 instead of 14px/500
<p className="text-base font-semibold text-terminal-text">
  No ticker selected
</p>

// CORRECT: Should match Heading role
<p className="text-sm font-medium text-terminal-text">
  No ticker selected
</p>
```
**Impact:** Visually breaks the empty-state hierarchy; makes the heading too prominent compared to panel titles. Violates UI-SPEC Heading role definition (line 87: "14/500/1.3").

**Issue 2: PortfolioHeatmap.tsx:214 — Overweighted tooltip label**
```typescript
// WRONG: font-semibold (600) in tooltip
<div className="font-semibold">{d.ticker}</div>
<div className="tabular-nums">Weight {weight.toFixed(1)}%</div>
<div className="tabular-nums">Change {formatPercent(...)}</div>

// CORRECT: Should match Label role (12/400)
<div>{d.ticker}</div>
<div className="tabular-nums">Weight {weight.toFixed(1)}%</div>
<div className="tabular-nums">Change {formatPercent(...)}</div>
```
**Impact:** Ticker label stands out incorrectly, creating false emphasis hierarchy within a single tooltip. Violates UI-SPEC Label role (12/400, line 87).

**Verification:** Audited all `className` attributes in Sparkline, MainChart, PortfolioHeatmap, PnlHistoryChart. Only these two deviations found. All other font weights match contract.

---

### Pillar 5: Spacing (4/4) ✓ PASS

Every spacing value follows the UI-SPEC scale. No arbitrary values, no hidden gaps.

**Spacing scale verification (UI-SPEC lines 52–72):**

| Token | Value | Usage | Verified |
|-------|-------|-------|----------|
| xs | 4px | Not used in Phase 4 charts | — |
| sm | 8px | Compact element spacing | Tooltip padding (px-2) |
| md | 16px | Panel padding, inter-panel gaps | `p-4` on all panels, `gap-4` in center column |
| lg | 24px | Top-level column gaps | `gap-6` in main page flex (24px) |
| xl | 32px | Unused | — |

**Chart-specific spacing (exceptions):**
- Treemap tile gap: 2px (SVG strokeWidth, data separator — correct exception per UI-SPEC) ✓
- Chart end-marker ring: 2px (SVG strokeWidth, mark detail — correct exception per UI-SPEC) ✓

**Chart dimensions:**
- Sparkline container: `h-5` (20px) ✓ — exact match to UI-SPEC "fixed height `h-5` (20px)"
- MainChart area: `h-72` (288px) ✓ — matches UI-SPEC "full width, `h-72` / 288px chart area"
- Side-by-side panels (Heatmap, Value): `h-60` (240px each) ✓ — matches UI-SPEC "`h-60` / 240px"
- Chart margins (MainChart): `margin={{ top: 24, right: 16, bottom: 0, left: 0 }}` ✓ — top margin allows room for axis ticks
- Chart margins (PnlHistoryChart): `margin={{ top: 20, right: 16, bottom: 0, left: 0 }}` ✓ — consistent with main chart

**Tooltip/legend spacing:**
- Tooltip padding: `px-2 py-1` (8px × 4px) ✓ — compact, appropriate for small containers
- Legend gap: `gap-0.5` (2px) ✓ — intentionally tight for visual continuity
- Legend width: 120px ✓ — compact header-right placement

**No arbitrary values found.** All spacing tokens are from the declared scale or documented exceptions. ✓

---

### Pillar 6: Experience Design (3/4) — Solid State Coverage, Focus Ring Question

All four state branches (loading/error/empty/populated) are implemented across every chart panel. Keyboard activation works on watchlist rows. Accessibility layer opt-out is documented in Sparkline.

**State coverage:**

| Panel | Empty | Loading | Error | Populated |
|-------|-------|---------|-------|-----------|
| MainChart | "No ticker selected" + body copy | "Waiting for price data…" (when <2 points) | None (SSE sync, not a fetch) | Full line + axes + tooltip + end marker |
| PortfolioHeatmap | "No positions to visualize…" | "Loading portfolio…" (reuses usePortfolio) | role="alert", red-400 text | Treemap tiles, legend |
| PnlHistoryChart | "Not enough history yet…" (0 or 1 snapshot) | "Loading portfolio history…" | role="alert", red-400 text | Line + axes + tooltip + end marker |
| Positions Table | (Existing, unchanged) | (Existing) | (Existing) | (Existing) |

All copy matches UI-SPEC Copywriting Contract exactly ✓

**Keyboard activation:**
- WatchlistRow: `role="button"` + `tabIndex={0}` + Enter/Space keydown handler ✓
- Sparkline: Correctly opts out via `accessibilityLayer={false}` (Plan 04-05 documented decision) ✓
- MainChart + PnlHistoryChart: Keep Recharts' focusable surface for arrow-key tooltip navigation ✓
- PortfolioHeatmap: Never focusable (Treemap renders through Surface, not RootSurface) ✓

**Focus ring styling:**
- File: `frontend/app/globals.css:62–64`
- Current: `.recharts-surface:focus-visible { outline: 2px solid var(--color-terminal-text); outline-offset: 2px; }`
- Assessment: Valid CSS, matches browser :focus-visible spec (keyboard-only). Outline is slightly less bold than Tailwind `ring-*` classes but is acceptable.
- **Consideration:** Test with keyboard navigation in a live session to confirm visibility on dark background. Outline rendering may be harder to see than ring classes in some browsers/OS combinations.

**Positive validation:**
- Tooltip hover state on all charts (cursor + styled content) ✓
- Loading spinner behavior: reuses existing usePortfolio/usePortfolioHistory hooks ✓
- Error handling: passes backend errors through without HTML injection ✓
- Trend consistency: All charts use same `trendDirection()` helper against same `firstPrices` reference ✓

---

## Files Audited

**Chart Components:**
- `frontend/components/charts/chartTheme.ts` — Constants, trend rule, color helpers
- `frontend/components/charts/Sparkline.tsx` — Mini per-row chart
- `frontend/components/charts/MainChart.tsx` — **[BLOCKER: line 76]** Selected ticker chart
- `frontend/components/charts/PortfolioHeatmap.tsx` — **[BLOCKER: line 214]** Treemap heatmap
- `frontend/components/charts/PnlHistoryChart.tsx` — Portfolio value line chart

**Integration Points:**
- `frontend/components/watchlist/WatchlistRow.tsx` — Sparkline embedding, selection handler
- `frontend/app/page.tsx` — Center column restructuring, panel arrangement
- `frontend/app/globals.css` — Color tokens, focus-visible rule
- `frontend/app/layout.tsx` — Chart providers (ChartSelectionProvider, PortfolioHistoryProvider)
- `frontend/lib/chartSelection.tsx` — Selected ticker state
- `frontend/lib/portfolioHistoryStore.tsx` — Portfolio history polling
- `frontend/lib/priceStore.tsx` — Price history buffer

**Total Components Verified:** 11 files, 0 registry blocks, 100% of Phase 4 UI surface

---

## Recommendation Summary

**Ship readiness:** CONDITIONAL on fixing the two typography blockers.

**Before shipping:**
- Fix "No ticker selected" heading from `text-base font-semibold` to `text-sm font-medium`
- Remove `font-semibold` from heatmap tooltip ticker label
- Test keyboard focus visibility on MainChart and PnlHistoryChart in a live session

**After shipping (non-blocking):**
- Monitor end-user feedback on focus ring visibility; consider switching to Tailwind `ring-*` classes if outline proves too subtle
- Verify all font family fallbacks load correctly on diverse user systems (font stack uses system sans-serif)

**Strengths to celebrate:**
- Sparkling implementation of Recharts integration with zero component library bloat
- Diverging-fill heatmap formula is mathematically precise and beautiful
- Four-state shell pattern applied consistently across three new panels
- Keyboard accessibility properly scoped per chart role (sparkline opts out, panels keep navigation)
- Copy matches design contract 100% (9 distinct phrases across 4 panels)
- Color token discipline — no hardcoded hex outside the palette

---

**Audit Complete**  
*Phase 04 — Portfolio Visualization UI Review*  
*Conducted 2026-09-22*
