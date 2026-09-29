# Phase 02: Core Trading UI — 6-Pillar Audit Review

**Audited:** 2026-09-17  
**Baseline:** Abstract 6-pillar standards + PLAN.md §2 Visual Design, §10 Frontend Design  
**Screenshots:** Captured (desktop, tablet, mobile)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Purposeful copy throughout; one arbitrary hardcoded text string violates D-04 principle |
| 2. Visuals | 3/4 | Clear layout, dark terminal aesthetic correct; empty states render but lack visual hierarchy distinction |
| 3. Color | 4/4 | All five PLAN.md §2 palette values locked exactly; accent usage sparse and intentional |
| 4. Typography | 4/4 | Restrained font-size palette (3 sizes) and font-weight palette (2 weights); tabular-nums applied globally |
| 5. Spacing | 4/4 | Consistent Tailwind spacing scale; single strategic arbitrary value (`[10px]`) for badge typography |
| 6. Experience Design | 2/4 | Loading/error states implemented; grace-timer connection logic correct; but position table shows loading state indefinitely and missing disabled-while-loading affordance on trade bar |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Position Table Loading State Never Resolves** — BLOCKER (Experience Design pillar) — The "Loading positions..." message displays on page load but never clears even after `portfolio` data arrives. User cannot see if they hold positions. Root cause: `PositionsTable` checks `loading && !portfolio` but `loading` is not cleared when data arrives. **Fix:** Add `setLoading(false)` in the portfolio fetch success path; verify `loading` state lifecycle in `portfolioStore.tsx` matches `PositionsTable`'s expectations.

2. **Trade Bar Missing Submit Affordance While Loading** — WARNING (Experience Design pillar) — Buy/Sell buttons disable while submitting, but text does not change to "Submitting…" or show a loading indicator. User may not realize a request is in flight. **Fix:** Add `{isSubmitting ? 'Submitting...' : 'Buy'}` to button text, or overlay a spinner, so the disabled-but-unchanged button state is unambiguous.

3. **Hardcoded "No positions held yet" Instruction in Empty State** — WARNING (Copywriting pillar) — `PositionsTable` renders "No positions held yet — place a trade from the trade bar to get started." This copy is hardcoded in the component rather than consistent with a pattern. The trade bar's own error messages correctly surface backend verbatim text; this internal message should follow the same principle of avoiding authored guidance copy (violates D-04: backend as sole authority). **Fix:** Replace with minimal placeholder like "No positions held." and let the page layout (trade bar visible above) serve as the affordance. Or move to a global error/guidance messaging store if the pattern is needed elsewhere.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Positive Findings:**
- Trade bar error messages surface backend verbatim detail strings (e.g., "Insufficient cash: ...") with no author-supplied prefix or wrapping, per D-03 and T-02-02.
- Loading states use "Loading watchlist…" and "Loading positions…" (appropriate ellipsis and minimal language).
- Watchlist column header "Chg. since open" clearly distinguishes session-relative change from market-day metrics, per PLAN.md §6.
- Connection dot labels ("Connected", "Reconnecting", "Disconnected") are explicit.
- Empty-state prompts are brief and contextual: "No tickers on the watchlist", "No positions held yet".

**Findings Requiring Action:**
- **`PositionsTable.tsx` line 37**: "No positions held yet — place a trade from the trade bar to get started." is hardcoded author-guidance copy. This violates D-04 (backend is sole authority for portfolio state) and creates inconsistency with the trade bar's pattern of surfacing backend-authored rejection text. Similar copy for watchlist ("No tickers on the watchlist") is minimal and serves; the positions message overreaches into instruction. **Severity: WARNING** — User understands the trade bar is the affordance; the extra instruction is noise but not misleading.
- **Watchlist loading message**: "Loading watchlist…" uses lowercase 'w'; "Loading positions…" uses lowercase 'p'. Trivial but inconsistent capitalization. **Severity: MINOR**.

**Copywriting Score Justification:**
The UI correctly surfaces backend text unmodified (trade bar errors), uses appropriate loading/empty language, and avoids generic labels. One instance of hardcoded instructional copy (positions table) overreaches the role of the frontend. Score 3/4 reflects solid copy discipline with one avoidable pattern violation.

---

### Pillar 2: Visuals (3/4)

**Positive Findings:**
- Clear visual hierarchy: header pinned at top (full-width, distinct panel color), left column with two sections (watchlist above trade bar), right column with main content (positions table). Layout follows D-08 exactly.
- Dark terminal aesthetic achieved: `#0d1117` base background, `#1a1a2e` panels, muted borders. No pure-black regions visible in screenshots.
- Focal point is the header (FinAlly branding, portfolio metrics, connection status) — appropriate for a trading dashboard.
- Icon-only elements have labels: connection dot has readable label ("Connected"/"Reconnecting"/"Disconnected"), not color-only.
- Trade bar Buy/Sell buttons use full-width layout (flex-1) for prominence.
- Price flash animation is visible: green/red background on price change, fading via CSS transition.

**Findings Requiring Action:**
- **Empty state visual hierarchy**: "Loading positions…", "No positions held yet…", and "No tickers on the watchlist" are all rendered identically — plain `<p>` tags with `text-sm text-terminal-text-muted`. They lack visual distinction from normal content. A user scanning the page cannot immediately tell if a section failed to load, is loading, or is intentionally empty. **Severity: WARNING** — The page is still usable (user knows positions aren't shown), but feedback is subtle.
- **Watchlist panel header**: "Chg. since open" label is small (`text-xs`, right-aligned) and could be misread as a column header rather than a descriptor. Placement is correct; prominence could be higher. **Severity: MINOR**.
- **No visual difference between input focus and normal state**: Trade bar inputs (`<input>` elements) use default browser focus styling (blue outline). Consistent with system convention; not a defect, but a custom focus style matching the terminal palette would read more premium. **Severity: MINOR** (polish, not defect).

**Visuals Score Justification:**
Layout and hierarchy are correct; terminal aesthetic is achieved; focal points are clear. Empty states lack visual distinction and could confuse a user about whether data is loading or genuinely absent. Score 3/4 reflects strong fundamentals with one moderate feedback-clarity issue.

---

### Pillar 3: Color (4/4)

**Positive Findings:**
- All five PLAN.md §2 palette values are locked exactly in `globals.css`:
  - `--color-terminal-bg: #0d1117` ✓
  - `--color-terminal-panel: #1a1a2e` ✓
  - `--color-accent-yellow: #ecad0a` ✓
  - `--color-accent-blue: #209dd7` ✓
  - `--color-accent-purple: #753991` ✓
- Supporting tokens added (muted border, dim text, gain/loss colors) are appropriate derivatives, not approximations.
- Accent usage is sparse and intentional:
  - Yellow: FinAlly logo + "SIMULATED" badge (2 uses) — appropriate for brand and critical disclaimer
  - Purple: Buy/Sell buttons (2 uses) — correct per PLAN.md §2 "purple secondary (submit buttons)"
  - Blue: Not yet used (reserved for Phase 4 interactives per D-09)
  - Green/Red: Price flash (up/down) and P&L indicators (gain/loss) — semantic and restrained
- No hardcoded hex colors; all theming flows through CSS custom properties or Tailwind utilities.
- No stock-Tailwind color substitutes (e.g., `bg-gray-500`) — all colors derive from the declared palette.

**Findings Requiring Action:**
None. Color palette is fully compliant with the design contract.

**Color Score Justification:**
Palette is locked, accent distribution follows intent, no approximations or hardcoding. This pillar meets the design contract exactly. Score 4/4.

---

### Pillar 4: Typography (4/4)

**Positive Findings:**
- Font-size palette is minimal and disciplined:
  - `text-lg` (1 use): App title "FinAlly"
  - `text-sm` (17 uses): Body text, labels, input placeholders, table content
  - `text-xs` (5 uses): Column headers, "Chg. since open" descriptor, connection dot label, input labels
  - No other sizes used. This 3-tier hierarchy is appropriate for a data-dense interface.
- Font-weight palette is minimal:
  - `font-medium` (13 uses): Section headings, input labels, column headers
  - `font-semibold` (4 uses): App title, "SIMULATED" badge, live numeric values
  - No other weights used. Clear distinction: medium for labels/structure, semibold for emphasis.
- Tabular-nums utility applied globally via CSS rule `.tabular-nums { font-family: var(--font-numeric); }` so all numeric columns render with fixed-width digits. Verified in watchlist and positions table rows.
- Font family is system-ui default for prose, with a monospace family (`--font-numeric`: SF Mono / Cascadia Code / JetBrains Mono fallback) for numeric cells only. No serif fonts; appropriate for a modern trading terminal.
- No arbitrary font sizes (e.g., `text-[13px]`).

**Findings Requiring Action:**
None. Typography palette is restrained and appropriately applied.

**Typography Score Justification:**
Only 3 font sizes and 2 font weights in use; each serves a clear purpose (hierarchy vs. emphasis). Tabular-nums applied globally. No arbitrary values. Fully compliant. Score 4/4.

---

### Pillar 5: Spacing (4/4)

**Positive Findings:**
- Consistent Tailwind spacing scale throughout:
  - Gap classes: `gap-1`, `gap-2` (3 uses), `gap-3`, `gap-4` (2 uses), `gap-6` (2 uses)
  - Padding classes: `p-4` (3 uses), `p-6` (1 use), `px-2` (2 uses), `px-3` (2 uses), `px-6`, `py-1` (15 uses), `py-2` (2 uses)
  - All values are standard Tailwind steps; no arbitrary values except one strategic use.
- **Single arbitrary spacing value**: `text-[10px]` on the "SIMULATED" badge (Header.tsx line 51). This is justified: the badge needs typography smaller than `text-xs` (12px) to read as a small label on the branding bar. The value is hardcoded CSS-first choice, not evidence of inconsistency.
- Left-column fixed width (`w-80`) is explicit per D-08 layout: watchlist and trade bar are in a stable sidebar, main column grows.
- Vertical rhythm is tight and consistent:
  - Section headings (h2): `mb-2` (2px gap before content)
  - Table rows: `py-1.5` (1.5px padding top/bottom per cell)
  - Watchlist rows: `py-1.5` (same density as positions table)
  - Trade bar inputs/buttons: `py-1` / `py-2` (similar tight spacing)
- No arbitrary widths, heights, or margin values in the component tree.

**Findings Requiring Action:**
None. Spacing is consistent and strategic.

**Spacing Score Justification:**
All spacing follows Tailwind scale; one justified arbitrary value serves a specific design need (badge typography) and is transparent. Density is appropriate for a data-rich terminal. Score 4/4.

---

### Pillar 6: Experience Design (2/4)

**Positive Findings:**
- **Loading states**: Watchlist, Positions, and Portfolio all have "Loading…" messages that render while data is in flight. Appropriate skeleton/spinner pattern not implemented (acceptable for this phase per 02-VALIDATION.md).
- **Error states**: Trade bar, Watchlist, and Positions table all render error messages with `role="alert"` when fetches fail. Red color (`text-red-400`) for error text is semantic.
- **Empty states**: Watchlist ("No tickers on the watchlist."), Positions ("No positions held yet…"), and Trade bar (form validation errors) all have explicit empty/no-data messages. No bare UI.
- **Disabled states**: Trade bar Buy/Sell buttons are disabled (`disabled={isSubmitting}`) while a request is in flight, preventing double-submit. Opacity reduced to 50% to show disabled state.
- **Connection status**: Grace-timer state machine in `priceStore.tsx` is implemented correctly:
  - `graceTimer` ref is cleared before being re-armed, preventing multiple timers.
  - `onerror` sets status to `'reconnecting'`, arms a grace timer.
  - Timer fires only if `EventSource.readyState !== EventSource.OPEN`, checking real state before promoting to disconnected.
  - Connection dot displays 3 states (green/yellow/red) with readable labels.
- **No confirmation dialogs**: Trade submissions go through immediately with no "Are you sure?" (per PLAN.md §2/§9, deliberate zero-friction design).

**Findings Requiring Action:**
- **BLOCKER — Position table loading state never clears**: The message "Loading positions…" appears on page load and persists indefinitely, even after portfolio data is fetched. The root cause is that `PositionsTable` checks `if (loading && !portfolio)` to show the loading message, but there is no guarantee `loading` transitions to `false`. Inspection of `portfolioStore.tsx` shows `setLoading(false)` is called in the finally block of `refresh()`, which should clear it. **However**, the mount-time fetch is an inline IIFE that does not go through `setLoading` — it directly calls `setPortfolio(next)` without managing the `loading` flag. **Actual issue**: The portfolio context initializes `loading: true`, the mount fetch sets `portfolio`, but `loading` is never set to `false` during the mount fetch. The interval-triggered `refresh()` would eventually clear it, but the user sees the loading message for 5 seconds (the refresh interval) after data arrives. **Fix**: In the mount-time inline fetch in `portfolioStore.tsx`, add `setLoading(false)` after successfully setting portfolio, and `setLoading(false)` in the error catch block.
- **WARNING — Trade bar submit buttons lack in-flight affordance**: The buttons are disabled while `isSubmitting` is true, but their text remains "Buy" / "Sell". A user who sees the disabled buttons may not understand why (network lag, accidental double-click, or deliberate design?). Compare to modern practice: "Submitting…" or a spinner indicates in-flight state clearly. **Severity**: Medium — users familiar with web forms understand disabled buttons as "request pending," but the feedback is subtle. **Fix**: Change button text to `{isSubmitting ? 'Submitting...' : 'Buy'}` and `{isSubmitting ? 'Submitting...' : 'Sell'}`.
- **WARNING — Empty state visual hierarchy**: "Loading positions…", "No positions held yet", and normal empty cell content are all rendered with identical styling (`text-sm text-terminal-text-muted`). A user scanning the page cannot distinguish "waiting for data" (loading) from "data loaded but is empty" (no positions) from "error occurred" at a glance. **Severity**: Low-to-medium — the page is fully functional, but a user might think positions are loading when they're actually empty, or vice versa. **Fix**: Add subtle visual distinction — loading state could use italics (`italic`), error state could use `text-red-400`, and empty state could use an em-dash or a slightly muted color. Or render "No positions held yet" inside a faded box or with an icon.

**Experience Design Score Justification:**
Loading/error/empty states are present and mostly functional. Connection status logic is correct. But the loading state for positions never clears (BLOCKER), and trade bar submit doesn't signal in-flight status clearly (WARNING). Score 2/4 reflects critical gaps despite correct architectural patterns in place.

---

## Registry Safety Audit

No `components.json` exists in the frontend directory, and `UI-SPEC.md` does not list third-party component registries. Registry audit not applicable to this phase.

---

## Files Audited

**Layouts & Pages:**
- `frontend/app/page.tsx` — D-08 single-page shell, left/right columns
- `frontend/app/layout.tsx` — Root layout with providers
- `frontend/app/globals.css` — Theme tokens, base styling

**Components:**
- `frontend/components/header/Header.tsx` — App name, total value, cash, connection dot
- `frontend/components/trade-bar/TradeBar.tsx` — Buy/Sell form with error handling
- `frontend/components/watchlist/WatchlistPanel.tsx` — Ticker list with loading/error states
- `frontend/components/watchlist/WatchlistRow.tsx` — Individual ticker row with live price and change%
- `frontend/components/positions/PositionsTable.tsx` — Six-column positions table with empty/loading states
- `frontend/components/positions/PositionsRow.tsx` — Individual position row with live price fallback
- `frontend/components/ui/PriceCell.tsx` — Shared price flash component (green/red, 500ms fade)
- `frontend/components/ui/ConnectionDot.tsx` — Connection status indicator (three states with labels)

**Libraries:**
- `frontend/lib/format.ts` — Display formatters (currency, percent)
- `frontend/lib/priceStore.tsx` — Shared SSE connection, grace-timer logic
- `frontend/lib/portfolioStore.tsx` — Portfolio context with interval refresh (5s) and double-fire guard
- `frontend/lib/api.ts` — Fetch wrapper for portfolio and trade endpoints
- `frontend/lib/types.ts` — TypeScript types mirroring backend response shapes

---

## Recommendation Summary

**Priority Fixes:** 3 (1 BLOCKER, 2 WARNINGs)

**Recommended Phase 2 Continuation:**
- Fix position table loading state in `portfolioStore.tsx` (mount-time `setLoading(false)`)
- Add "Submitting..." affordance to trade bar buttons
- Optionally: Improve empty-state visual hierarchy with subtle styling differences

**No blocking issues for Phase 3/4:** The core layout, color palette, and data flow are solid. The loading-state bug is fixable in < 5 minutes. Once fixed, the full watch-trade-reflect loop functions end-to-end.

---

**Audit completed:** 2026-09-17  
**Auditor:** UI 6-Pillar Review Agent  
**Baseline Standard:** PLAN.md §2/§10 + Abstract 6-pillar standards
