---
phase: 02-core-trading-ui
fixed_at: 2026-09-17T00:00:00Z
review_path: .planning/phases/02-core-trading-ui/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-17T00:00:00Z
**Source review:** .planning/phases/02-core-trading-ui/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (1 Critical, 2 Warning)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: Trade error message is garbled for any 422 validation failure, reachable via the default empty form

**Files modified:** `frontend/lib/api.ts`
**Commit:** dbd8c76
**Applied fix:** Added an `ApiErrorDetail` union type (`string | {msg, loc?}[]`) to `postTrade()`'s error parsing. When `detail` is an array (FastAPI's Pydantic 422 validation shape), the fix maps each error object to its `msg` field and joins them with `"; "` into a readable string. When `detail` is a string (the manually-raised `HTTPException(400, detail="...")` path in `execute_trade()`), it is used verbatim, preserving the D-03 invariant that the backend's own rejection text reaches the user unmodified. Only the fallback `HTTP {status}` path is used when the body isn't JSON at all — unchanged from before.

### WR-01: TradeBar has no client-side validation, letting trivially-invalid submissions reach the backend

**Files modified:** `frontend/components/trade-bar/TradeBar.tsx`
**Commit:** e57c1d2
**Applied fix:** Added guards in `submit()` before the `postTrade` call: an empty/whitespace-only ticker sets `error` to "Enter a ticker." and returns early; a non-finite or non-positive quantity sets `error` to "Enter a quantity greater than 0." and returns early. Also added `min="0"` to the quantity `<input type="number">` so the browser's own UI additionally discourages negative values (defense in depth, matching the Fix guidance's `min` attribute note). This does not touch the deliberate "no client-side pre-check of sufficient cash/shares" boundary documented in the component's header comment — only obviously-invalid (empty/non-positive) input is now blocked before the network call.

### WR-02: WatchlistPanel silently swallows fetch failures as "no tickers"

**Files modified:** `frontend/components/watchlist/WatchlistPanel.tsx`
**Commit:** 5892ed7
**Applied fix:** Added a distinct `error` state (`useState<string | null>(null)`), mirroring `PortfolioProvider`'s pattern. On success, `error` is cleared alongside setting `entries`. On failure, `error` is set to the caught error's message (or a fallback string) and `entries` is set to `[]`. The render logic now shows the error message (with `role="alert"`, matching the existing pattern used in `TradeBar.tsx` and `PositionsTable.tsx`) distinctly from the genuinely-empty-watchlist message, which now only renders when `entries.length === 0 && !error`.

## Skipped Issues

None — all findings were fixed.

## Verification

Verification ran in the **main checkout** (`C:/Users/jamal/projects/finally`), after the isolated worktree's commits were fast-forwarded onto `finally-gsd` and the worktree was torn down. The worktree itself has no `node_modules` (by design — it is created fresh per run), so `tsc`/`next build` could not run inside it; per-fix verification during editing used Tier 1 (re-read + structural check) only. The commands below are reproducible from the current state of `finally-gsd`:

- `npm --prefix frontend run typecheck` — exit 0, no errors.
- `npm --prefix frontend run build` — exit 0, Next.js static export compiled and generated successfully (4/4 pages).
- `cd backend && uv run pytest -q` — 139 passed, 0 failed, 2 pre-existing deprecation warnings (unrelated to this fix).

No regressions observed. All three in-scope findings (CR-01, WR-01, WR-02) are fixed and verified against the actual project toolchain.

---

_Fixed: 2026-09-17T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
