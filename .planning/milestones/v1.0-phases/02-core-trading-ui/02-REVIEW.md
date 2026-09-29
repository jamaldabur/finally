---
phase: 02-core-trading-ui
reviewed: 2026-09-17T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - .gitignore
  - backend/app/main.py
  - backend/tests/test_main.py
  - frontend/.env.example
  - frontend/.gitignore
  - frontend/AGENTS.md
  - frontend/app/favicon.ico
  - frontend/app/globals.css
  - frontend/app/layout.tsx
  - frontend/app/page.tsx
  - frontend/CLAUDE.md
  - frontend/components/header/Header.tsx
  - frontend/components/positions/PositionsRow.tsx
  - frontend/components/positions/PositionsTable.tsx
  - frontend/components/trade-bar/TradeBar.tsx
  - frontend/components/ui/ConnectionDot.tsx
  - frontend/components/ui/PriceCell.tsx
  - frontend/components/watchlist/WatchlistPanel.tsx
  - frontend/components/watchlist/WatchlistRow.tsx
  - frontend/eslint.config.mjs
  - frontend/lib/api.ts
  - frontend/lib/format.ts
  - frontend/lib/portfolioStore.tsx
  - frontend/lib/priceStore.tsx
  - frontend/lib/types.ts
  - frontend/next.config.ts
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/postcss.config.mjs
  - frontend/public/file.svg
  - frontend/public/globe.svg
  - frontend/public/next.svg
  - frontend/public/vercel.svg
  - frontend/public/window.svg
  - frontend/README.md
  - frontend/tsconfig.json
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Summary

Reviewed the phase 02 (Core Trading UI) frontend build — SSE price store with its connection-status grace timer, the trade bar, the flash-on-change price cell, the positions table, the header, and the backend's dev-only CORS addition — plus the create-next-app scaffolding files.

The SSE connection-status state machine in `priceStore.tsx` and the flash-trigger comparison in `PriceCell.tsx` were traced closely against `backend/app/market/cache.py`'s `previous_price`/`direction` semantics and hold up: both correctly anchor to what the client itself last rendered/observed rather than trusting a stale field, and the grace-timer clear-before-arm pattern prevents a stuck red dot. The positions table also correctly upholds the "no client-side arithmetic on server-authoritative values" invariant — the only place `quantity * price` is computed client-side is `Header.tsx`'s explicitly-sanctioned live total.

The one real defect is in the trade bar's error-surfacing path: `postTrade()` assumes the backend's error body always carries a `detail: string`, but FastAPI's own Pydantic validation (`TradeRequest.quantity: Field(gt=0)`, `.ticker: Field(min_length=1)`) returns `detail` as an *array* of error objects on a 422, and the trade bar has no client-side guard stopping a blank ticker/quantity submission from ever reaching that path — meaning the most basic first interaction (clicking Buy or Sell before typing anything) surfaces a garbled, unreadable error instead of the human-readable message the design explicitly requires (D-03).

## Critical Issues

### CR-01: Trade error message is garbled for any 422 validation failure, reachable via the default empty form

**File:** `frontend/lib/api.ts:41-48`, `frontend/components/trade-bar/TradeBar.tsx:19-47`

**Issue:**
`postTrade()` types the error body as `{ detail?: string }` and passes `parsed.detail` straight into `new Error(...)`:

```ts
const parsed: { detail?: string } = await res
  .json()
  .catch(() => ({ detail: undefined }));
throw new Error(parsed.detail ?? `HTTP ${res.status}`);
```

But `backend/app/routes/portfolio.py:24-27` defines:

```python
class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
```

FastAPI's default handler for a Pydantic validation failure (422) returns `{"detail": [{"type": ..., "loc": ..., "msg": ..., "input": ...}, ...]}` — `detail` is an **array of objects**, not a string. Only the manually-raised `HTTPException(400, detail="...")` path in `execute_trade()` produces a string `detail`.

`TradeBar.submit()` (`frontend/components/trade-bar/TradeBar.tsx:26-47`) has no guard before calling `postTrade`: both `ticker` and `quantity` start as `""`, and `Number("")` is `0`, `Number("abc")` is `NaN` (which `JSON.stringify` silently turns into `null`). Any of: clicking Buy/Sell with the form still blank, typing a non-numeric quantity, or typing `0`/a negative quantity will hit the 422 path.

When that happens, `new Error(arrayOfObjects)` coerces the array via `Array.prototype.toString`, which calls `toString()` on each plain object — the user sees literally `"[object Object]"` (or a comma-joined run of them) in the inline error banner, instead of a usable message. This directly violates the documented invariant in the file's own header comment ("The backend's own rejection text ... is the message the user must see (D-03) — never a generic substitute") for the single most likely first interaction with the app.

**Fix:** Handle both `detail` shapes in `api.ts`, and add a client-side guard in `TradeBar` so obviously-invalid input never reaches the network call in the first place (defense in depth — see WR-01 below):

```ts
// lib/api.ts
type ApiErrorDetail = string | { msg: string; loc?: (string | number)[] }[];

export async function postTrade(body: TradeRequest): Promise<TradeResponse> {
  const res = await fetch(`${BASE}/api/portfolio/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const parsed: { detail?: ApiErrorDetail } = await res
      .json()
      .catch(() => ({ detail: undefined }));
    const message = Array.isArray(parsed.detail)
      ? parsed.detail.map((e) => e.msg).join("; ")
      : (parsed.detail ?? `HTTP ${res.status}`);
    throw new Error(message);
  }
  return res.json();
}
```

## Warnings

### WR-01: TradeBar has no client-side validation, letting trivially-invalid submissions reach the backend

**File:** `frontend/components/trade-bar/TradeBar.tsx:26-47`

**Issue:** `submit()` never checks that `normalizedTicker` is non-empty or that `parsedQuantity` is a finite, positive number before calling `postTrade`. The quantity `<input type="number">` (line 68-76) has no `min` attribute, so the browser doesn't even block a negative value. This is what makes CR-01 reachable on the very first click, and independent of the api.ts fix, it means every avoidable round trip to the backend for a definitely-invalid trade still happens.

**Fix:**
```ts
async function submit(side: Side) {
  if (isSubmitting) return;

  const normalizedTicker = ticker.trim().toUpperCase();
  const parsedQuantity = Number(quantity);

  if (!normalizedTicker) {
    setError("Enter a ticker.");
    return;
  }
  if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) {
    setError("Enter a quantity greater than 0.");
    return;
  }

  setIsSubmitting(true);
  // ...
}
```

### WR-02: WatchlistPanel silently swallows fetch failures as "no tickers"

**File:** `frontend/components/watchlist/WatchlistPanel.tsx:19-29`

**Issue:**
```ts
useEffect(() => {
  let cancelled = false;
  (async () => {
    try {
      const { watchlist } = await fetchWatchlist();
      if (!cancelled) setEntries(watchlist);
    } catch {
      if (!cancelled) setEntries([]);
    }
  })();
  ...
}, []);
```
Any failure from `fetchWatchlist()` (network error, backend down, 500) is caught and discarded — the `catch` block has no parameter, no logging, and no distinct error state. The component then renders "No tickers on the watchlist," which is indistinguishable from a genuinely empty watchlist and actively misleads the user about what actually happened. This is inconsistent with `PortfolioProvider` (`lib/portfolioStore.tsx:55-61, 72-80`) and `TradeBar`, both of which track and surface a distinct `error` state for the same class of failure.

**Fix:** Track an error state and render it distinctly from the empty-watchlist case, mirroring `PortfolioProvider`'s pattern:
```ts
const [entries, setEntries] = useState<WatchlistEntry[] | null>(null);
const [error, setError] = useState<string | null>(null);
// ...
} catch (e) {
  if (!cancelled) {
    setError(e instanceof Error ? e.message : "Failed to load watchlist");
    setEntries([]);
  }
}
```
and render `error` with the same `role="alert"` pattern used elsewhere before falling back to the "No tickers" message.

## Info

### IN-01: Initial connection status is mislabeled "reconnecting" before any connection has ever succeeded

**File:** `frontend/lib/priceStore.tsx:59`

**Issue:** `useState<ConnectionStatus>("reconnecting")` is the initial value shown before the `EventSource` has ever opened. On first page load this reads as "Reconnecting" in the header dot/label even though the app is not recovering from any prior connection — it's connecting for the first time. `ConnectionStatus` has no dedicated "connecting" state to distinguish first-connect from recovery-after-drop.

**Fix:** Either add a fourth `"connecting"` status distinct from `"reconnecting"` for the pre-first-`onopen` window, or relabel the initial state's displayed text in `ConnectionDot` when it hasn't yet transitioned from the initial value.

### IN-02: PortfolioProvider duplicates fetch/set/error/loading logic between its mount effect and `refresh()`

**File:** `frontend/lib/portfolioStore.tsx:48-61` vs `69-87`

**Issue:** The mount-only effect re-implements the same `fetchPortfolio()` → `setPortfolio`/`setError`/`setLoading` sequence that `refresh()` already encapsulates, rather than calling `refresh()` directly. The in-code comment explains this is deliberate (to keep a lint rule about "setState in effect" happy), but it still means any future change to error handling or response shaping in `refresh()` must be mirrored by hand in the mount effect or the two paths will silently drift.

**Fix:** If the lint constraint is real, consider extracting a shared `async function loadPortfolio(): Promise<PortfolioResponse>` (no state calls) that both the mount effect and `refresh()` call, so only the state-setting is duplicated instead of the full fetch/parse/catch logic.

### IN-03: Position quantity rendered with no numeric formatting

**File:** `frontend/components/positions/PositionsRow.tsx:44-46`

**Issue:** Every other numeric column in the row goes through `formatCurrency`/`formatSignedCurrency`/`formatPercent` or `PriceCell`'s `.toFixed(2)`. `quantity` is rendered raw: `{position.quantity}`. Since `quantity` is a `REAL` column accumulating fractional shares across multiple buys/sells, a value like `0.30000000000000004` (classic float-accumulation artifact) or a long-tail decimal would render verbatim in the UI with no rounding.

**Fix:** Format with a fixed precision appropriate for fractional shares, e.g. `position.quantity.toFixed(4)` (trimmed of trailing zeros if desired), consistent with how every other numeric cell in this table is formatted.

---

_Reviewed: 2026-09-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
