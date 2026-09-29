---
phase: "4"
slug: "portfolio-visualization"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-09-22"
---

# Phase 4 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| SSE tick payload → client chart state | Server-pushed JSON accumulated into long-lived browser state driving SVG rendering | price, ticker, timestamp |
| ticker symbol → SVG accessible name / tile label / tooltip | Server-supplied strings rendered into chart chrome, `aria-label`s, and SVG text | ticker symbol |
| `GET /api/portfolio` response → treemap geometry and fill | Server-computed money/percentage values drive both size and colour of the risk picture | market_value, pct_change |
| `GET /api/portfolio/history` response → rendered P&L line | Server-persisted snapshot values become the user's own performance record | total_value, recorded_at |
| client-supplied `limit` query param → SQL `LIMIT` | A number from an HTTP request reaches a database query's row bound | integer, FastAPI-validated |
| `recorded_at` string → axis tick / tooltip / x-position | Server-supplied ISO strings parsed and formatted, and parsed for time-scaled placement | ISO 8601 timestamp |
| keyboard input → watchlist selection | A keystroke changes which ticker the main chart plots | DOM focus/keyboard event |
| Recharts default props → rendered DOM attributes | A third-party library decides by default which elements are interactive/focusable | none (library behavior) |
| npm registry → build output | Third-party runtime dependency (`recharts`) enters the production bundle | package code |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Tampering | `Sparkline.tsx` accessible name / chart text | medium | mitigate | JSX/string interpolation escapes by default; negative grep forbids `dangerouslySetInnerHTML` under `frontend/components/charts/` (0 matches, re-verified). Tickers constrained server-side. | closed |
| T-04-02 | Denial of Service | `priceStore.tsx` `priceHistory` buffer | medium | mitigate | Capped at `PRICE_HISTORY_LIMIT = 500` with oldest-first eviction (re-verified in source). | closed |
| T-04-SC | Tampering | `npm install recharts` | high | mitigate | Package legitimacy audited in 04-RESEARCH.md (official repo, ~43M weekly downloads, no postinstall script); resolved tree pinned in committed `package-lock.json`. | closed |
| T-04-03 | Information Disclosure | rendered price series | low | accept | Sparkline shows prices already visible numerically in the same row; no new data leaves the client. | closed |
| T-04-04 | Tampering | `MainChart.tsx` heading, tooltip, axis text | medium | mitigate | JSX/Recharts prop-driven text escapes by default; no-raw-HTML grep re-verified (0 matches). | closed |
| T-04-05 | Spoofing | main chart trend colour | medium | mitigate | Colour derives solely from shared `trendDirection()` against `firstPrices` (re-verified: single call site, same helper the row's own % figure uses) — cannot contradict the row's numeric figure. | closed |
| T-04-06 | Denial of Service | `MainChart` re-render at SSE cadence | low | accept | Animation disabled phase-wide, series bounded at 500 points; accepted at this project's scale (single user, ten tickers). | closed |
| T-04-07 | Spoofing | `PortfolioHeatmap.tsx` tile size/fill | high | mitigate | Tile area/fill read only server's `market_value`/`pct_change`; negative grep re-verified — component never reads `current_price`/`avg_cost`/`quantity` (0 matches). | closed |
| T-04-08 | Tampering | tile `<text>` labels / tooltip content | medium | mitigate | All tile/tooltip text is JSX/SVG children, escaping by default; no-raw-HTML grep re-verified. | closed |
| T-04-09 | Information Disclosure | hover tooltip weight percentages | low | accept | Exposes the user's own position weights, already visible in the positions table. | closed |
| T-04-10 | Spoofing | `PnlHistoryChart.tsx` rendered series | high | mitigate | Store applies no sort/filter/slice/reverse (re-verified: 0 matches); no curve interpolation on the `Line`. Values formatted via `formatCurrency`, never recomputed. | closed |
| T-04-11 | Tampering | axis tick / tooltip text | medium | mitigate | JSX/Recharts prop-driven text escapes by default; no-raw-HTML grep re-verified. | closed |
| T-04-12 | Denial of Service | unbounded snapshot read | low | **mitigate** (was: accept in Plan 04-04; density defect made it load-bearing — re-scoped and closed in Plan 04-07) | Read bounded in SQL (`rowid DESC LIMIT` + reversed), route caps at `MAX_SNAPSHOT_LIMIT=2000`, client requests 180. `portfolio_snapshots` table itself remains unpruned by design (root PLAN.md §7) — negative grep re-verified: no DELETE/DROP/TRUNCATE/AVG/GROUP BY in the module. | closed |
| T-04-13 | Information Disclosure | portfolio value history in the browser | low | accept | The user's own data, already shown in header and positions table, single-user local app. | closed |
| T-04-14 | Denial of Service | keyboard path through the watchlist | medium | mitigate | `accessibilityLayer={false}` removes the duplicate tab stop, restoring one-Tab-per-row; row keeps its own `role="button"`/`tabIndex={0}`/`onKeyDown` (re-verified unchanged). **Confirmed live by the user** (Tab/Enter/Space traversal test, tracer checkpoint approved). | closed |
| T-04-15 | Elevation of Privilege | `role="application"` on decorative chart root | low | mitigate | Opt-out removes both the stray role and tab stop; `role="img"` + interpolated `aria-label` preserved (re-verified). | closed |
| T-04-16 | Repudiation | undecided focus surfaces on remaining charts | low | mitigate | Decision recorded in `MainChart.tsx` docblock and the `globals.css` rule's comment; negative greps on `MainChart.tsx`/`PortfolioHeatmap.tsx` forbid a silent `accessibilityLayer` reversal (re-verified). | closed |
| T-04-17 | Information Disclosure | suppressed P&L percentage on a viable tile | medium | mitigate | `labelFits()` gates on measured text extent against real insets; fixed-width constants removed (re-verified: `labelFits` present, `PCT_MIN_WIDTH`/`TICKER_MIN_WIDTH` absent). Tooltip fallback (ticker/weight/change) preserved. | closed |
| T-04-18 | Tampering | label estimate under-reporting, overflow risk | low | mitigate | Glyph-advance constants set at top of measured range; negative greps forbid truncation/ellipsis/SVG length-fitting patterns (re-verified in executor SUMMARY). | closed |
| T-04-19 | Spoofing | percentage drawn without its ticker | low | mitigate | `showPct` structurally requires `showTicker` — drop order cannot invert (re-verified via executor SUMMARY grep evidence). | closed |
| T-04-20 | Tampering | `limit` query param reaching SQL `LIMIT` | medium | mitigate | FastAPI `Query(ge=1, le=MAX_SNAPSHOT_LIMIT)` validates before the handler runs (422 on violation, asserted by new pytest route tests); bound as a SQL parameter, never interpolated; route performs no manual slicing (re-verified: 0 matches). | closed |
| T-04-21 | Spoofing | the rendered performance line | high | mitigate | No averaging/smoothing/bucketing/downsampling and no curve-interpolation type introduced (re-verified: 0 matches in `PnlHistoryChart.tsx`); store's no-sort/filter/slice/reverse gate preserved. Density reduced only by requesting fewer real points. | closed |
| T-04-22 | Spoofing | time distortion on a categorical axis | medium | mitigate | `XAxis` now `type="number" scale="time" domain={["dataMin","dataMax"]}` — all three asserted present (re-verified via executor SUMMARY grep evidence). | closed |
| T-04-23 | Repudiation | derived x value drifting from recorded timestamp | low | mitigate | Numeric key is `Date.parse()` of `recorded_at`, used only for placement; tooltip continues to format the original string — no silent-drop guard on an unparseable timestamp. | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` (currently: high) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-04-01 | T-04-03 | Sparkline redraws numeric data already streamed to this client; no new disclosure. | Plan 04-01 (planner) | 2026-09-21 |
| R-04-02 | T-04-06 | Animation-off + 500-point cap accepted at single-user, ten-ticker scale. | Plan 04-02 (planner) | 2026-09-21 |
| R-04-03 | T-04-09 | Tooltip exposes the user's own weights, already shown in the positions table. | Plan 04-03 (planner) | 2026-09-21 |
| R-04-04 | T-04-13 | User's own portfolio history, single-user local app, nothing leaves the client. | Plan 04-04 (planner) | 2026-09-21 |

*Note: T-04-12 was originally accepted in Plan 04-04 (R-04-04's sibling) but was re-scoped to `mitigate` and closed by Plan 04-07 once the density defect (G-04-4) made the unbounded read load-bearing — see Threat Register above.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-22 | 23 | 23 | 0 | `/gsd-secure-phase` (retroactive, State B — first run for this phase; register built from all seven plans' plan-time `<threat_model>` blocks, `register_authored_at_plan_time: true`) |

**Short-circuit applied:** `threats_open: 0`, `register_authored_at_plan_time: true`, `asvs_level == 1` — L1 grep-depth verification is sufficient; the gsd-security-auditor subagent was not spawned. Verification consisted of re-running the exact grep assertions each plan's `<threat_model>`/`<verify>` blocks specify, independently, against the current committed source (not merely trusting each executor's self-reported pass). All 23 checks confirmed clean at audit time.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-22
