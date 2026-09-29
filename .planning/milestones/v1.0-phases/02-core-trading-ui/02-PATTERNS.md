# Phase 2: Core Trading UI - Pattern Map

**Mapped:** 2026-09-17
**Files analyzed:** 16 (frontend scaffold + config)
**Analogs found:** 0 exact / 16 (greenfield — no existing `frontend/` code). All patterns below are sourced from RESEARCH.md's verified Code Examples (already cross-checked against backend contracts and Next.js/Tailwind docs) plus the backend route modules that define the API contract these files must consume.

**Read-only note:** `frontend/` does not exist in the repo yet (verified: `git ls-files -- frontend` returns nothing). There is no in-repo frontend analog to copy from. The "closest analog" for every new file is either (a) the RESEARCH.md code example that already encodes the correct pattern for this exact file, or (b) the backend route module whose response shape the file must mirror.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/lib/types.ts` | model (TS types) | transform | `backend/app/routes/portfolio.py`, `backend/app/routes/watchlist.py`, `backend/app/routes/stream.py` (response shapes) | contract-match (cross-language) |
| `frontend/lib/api.ts` | service (fetch wrapper) | request-response | RESEARCH.md Pattern 2 (`lib/api.ts` code example) | exact (research-provided) |
| `frontend/lib/priceStore.tsx` | provider/store | streaming (SSE) | RESEARCH.md Pattern 1 (`lib/priceStore.tsx` code example) | exact (research-provided) |
| `frontend/app/layout.tsx` | provider (root layout) | request-response | none — greenfield scaffold; see Shared Patterns "Provider wiring" | no analog |
| `frontend/app/page.tsx` | component (page composition) | request-response | RESEARCH.md "System Architecture Diagram" + "Recommended Project Structure" | role-match (research-provided) |
| `frontend/app/globals.css` | config (theme tokens) | transform | RESEARCH.md Pitfall 5 (`@theme` block example) | exact (research-provided) |
| `frontend/components/header/Header.tsx` | component | streaming + request-response | RESEARCH.md "Header live total value" code example (`useLiveTotalValue`) | exact (research-provided) |
| `frontend/components/ui/ConnectionDot.tsx` | component | streaming | RESEARCH.md Pattern 1 (`status` context value) | role-match (research-provided) |
| `frontend/components/ui/PriceCell.tsx` | component | streaming | RESEARCH.md Pattern 3 (`PriceCell` full code example) | exact (research-provided) |
| `frontend/components/watchlist/WatchlistPanel.tsx` | component | request-response + streaming | `backend/app/routes/watchlist.py` (`WatchlistResponse` shape) + Pattern 1 | role-match |
| `frontend/components/watchlist/WatchlistRow.tsx` | component | streaming | RESEARCH.md Pattern 3 (`PriceCell` usage) | role-match |
| `frontend/components/trade-bar/TradeBar.tsx` | component (form) | request-response (mutation) | RESEARCH.md Pattern 2 (`postTrade`) + `backend/app/routes/portfolio.py` (`TradeRequest`/`TradeResponse`/400 `detail`) | exact (research-provided + contract-match) |
| `frontend/components/positions/PositionsTable.tsx` | component | request-response + streaming | `backend/app/routes/portfolio.py` (`PortfolioResponse.positions`) + Pattern 1 (D-07 fallback) | role-match |
| `frontend/components/positions/PositionsRow.tsx` | component | streaming | RESEARCH.md Pattern 3 (`PriceCell` usage) | role-match |
| `frontend/next.config.ts` | config | — | RESEARCH.md "Recommended Project Structure" (`output: 'export'`, `images: { unoptimized: true }`) | exact (research-provided) |
| `backend/app/main.py` (modify: add dev-only CORS) | middleware/config | request-response | RESEARCH.md Pattern 2 (CORS snippet) + existing `create_app()` in `backend/app/main.py` | exact (research-provided, applies to tracked file) |

## Pattern Assignments

### `frontend/lib/types.ts` (model, transform)

**Analog:** `backend/app/routes/portfolio.py` (lines 24-66), `backend/app/routes/watchlist.py` (`WatchlistEntryResponse`), `backend/app/routes/stream.py` (lines 24-31)

Mirror these Pydantic models as TS types verbatim (field names/nullability), per RESEARCH.md "Code Examples" section (already extracted from source this session — copy directly rather than re-deriving):

```typescript
export type PositionView = {
  ticker: string
  quantity: number
  avg_cost: number
  current_price: number | null
  market_value: number
  unrealized_pnl: number
  pct_change: number
}

export type PortfolioResponse = {
  cash_balance: number
  positions: PositionView[]
  positions_value: number
  total_value: number
  total_unrealized_pnl: number
}

export type TradeRequest = { ticker: string; side: 'buy' | 'sell'; quantity: number }
export type TradeResponse = {
  trade: { id: string; ticker: string; side: string; quantity: number; price: number; executed_at: string }
  cash_balance: number
  position: { ticker: string; quantity: number; avg_cost: number } | null
}

export type WatchlistEntry = {
  ticker: string
  price: number | null
  previous_price: number | null
  direction: 'up' | 'down' | 'unchanged' | null
  timestamp: string | null
}

export type PriceTick = {
  ticker: string
  price: number
  previous_price: number
  timestamp: string
  direction: 'up' | 'down' | 'unchanged'
}
export type PricesEvent = { ticks: PriceTick[] }
```

**Why this is authoritative, not inferred:** `TradeRequest.quantity` must stay `> 0` (Pydantic `Field(gt=0)`, `backend/app/routes/portfolio.py:27`); `position` is nullable in `TradeResponse` because a full-close sell returns `None` (`backend/app/routes/portfolio.py:140-148`); `current_price` is nullable in `PositionViewResponse` and all watchlist/tick fields are nullable pre-stream — do not widen or narrow these without re-checking the source route file.

---

### `frontend/lib/api.ts` (service, request-response)

**Analog:** RESEARCH.md Pattern 2 (full code already written and verified against `backend/app/routes/portfolio.py`'s 400 `detail` shape)

**Core pattern:**
```typescript
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE}/api/portfolio`)
  if (!res.ok) throw new Error(`GET /api/portfolio failed: ${res.status}`)
  return res.json()
}

export async function postTrade(body: TradeRequest): Promise<TradeResponse> {
  const res = await fetch(`${BASE}/api/portfolio/trade`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const { detail } = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(detail)
  }
  return res.json()
}
```

**Error handling pattern:** the 400 response's `detail` string is generated by `HTTPException(status_code=400, detail=result.reason)` in `backend/app/routes/portfolio.py:126` — always surface `detail` verbatim in the trade bar's inline error (per D-03), never a generic message, so the exact backend validation reason (e.g. "insufficient cash") reaches the user.

Add `fetchWatchlist()` following the same `fetch` + `!res.ok` throw shape, targeting `GET /api/watchlist`.

---

### `frontend/lib/priceStore.tsx` (provider/store, streaming)

**Analog:** RESEARCH.md Pattern 1, full working example (lines 197-265 of 02-RESEARCH.md)

**Imports pattern:**
```tsx
'use client'
import { createContext, useContext, useEffect, useRef, useState } from 'react'
```

**Core streaming pattern:** single `EventSource` opened once in a `useEffect` with `[]` deps, named-event listener (`es.addEventListener('prices', ...)` — NOT `onmessage`, per backend/app/routes/stream.py:40's `event: prices` line), `Map<ticker, PriceTick>` state updated by merging each tick batch, cleanup via `es.close()` in the effect's return.

**Connection-status pattern:** `onopen` → `'connected'`; `onerror` → `'reconnecting'` with a grace-window `setTimeout` that flips to `'disconnected'` only if `es.readyState !== EventSource.OPEN` after ~5s (tune per D-06). Full excerpt is in RESEARCH.md lines 217-258 — copy verbatim, it's already been checked against MDN `EventSource.readyState` semantics.

**Error handling:** no explicit try/catch needed — `EventSource` has its own error channel (`onerror`), and `JSON.parse(event.data)` is trusted (same-origin backend, not user input).

---

### `frontend/components/ui/PriceCell.tsx` (component, streaming)

**Analog:** RESEARCH.md Pattern 3, full working example (lines 316-348)

**Core pattern:** track `lastPrice` in a `useRef`; on each `price` prop change, flash only if `price !== lastPrice.current` (mirrors backend's `price !== previous_price` semantics from the tick itself — do not compare against component-local "last render" as a substitute, per Anti-Pattern 4 in RESEARCH.md); apply `bg-green-500/30` or `bg-red-500/30` for ~500ms via `setTimeout`, using Tailwind's `transition-colors duration-500` for the fade.

```tsx
'use client'
import { useEffect, useRef, useState } from 'react'

export function PriceCell({ price, direction }: { price: number | null; direction: 'up'|'down'|'unchanged'|null }) {
  const [flashClass, setFlashClass] = useState('')
  const lastPrice = useRef<number | null>(null)
  useEffect(() => {
    if (price == null) return
    if (lastPrice.current !== null && price !== lastPrice.current) {
      setFlashClass(direction === 'up' ? 'bg-green-500/30' : 'bg-red-500/30')
      const t = setTimeout(() => setFlashClass(''), 500)
      lastPrice.current = price
      return () => clearTimeout(t)
    }
    lastPrice.current = price
  }, [price, direction])
  return <span className={`transition-colors duration-500 ${flashClass}`}>{price != null ? price.toFixed(2) : '—'}</span>
}
```

Used by both `WatchlistRow.tsx` and `PositionsRow.tsx` (D-07/D-09) — do not fork a second flash implementation.

---

### `frontend/components/header/Header.tsx` (component, streaming + request-response)

**Analog:** RESEARCH.md "Header live total value" code example (lines 456-471) + `backend/app/routes/portfolio.py` for `cash_balance`/`positions` shape

**Core pattern:** `cash_balance` renders straight from `GET /api/portfolio` unmodified; only the header's total value is recomputed client-side via `useLiveTotalValue`, scoped exactly to `Σ (position.quantity × latest SSE price ?? position.current_price ?? position.avg_cost) + cash_balance` — this is the one sanctioned client-side recompute in the whole phase (RESEARCH.md Anti-Patterns: "Re-deriving P&L math client-side"). Connection dot reads `status` from `usePriceStore()` (Pattern 1) via `ConnectionDot.tsx`.

```tsx
function useLiveTotalValue(positions: PositionView[], cashBalance: number) {
  const { prices } = usePriceStore()
  return useMemo(() => {
    const positionsValue = positions.reduce((sum, p) => {
      const tick = prices.get(p.ticker)
      const price = tick?.price ?? p.current_price ?? p.avg_cost
      return sum + p.quantity * price
    }, 0)
    return cashBalance + positionsValue
  }, [positions, cashBalance, prices])
}
```

---

### `frontend/components/trade-bar/TradeBar.tsx` (component/form, request-response mutation)

**Analog:** RESEARCH.md Pattern 2 (`postTrade`) + `backend/app/routes/portfolio.py` (`TradeRequest`, lines 24-27; 400 `detail` at line 126)

**Core pattern:**
- Ticker input: plain text, `.toUpperCase()` applied before submit (D-01, Pitfall 4) — not a dropdown.
- Quantity input: `type="number" step="any"` (D-02, matches backend's `REAL`/`float` fractional-share support).
- Submit (buy/sell buttons): call `postTrade({ ticker: ticker.toUpperCase(), side, quantity })`.
- On success: clear/reset the quantity field, then trigger a `GET /api/portfolio` refetch (D-04) — do not locally construct a position update from the trade response.
- On error: `postTrade` throws `Error(detail)` (per `lib/api.ts` above) — catch and render `error.message` inline near the trade bar, not a global toast (D-03).
- No client-side pre-validation of sufficient cash/shares — that's the backend's sole authority (RESEARCH.md "Don't Hand-Roll").

**Error handling pattern:**
```tsx
try {
  await postTrade({ ticker: ticker.toUpperCase(), side, quantity: Number(quantity) })
  setQuantity('')
  setError(null)
  await refetchPortfolio()
} catch (e) {
  setError(e instanceof Error ? e.message : 'Trade failed')
}
```

---

### `frontend/components/watchlist/WatchlistPanel.tsx` / `WatchlistRow.tsx` (component, request-response + streaming)

**Analog:** `backend/app/routes/watchlist.py` (`WatchlistEntryResponse` shape) for initial hydration via `fetchWatchlist()`, then `usePriceStore()` (Pattern 1) for live updates per ticker; each row renders ticker + `PriceCell` (price + direction) + daily change %.

**Core pattern:** on mount, `fetchWatchlist()` seeds the initial list/prices (handles the pre-stream null case); thereafter each row reads its own ticker's `PriceTick` from the shared `prices` Map in context — no per-row `EventSource`, no polling (D-05 Anti-Pattern: "Opening a second EventSource per component").

---

### `frontend/components/positions/PositionsTable.tsx` / `PositionsRow.tsx` (component, request-response + streaming)

**Analog:** `backend/app/routes/portfolio.py` (`PositionViewResponse`, lines 51-58) for columns (ticker, quantity, avg_cost, current_price, unrealized_pnl, pct_change); D-07's fallback chain for `current_price`.

**Core pattern:** `current_price` resolves as `prices.get(ticker)?.price ?? position.current_price` (SSE store first, `/api/portfolio` value as fallback for tickers not yet streamed) — same fallback chain as the header's `useLiveTotalValue`, do not diverge. `unrealized_pnl`/`pct_change`/`avg_cost` always come straight from `GET /api/portfolio` — never recomputed (RESEARCH.md "Don't Hand-Roll": portfolio math).

---

### `frontend/app/globals.css` (config, theme tokens)

**Analog:** RESEARCH.md Pitfall 5 code guidance (Tailwind v4 `@theme` block, not `tailwind.config.js`)

**Core pattern:**
```css
@import "tailwindcss";
@theme {
  --color-terminal-bg: #0d1117;
  --color-terminal-bg-alt: #1a1a2e;
  --color-accent-yellow: #ecad0a;
  --color-accent-blue: #209dd7;
  --color-accent-purple: #753991;
}
```
PLAN.md §2 palette values are locked; secondary shades (hover/disabled/flash green-red) are Claude's discretion per RESEARCH.md Open Question 1 — default to Tailwind's stock `green-500`/`red-500` at 30% opacity, consistent with Pattern 3's example.

---

### `frontend/next.config.ts` (config)

**Analog:** RESEARCH.md "Recommended Project Structure" + Pitfall 1/2

**Core pattern:**
```ts
import type { NextConfig } from 'next'
const nextConfig: NextConfig = {
  output: 'export',
  images: { unoptimized: true },
}
export default nextConfig
```
Do NOT add `rewrites`/`redirects`/`headers` — errors under `output: 'export'` even in `next dev` (Pitfall 1). Use `lib/api.ts`'s env-var base URL instead.

---

### `backend/app/main.py` (modify — add dev-only CORS middleware)

**Analog:** RESEARCH.md Pattern 2 CORS snippet; existing file is tracked (`git ls-files` confirmed) — read `create_app()` before editing to place the middleware correctly (before `app.include_router(...)` calls) and preserve existing conventions (module docstring style, `from __future__ import annotations` if present).

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Scope `allow_origins` explicitly to the dev frontend origin — never `["*"]` (Security Domain note in RESEARCH.md). Flag for Phase 5 to reconsider whether this middleware ships in the Docker image at all once frontend/backend are same-origin.

---

## Shared Patterns

### Single shared SSE connection (D-05)
**Source:** `frontend/lib/priceStore.tsx` (RESEARCH.md Pattern 1)
**Apply to:** `Header.tsx`, `WatchlistRow.tsx`, `PositionsRow.tsx`/`PositionsTable.tsx` — every price-dependent component reads `usePriceStore()`; none construct their own `EventSource`.

### Env-var API base URL (D-10 static-export constraint)
**Source:** `frontend/lib/api.ts` (RESEARCH.md Pattern 2)
**Apply to:** every `fetch`/`EventSource` call in the app — never hardcode `/api/...` directly in a component; always go through `lib/api.ts` or `lib/priceStore.tsx`'s `BASE` constant.

### Backend as single source of truth for money math (D-04)
**Source:** `backend/app/portfolio/service.py` (`compute_portfolio_view`, `execute_trade` — not read this session but referenced verbatim in RESEARCH.md's verified excerpts)
**Apply to:** `TradeBar.tsx` (refetch after trade, never optimistic-construct a position), `PositionsTable.tsx` (`unrealized_pnl`/`pct_change`/`avg_cost` always server-sourced), `Header.tsx` (only total_value is client-recomputed, scoped exactly as shown above).

### Flash-only-on-real-change (D-09, PLAN.md §6)
**Source:** `frontend/components/ui/PriceCell.tsx` (RESEARCH.md Pattern 3)
**Apply to:** `WatchlistRow.tsx`, `PositionsRow.tsx` — compare `price !== previous_price` from the tick itself (or component-tracked `lastPrice` for values falling back to `/api/portfolio`), never trigger on an unchanged heartbeat resend.

### Provider wiring (root layout)
**Source:** no existing analog — greenfield; wire per RESEARCH.md's structure: `app/layout.tsx` wraps `{children}` in `PriceStoreProvider` (from `lib/priceStore.tsx`) so it's mounted once at the root and available to every route (only one route exists this phase, `app/page.tsx`, but this keeps Phase 3/4 additions from needing to rework the provider tree).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/app/layout.tsx` | provider | request-response | No existing frontend code; also no prior "root provider wiring" pattern in this backend-only repo. Use RESEARCH.md's structure recommendation directly (see Shared Patterns above). |
| `frontend/app/page.tsx` | component (composition) | request-response | Greenfield page composition (header + watchlist/trade-bar column + positions column per D-08); no in-repo analog, follow RESEARCH.md's System Architecture Diagram layout. |
| `frontend/package.json`, `tsconfig.json`, `postcss.config.mjs` | config | — | Standard `create-next-app@16.3.5 --typescript --tailwind --app` scaffold output per RESEARCH.md Installation section — not hand-written, no analog needed. |

## Metadata

**Analog search scope:** `backend/app/routes/`, `backend/app/main.py`, `backend/app/portfolio/`, `backend/app/market/` (contract sources only — `frontend/` confirmed empty via `git ls-files -- frontend`)
**Files scanned:** 3 backend route modules read directly this session (`portfolio.py`, `stream.py`); `watchlist.py`/`main.py`/`service.py` referenced via RESEARCH.md's verbatim-quoted excerpts (already read and verified in the research session, re-reading avoided per no-duplicate-range rule)
**Pattern extraction date:** 2026-09-17
