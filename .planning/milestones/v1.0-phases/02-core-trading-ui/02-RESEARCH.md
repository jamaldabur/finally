# Phase 2: Core Trading UI - Research

**Researched:** 2026-09-17
**Domain:** Next.js 16 (App Router, static export) trading UI consuming a FastAPI SSE + REST backend
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Trade bar UX**
- **D-01:** Ticker field is a plain text input (uppercase-normalized client-side before submit), not a dropdown restricted to the watchlist — the backend's `execute_trade()` accepts any ticker `is_valid_ticker()` recognizes, not just watched ones, and PLAN.md §10 describes it as "a simple input area: ticker field, quantity field." — Reversibility: reversible — swapping to a dropdown later is a local component change with no API impact.
- **D-02:** Quantity field accepts decimals (`type="number" step="any"`, or a text input with numeric validation), since `positions.quantity` is `REAL` and the backend explicitly supports fractional shares (PLAN.md §7).
- **D-03:** No confirmation dialog on submit (per PLAN.md §2/§9 — zero-friction, instant fill). On response: success clears/resets the quantity field and the positions table + header refresh (see D-04); on error (400 with `detail` from `TradeRequest`/`execute_trade` validation, e.g. insufficient cash/shares), show the message inline near the trade bar, not a global toast — keeps it visible next to the action that caused it, no new UI dependency needed.

**Live data & refresh flow**
- **D-04:** After a trade executes, the frontend refetches `GET /api/portfolio` immediately (rather than optimistic local updates) — `compute_portfolio_view()` is the single source of truth for cash/positions/P&L math (rounding, avg cost, etc.), so re-deriving it client-side would duplicate backend logic and risk drifting from it. — Reversibility: reversible — optimistic updates can be layered on top later without changing the API contract.
- **D-05:** A single shared SSE connection (one `EventSource` for `/api/stream/prices`, opened once — e.g. via a React context/provider or a top-level hook) feeds all price-dependent UI: watchlist rows, and the header's live total value (recomputed client-side from cached position quantities/avg cost + latest SSE prices, so it updates every tick without polling `/api/portfolio` on each tick).
- **D-06:** Connection status dot: green while the `EventSource` is open and receiving events, yellow after an `onerror` fires (browser is auto-retrying — native `EventSource` reconnect behavior per PLAN.md §6), red if no reconnection succeeds after a short grace window. Exact thresholds are left to the executor/planner to tune.
- **D-07:** Positions table rows resolve `current_price` from the same shared SSE price store the watchlist uses (falling back to `GET /api/portfolio`'s `current_price` field when the ticker's price hasn't streamed yet, e.g. right after page load) rather than issuing separate polling requests.

**Layout & panel arrangement**
- **D-08:** Single page, header pinned at top (portfolio total value, cash balance, connection dot — full width). Below the header: a left column with the watchlist panel stacked above the trade bar, and a right/main column with the positions table. This leaves an obvious main-content slot for the Phase 4 chart/heatmap and an obvious side slot for the Phase 3 chat panel, so those phases extend the layout instead of reworking it.
- **D-09:** Dark theme per PLAN.md §2: background ~`#0d1117`/`#1a1a2e`, accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991` for submit/buy-type actions. Price flash: brief green/red background on the changed price cell, fading via CSS transition over ~500ms, triggered only when `price !== previous_price` from a given SSE tick (never on an unchanged heartbeat resend — PLAN.md §6).

**Frontend scaffolding**
- **D-10:** Next.js App Router with `output: 'export'` (static export), TypeScript, Tailwind CSS — all explicitly named in PLAN.md §3/§10/§11.
- **D-11:** Frontend naming/style is idiomatic TypeScript/React (camelCase functions/variables, PascalCase components), not a mirror of the backend's Python snake_case — PLAN.md §4 treats `frontend/` and `backend/` as independent, loosely-coupled projects ("frontend knows nothing about Python").
- **D-12:** Components organized by feature (`components/watchlist/`, `components/trade-bar/`, `components/positions/`, `components/header/`), with shared primitives (buttons, status dot, etc.) under `components/ui/`. Exact file layout beyond this grouping is left to the planner/researcher.

### Claude's Discretion
Per the user's "you choose everything" response, essentially all of Phase 2's implementation gray areas (trade bar UX, live-data refresh strategy, layout arrangement, and frontend scaffolding conventions) were left to Claude's judgment rather than individually discussed. The decisions above (D-01 through D-12) are the record of those calls; anything not explicitly pinned down there (e.g. exact Tailwind config structure, precise flash-animation timing curve, specific component prop shapes) remains open for the researcher/planner to decide — this document's Architecture Patterns, Code Examples, and Open Questions sections make those remaining calls.

### Deferred Ideas (OUT OF SCOPE)
None — no scope-creep suggestions came up during the Phase 2 discussion; the user deferred implementation choices rather than proposing new capabilities. Out-of-scope-for-this-phase items (from the Phase Boundary, not "Deferred Ideas" per se): sparklines and the detailed per-ticker chart, the portfolio heatmap, the P&L history chart (all Phase 4); the AI chat panel (Phase 3); Docker packaging (Phase 5); automated test suites (Phase 6).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|--------------------|
| UI-01 | Watchlist panel shows live-updating prices via SSE, flashing green/red on price change | Pattern 1 (shared `EventSource`/`PriceStore` context) + Pattern 3 (`PriceCell` flash-on-real-change component) + verified `event: prices` payload shape from `backend/app/routes/stream.py` |
| UI-06 | Positions table shows ticker, quantity, avg cost, current price, unrealized P&L, % change | Verified `PositionViewResponse`/`PortfolioResponse` shape from `backend/app/routes/portfolio.py:51-66`, quoted verbatim in Code Examples; D-07's fallback-to-`/api/portfolio` pattern documented in Architectural Responsibility Map and Pattern 1 |
| UI-07 | Trade bar lets the user submit buy/sell market orders (ticker, quantity, buy button, sell button) | Verified `TradeRequest`/`TradeResponse` shape and 400 `detail` error strings from `backend/app/routes/portfolio.py` and `backend/app/portfolio/service.py`; Pitfall 4 (ticker casing) and D-04's refetch-after-trade flow addressed in Pattern 2 |
| UI-09 | Header shows live portfolio total value, a connection status indicator (green/yellow/red dot), and cash balance | Pattern 1's `status` context value + `useLiveTotalValue` Code Example; D-06's grace-window logic implemented in Pattern 1 with `EventSource.readyState` semantics cited from MDN |
| UI-10 | UI follows the dark trading-terminal visual design (color scheme, price flash animation) specified in PLAN.md §2 | Pitfall 5 (Tailwind v4 `@theme`-based palette setup) + Pattern 3 (500ms flash fade) directly implement PLAN.md §2's color scheme and animation requirements |
</phase_requirements>

## Summary

Phase 2 builds the entire `frontend/` Next.js project from scratch (greenfield — nothing exists yet) and wires it to a fully-implemented, fully-tested backend (Phase 1: 73+ passing tests). The backend contracts (`GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/watchlist`, `GET /api/stream/prices`) are locked and were read directly from source this session — every field name, type, and error string quoted below is verbatim from the route/service modules, not inferred.

The one non-obvious architectural problem this phase must solve, which CONTEXT.md's decisions don't address: **the project is locked into `output: 'export'` (D-10) from day one, and Next.js explicitly errors on `rewrites`/`redirects`/`headers` in that mode — including during `next dev`, not just at build time** (verified via Context7 against Next.js's static-export docs and validation source). That forecloses the usual "Next.js dev-server proxy" trick for talking to the FastAPI backend on a different port during local development. The standard, unblocked fix — confirmed against both official docs and general practice — is an env-var-switched API base URL (`NEXT_PUBLIC_API_BASE_URL`, empty/relative in the production static export, `http://localhost:8000` in dev) paired with a FastAPI `CORSMiddleware` for local dev only. This does not conflict with PLAN.md's "same-origin, no CORS" production architecture — CORS headers are inert once frontend and backend are actually same-origin behind Docker (Phase 5).

**Primary recommendation:** Scaffold `frontend/` as a Next.js 16 App Router + TypeScript + Tailwind CSS v4 project with `output: 'export'` set from the start; centralize all API access behind a small `lib/api.ts` (fetch wrapper using `NEXT_PUBLIC_API_BASE_URL`) and a single shared `EventSource` context/hook (per D-05) so every price-dependent component (watchlist rows, header total, positions table) reads from one in-memory price store rather than opening its own connection or polling.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Live price streaming (watchlist flash, header total, positions current_price) | Browser / Client | API / Backend (SSE source) | Backend pushes via SSE; browser owns the shared `EventSource` connection, price cache, and flash-trigger comparison (`price !== previous_price`) — D-05, D-07 |
| Trade execution (buy/sell) | API / Backend | Browser / Client (form UX only) | `execute_trade()` is the single validation/mutation path (cash, shares, avg-cost math); frontend only collects input and displays the 400 `detail` — D-04 |
| Portfolio state (cash, positions, P&L) | API / Backend | Browser / Client (render only) | `compute_portfolio_view()` is the sole source of truth for derived math (rounding, pct_change); frontend never re-derives it — D-04 |
| Connection status (dot) | Browser / Client | — | Purely a client-side reading of `EventSource.readyState` / `onerror`/`onopen` — no backend signal exists or is needed — D-06 |
| Watchlist membership | API / Backend | Browser / Client (display) | Ticker validity (`is_valid_ticker`) is backend-owned; out of scope for Phase 2 UI (no add/remove UI yet — CONTEXT.md boundary) |
| Dark theme / visual design | Browser / Client | — | Tailwind CSS utility classes + CSS custom properties; no backend involvement — D-09 |
| Static asset serving | CDN / Static (via FastAPI in prod) | Browser / Client (dev via `next dev`) | Production: FastAPI serves the exported `out/` directory (Phase 5, not this phase); dev: Next.js's own dev server |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `next` | 16.3.5 [VERIFIED: npm registry] | React framework, App Router, static export build | Explicitly named in PLAN.md §3/§10/§11 and CONTEXT.md D-10 |
| `react` | 19.3.0 [VERIFIED: npm registry] | UI library | Next.js 16's required peer |
| `react-dom` | 19.3.0 [VERIFIED: npm registry] | DOM renderer | Pairs with `react` |
| `typescript` | 7.0.2 [VERIFIED: npm registry] | Type checking | Explicitly named in PLAN.md §3/§10; D-10 |
| `tailwindcss` | 4.3.3 [VERIFIED: npm registry] | Utility-first styling, dark theme | Explicitly named in PLAN.md §10; D-10 |
| `@tailwindcss/postcss` | 4.3.3 [VERIFIED: npm registry] | Tailwind v4's PostCSS plugin (replaces the old `tailwindcss` PostCSS entry + `autoprefixer`) | Required install step for Tailwind v4 — [CITED: tailwindcss.com/docs/installation/framework-guides/nextjs] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `eslint-config-next` | 16.3.5 [VERIFIED: npm registry] | Next.js's official ESLint ruleset | Standard `create-next-app` scaffolding output; keeps App Router conventions enforced |
| `@types/react` | 19.3.0 [VERIFIED: npm registry] | TypeScript types for React | Dev dependency, standard with `react`+TS |
| `@types/node` | 22.20.3 [VERIFIED: npm registry] | TypeScript types for Node APIs used in config files | Dev dependency, standard with any TS Next.js project |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tailwind CSS v4 (`@tailwindcss/postcss`, CSS-based `@theme` config) | Tailwind CSS v3 (`tailwind.config.js`, `autoprefixer`) | v3 is more familiar/documented in older tutorials, but v4 is current, has zero-config content detection, and is what `npm view` resolves to as `latest` — no reason to pin v3 for a greenfield project |
| Custom `EventSource` hook/context (D-05) | A library like `@microsoft/fetch-event-source` or `eventsource-polyfill` | Native `EventSource` is sufficient — PLAN.md §10 explicitly calls for the native API, no auth headers or POST-body SSE needed, and D-06's connection dot logic maps directly onto `readyState`/`onerror`/`onopen` |
| Env-var API base URL + dev-only CORS (this research's recommendation) | Running `next build && next start` in a "hybrid" (non-export) mode during dev to keep rewrites working | Contradicts D-10's locked `output: 'export'` decision, and Next.js's own static-export docs state rewrites/redirects/headers "will result in errors during development" once `output: 'export'` is set — not just at build time [CITED: github.com/vercel/next.js static-exports.mdx] |

**Installation:**
```bash
cd frontend
npx create-next-app@16.3.5 . --typescript --tailwind --app --eslint --src-dir=false --import-alias "@/*"
npm install @tailwindcss/postcss@4.3.3
```
(`create-next-app`'s `--tailwind` flag already wires Tailwind v4 correctly for Next.js 16 — the explicit install above is a fallback if the scaffold needs adjusting post-hoc.)

**Version verification:** All versions above were confirmed via `npm view <pkg> version` against the live npm registry this session (2026-09-17). `next`, `react`, `react-dom`, `eslint-config-next`, `@types/react`, and `@types/node` publish very frequently (all had a `publishedAt` within the last week per the legitimacy check below) — recency is expected, not a red flag, for these specific high-volume official packages.

## Package Legitimacy Audit

| Package | Registry | Weekly Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-------------------|-------------|---------|-------------|
| `next` | npm | 43.4M | github.com/vercel/next.js | SUS ("too-new" — published 2026-09-11) | Approved — false-positive: official Vercel package, high-frequency release cadence |
| `react` | npm | 128.1M | github.com/react/react | SUS ("too-new" — published 2026-09-09) | Approved — false-positive: official React monorepo, high-frequency release cadence |
| `react-dom` | npm | 120.7M | github.com/react/react | SUS ("too-new" — published 2026-09-09) | Approved — same as `react` |
| `typescript` | npm | 203.4M | github.com/microsoft/TypeScript | OK | Approved |
| `tailwindcss` | npm | 92.7M | github.com/tailwindlabs/tailwindcss | OK | Approved |
| `@tailwindcss/postcss` | npm | 27.9M | github.com/tailwindlabs/tailwindcss | OK | Approved |
| `eslint-config-next` | npm | 24.6M | github.com/vercel/next.js | SUS ("too-new" — published 2026-09-11) | Approved — ships in lockstep with `next` |
| `@types/react` | npm | 117.8M | github.com/DefinitelyTyped/DefinitelyTyped | SUS ("too-new" — published 2026-09-09) | Approved — DefinitelyTyped publishes on every upstream release |
| `@types/node` | npm | 316.5M | github.com/DefinitelyTyped/DefinitelyTyped | SUS ("too-new" — published 2026-09-15) | Approved — DefinitelyTyped publishes on every upstream release |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `next`, `react`, `react-dom`, `eslint-config-next`, `@types/react`, `@types/node` — all flagged solely on the legitimacy checker's "too-new" heuristic (recent `publishedAt`). Every one is an extremely well-known, extremely high-download package with an official/DefinitelyTyped source repo confirmed via `npm view`; the "too-new" signal is a known false-positive pattern for packages with weekly or near-weekly release cadences. The planner may still insert a lightweight `checkpoint:human-verify` before `npm install` per the protocol's default, but there is no substantive legitimacy concern here.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────── Browser ───────────────────────────────┐
│                                                                         │
│  Page load                                                             │
│    │                                                                   │
│    ├─► fetch GET /api/portfolio ──────► PortfolioContext (cash, positions)
│    ├─► fetch GET /api/watchlist ──────► WatchlistContext (tickers, seed prices)
│    └─► new EventSource('/api/stream/prices')                          │
│              │  addEventListener('prices', handler)                    │
│              │  onerror / onopen  ──────► ConnectionStatus (dot color) │
│              ▼                                                         │
│        PriceStore (shared context/hook)                                │
│         - per-ticker {price, previous_price, direction, ts}            │
│         - flash trigger: price !== previous_price from the tick        │
│              │                                                         │
│    ┌─────────┼───────────────────────────────┐                        │
│    ▼         ▼                                ▼                       │
│  Watchlist  Header (live total value =    Positions Table              │
│  rows       Σ qty·price + cash, computed   (current_price from         │
│  (flash)    client-side from Portfolio     PriceStore, falls back      │
│             positions + PriceStore)        to /api/portfolio value)    │
│                                                                         │
│  Trade Bar ──► POST /api/portfolio/trade ──► on success: refetch       │
│  (ticker, qty,     400 → inline error         GET /api/portfolio       │
│   buy/sell)        near trade bar             (D-04, single source     │
│                                                 of truth for math)      │
└─────────────────────────────────────────────────────────────────────────┘
                              │  (dev: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
                              │   prod: relative /api/* — same origin, no env var)
                              ▼
┌──────────────────────────── FastAPI (backend, Phase 1, already built) ─┐
│  GET  /api/portfolio        → compute_portfolio_view()                 │
│  POST /api/portfolio/trade  → execute_trade() (400 + detail on error)  │
│  GET  /api/watchlist        → get_watchlist_entries() + price_cache    │
│  GET  /api/stream/prices    → SSE, event: prices, every 0.5s            │
└──────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
frontend/
├── app/
│   ├── layout.tsx           # Root layout: fonts, global providers (PriceStore, Portfolio)
│   ├── page.tsx             # Single page: header + left column (watchlist+trade bar) + right column (positions)
│   └── globals.css          # @import "tailwindcss"; @theme { --color-* } (dark palette)
├── components/
│   ├── header/
│   │   └── Header.tsx       # Total value, cash balance, connection dot
│   ├── watchlist/
│   │   ├── WatchlistPanel.tsx
│   │   └── WatchlistRow.tsx # Flash-on-change price cell
│   ├── trade-bar/
│   │   └── TradeBar.tsx     # Ticker/qty inputs, buy/sell buttons, inline error
│   ├── positions/
│   │   ├── PositionsTable.tsx
│   │   └── PositionsRow.tsx
│   └── ui/
│       ├── ConnectionDot.tsx
│       └── PriceCell.tsx    # Shared flash-animation cell (used by watchlist + positions)
├── lib/
│   ├── api.ts                # fetchPortfolio(), postTrade(), fetchWatchlist() — wraps NEXT_PUBLIC_API_BASE_URL
│   ├── types.ts               # TS mirrors of backend response shapes (PortfolioResponse, TradeResponse, etc.)
│   └── priceStore.tsx          # Context + hook wrapping the shared EventSource (D-05)
├── next.config.ts             # output: 'export', images: { unoptimized: true }
├── postcss.config.mjs         # @tailwindcss/postcss plugin
├── package.json
└── tsconfig.json
```

### Pattern 1: Single shared `EventSource` via React Context
**What:** One `EventSource` instance created once (e.g. in a `PriceStoreProvider` mounted in `app/layout.tsx`), exposing a `Map<ticker, PriceTick>` plus a `connectionStatus: 'connected' | 'reconnecting' | 'disconnected'` value via context.
**When to use:** Any component needing live prices (watchlist rows, positions table, header total) — never open a second `EventSource`.
**Example:**
```tsx
// lib/priceStore.tsx — pattern informed by Next.js's official static-export
// client-fetching guidance (below) and native EventSource semantics
// [CITED: github.com/vercel/next.js static-exports.mdx; MDN EventSource docs]
'use client'
import { createContext, useContext, useEffect, useRef, useState } from 'react'

type Direction = 'up' | 'down' | 'unchanged'
type PriceTick = { ticker: string; price: number; previous_price: number; timestamp: string; direction: Direction }
type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected'

const PriceStoreContext = createContext<{
  prices: Map<string, PriceTick>
  status: ConnectionStatus
} | null>(null)

export function PriceStoreProvider({ children }: { children: React.ReactNode }) {
  const [prices, setPrices] = useState<Map<string, PriceTick>>(new Map())
  const [status, setStatus] = useState<ConnectionStatus>('reconnecting')
  const graceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''
    const es = new EventSource(`${base}/api/stream/prices`)

    es.addEventListener('prices', (event) => {
      // Named event, NOT the default 'message' event — backend emits
      // "event: prices\ndata: ...\n\n" (verified: backend/app/routes/stream.py:40)
      const payload = JSON.parse(event.data) as { ticks: PriceTick[] }
      setPrices((prev) => {
        const next = new Map(prev)
        for (const tick of payload.ticks) next.set(tick.ticker, tick)
        return next
      })
      setStatus('connected')
      if (graceTimer.current) clearTimeout(graceTimer.current)
    })

    es.onopen = () => setStatus('connected')
    es.onerror = () => {
      // readyState: CONNECTING=0 (browser is auto-retrying), CLOSED=2 (gave up)
      // [CITED: MDN EventSource/readyState]
      setStatus('reconnecting')
      if (graceTimer.current) clearTimeout(graceTimer.current)
      graceTimer.current = setTimeout(() => {
        if (es.readyState !== EventSource.OPEN) setStatus('disconnected')
      }, 5000) // grace window before showing red — tune per D-06
    }

    return () => es.close()
  }, [])

  return (
    <PriceStoreContext.Provider value={{ prices, status }}>
      {children}
    </PriceStoreContext.Provider>
  )
}

export function usePriceStore() {
  const ctx = useContext(PriceStoreContext)
  if (!ctx) throw new Error('usePriceStore must be used within PriceStoreProvider')
  return ctx
}
```

### Pattern 2: Env-var API base URL (dev/prod split under `output: 'export'`)
**What:** A single `lib/api.ts` module resolves every backend call against `process.env.NEXT_PUBLIC_API_BASE_URL`, which is empty in production (relative `/api/...`, same-origin per PLAN.md §3) and `http://localhost:8000` in local dev.
**When to use:** Every `fetch()`/`EventSource` call in the app — never hardcode a relative path directly in a component.
**Example:**
```ts
// lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE}/api/portfolio`)
  if (!res.ok) throw new Error(`GET /api/portfolio failed: ${res.status}`)
  return res.json()
}

export async function postTrade(body: {
  ticker: string
  side: 'buy' | 'sell'
  quantity: number
}): Promise<TradeResponse> {
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
```env
# frontend/.env.development.local (git-ignored — dev-only override)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
Companion backend change (dev convenience only — harmless once same-origin in Docker):
```python
# backend/app/main.py — add inside create_app(), before app.include_router(...) calls
# [CITED: fastapi.tiangolo.com/tutorial/cors]
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Pattern 3: Flash-on-change price cell, triggered only on real change
**What:** A `PriceCell` component that applies a brief green/red background class only when `tick.price !== tick.previous_price` for the tick just received — never on an unchanged heartbeat resend.
**When to use:** Watchlist rows, positions table `current_price` column.
**Example:**
```tsx
// components/ui/PriceCell.tsx
'use client'
import { useEffect, useRef, useState } from 'react'

export function PriceCell({ ticker, price, direction }: {
  ticker: string; price: number | null; direction: 'up' | 'down' | 'unchanged' | null
}) {
  const [flashClass, setFlashClass] = useState('')
  const lastPrice = useRef<number | null>(null)

  useEffect(() => {
    if (price == null) return
    if (lastPrice.current !== null && price !== lastPrice.current) {
      setFlashClass(direction === 'up' ? 'bg-green-500/30' : 'bg-red-500/30')
      const t = setTimeout(() => setFlashClass(''), 500) // ~500ms fade per D-09/PLAN.md §2
      lastPrice.current = price
      return () => clearTimeout(t)
    }
    lastPrice.current = price
  }, [price, direction])

  return (
    <span className={`transition-colors duration-500 ${flashClass}`}>
      {price != null ? price.toFixed(2) : '—'}
    </span>
  )
}
```

### Anti-Patterns to Avoid
- **Opening a second `EventSource` per component:** Violates D-05; each watchlist row or positions row must read from the shared `PriceStore`, not construct its own `new EventSource(...)`. Multiple connections also multiply backend SSE load for zero benefit (all tickers stream in one event already).
- **Re-deriving P&L math client-side:** `compute_portfolio_view()` rounds monetary values to cent precision deliberately to avoid float-imprecision leaking into the API (verified: `backend/app/portfolio/service.py:85-99`, e.g. the `pct_change` rounding comment). Recompute nothing except the header's live total value, which D-05 explicitly scopes to `Σ (position.quantity × latest SSE price) + cash_balance` — everything else comes from `GET /api/portfolio`.
- **Listening for the default `message` event:** The backend's SSE stream uses a **named** `event: prices` line (verified: `backend/app/routes/stream.py:40`, `yield f"event: prices\ndata: {json.dumps(payload)}\n\n"`). `es.onmessage = ...` will never fire; must use `es.addEventListener('prices', ...)`.
- **Treating `previous_price` as "the value from the prior SSE event":** It is the last known *different* price (heartbeats resend it unchanged). Comparing `tick.price !== tick.previous_price` from a single incoming tick is correct; comparing against a locally-tracked "last event" value duplicates backend logic and can double-trigger or miss flashes across a page-load boundary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| SSE reconnection | Custom retry/backoff loop around `fetch` + manual polling | Native `EventSource` | Browser-native automatic reconnection with a `retry:`-configurable delay is already spec'd behavior (verified: WHATWG HTML spec, MDN) — PLAN.md §6 explicitly calls for it ("Client handles reconnection automatically") |
| Portfolio P&L / avg-cost math | Client-side recomputation of `unrealized_pnl`, `pct_change`, average cost after a sell | `GET /api/portfolio` (`compute_portfolio_view()`) | Backend already handles float-precision rounding, mark-to-cost fallback for delisted-from-watchlist positions, and average-cost-preserved-on-sell — re-implementing any of this client-side risks drift (D-04) |
| Trade validation (sufficient cash/shares) | Client-side pre-check before submit | `POST /api/portfolio/trade`'s 400 response | The backend's `_apply_buy`/`_apply_sell` are the single source of truth (epsilon-tolerant float comparison, `QUANTITY_EPSILON = 1e-9`); a client-side pre-check would either duplicate or drift from that logic |
| Tailwind dark-theme tokens | Custom CSS variable system for colors | Tailwind v4 `@theme` block in `globals.css` | v4's CSS-first theming (`@theme { --color-terminal-bg: #0d1117; ... }`) generates matching utilities (`bg-terminal-bg`) automatically — no separate token/CSS-var wiring needed [CITED: tailwindcss.com/docs/theme] |

**Key insight:** Every hand-roll risk in this phase traces back to duplicating logic the backend already owns (trade validation, P&L math) or reinventing a browser-native primitive (`EventSource` reconnection) that PLAN.md deliberately chose *because* it's built-in.

## Common Pitfalls

### Pitfall 1: `rewrites`/`redirects`/`headers` silently don't work under `output: 'export'` — including in `next dev`
**What goes wrong:** A developer adds a `rewrites()` entry in `next.config.ts` to proxy `/api/*` to `http://localhost:8000` during local dev, expecting it to work like a normal Next.js project, then hits errors or silent no-ops.
**Why it happens:** `output: 'export'` disables Node-server-only features project-wide, not just at the final `next build` static-export step. Next.js's own docs state: "Attempting to use these features will result in errors during development" [CITED: github.com/vercel/next.js docs/01-app/02-guides/static-exports.mdx "Unsupported Features"].
**How to avoid:** Use the env-var API base URL + dev-only CORS pattern (Pattern 2 above) instead of rewrites.
**Warning signs:** A `next dev` console warning referencing `export-no-custom-routes`, or `/api/*` requests from the browser resolving to `localhost:3000` (404/HTML response) instead of the FastAPI backend on `:8000`.

### Pitfall 2: `next/image` optimization breaks under static export
**What goes wrong:** Using the default `next/image` component (which relies on a server-side optimization API) fails or warns under `output: 'export'`.
**Why it happens:** No Node server exists at runtime for a static export to call into.
**How to avoid:** Set `images: { unoptimized: true }` in `next.config.ts`, or avoid `next/image` for this phase (no images/logos are required by Phase 2's scope — plain text/icons only).
**Warning signs:** Build-time errors mentioning `Image Optimization using the default loader is not compatible with `{ output: 'export' }`.`

### Pitfall 3: Trade bar success handler racing the SSE price used for the fill
**What goes wrong:** After `POST /api/portfolio/trade` succeeds, the frontend must refetch `GET /api/portfolio` (D-04) — but if the UI also tries to optimistically update from the *client's last-seen SSE price* rather than the trade response's actual fill price, the displayed avg_cost/position can transiently disagree with the backend (the fill price is whatever `PriceCache` held at execution time, which may differ slightly from the last SSE tick the browser rendered, since SSE broadcasts every 0.5s and a trade can land mid-interval).
**Why it happens:** Two different "current price" sources (`PriceCache` server-side vs. the browser's last-rendered tick) can be up to ~500ms apart.
**How to avoid:** Per D-04, trust `POST /api/portfolio/trade`'s response for the trade confirmation itself, and immediately follow with a `GET /api/portfolio` refetch for the canonical positions/cash state — never construct a position update from the trade bar's local state.
**Warning signs:** Positions table briefly showing a different avg_cost/quantity than what appears after the next SSE tick or manual refresh.

### Pitfall 4: Ticker casing round-trip through a 400
**What goes wrong:** Submitting a lowercase ticker (`aapl`) from the trade bar or watchlist input reaches the backend, which does its own `.strip().upper()` normalization inside `execute_trade()` (verified: `backend/app/portfolio/service.py:149`) — so this specific pitfall is actually *already handled* server-side for trades. However, D-01 still calls for client-side uppercase normalization before submit, for UX consistency (avoids a round-trip flicker) and because other endpoints (e.g. future watchlist POST) are stricter.
**Why it happens:** `is_valid_ticker()` performs a case-sensitive membership check against an uppercase-keyed table in some backend contexts (verified pattern noted in `backend/app/routes/watchlist.py:9-10` docstring).
**How to avoid:** Uppercase the ticker field client-side (`.toUpperCase()`) before every submit, matching D-01's decision.
**Warning signs:** A ticker that should be valid getting rejected only when typed in lowercase.

### Pitfall 5: Tailwind v4 config mistaken for v3's `tailwind.config.js` pattern
**What goes wrong:** Copying an older Tailwind v3 tutorial's `tailwind.config.js` `theme.extend.colors` block and expecting it to work with `tailwindcss@4.3.3`.
**Why it happens:** Tailwind v4 moved theme configuration into CSS itself (`@theme { --color-*: ... }` inside `globals.css`), installed via the `@tailwindcss/postcss` PostCSS plugin rather than the old `tailwindcss` + `autoprefixer` PostCSS pair [CITED: tailwindcss.com/docs/installation/framework-guides/nextjs, tailwindcss.com/docs/theme].
**How to avoid:** Define the PLAN.md §2 palette (`#0d1117`/`#1a1a2e` backgrounds, `#ecad0a` accent, `#209dd7` blue, `#753991` purple) as `@theme { --color-terminal-bg: #0d1117; --color-accent-yellow: #ecad0a; ... }` in `app/globals.css`, not in a JS config object.
**Warning signs:** Custom color utilities (`bg-terminal-bg`) not generating any CSS output.

## Code Examples

### Backend response shapes to mirror in `lib/types.ts` (verbatim from source)
```typescript
// Source: backend/app/routes/portfolio.py:39-66 (PositionViewResponse, PortfolioResponse)
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

// Source: backend/app/routes/portfolio.py:24-48 (TradeRequest, TradeResponse)
export type TradeRequest = {
  ticker: string
  side: 'buy' | 'sell'
  quantity: number // must be > 0 — backend Pydantic Field(gt=0)
}

export type TradeResponse = {
  trade: { id: string; ticker: string; side: string; quantity: number; price: number; executed_at: string }
  cash_balance: number
  position: { ticker: string; quantity: number; avg_cost: number } | null // null if a sell fully closed the position
}

// Source: backend/app/routes/watchlist.py:31-41 (WatchlistEntryResponse)
export type WatchlistEntry = {
  ticker: string
  price: number | null       // null if not yet streamed
  previous_price: number | null
  direction: 'up' | 'down' | 'unchanged' | null
  timestamp: string | null
}

// Source: backend/app/routes/stream.py:24-31 (_serialize_tick), backend/app/market/base.py:16-19 (ChangeDirection)
export type PriceTick = {
  ticker: string
  price: number
  previous_price: number
  timestamp: string
  direction: 'up' | 'down' | 'unchanged'
}
export type PricesEvent = { ticks: PriceTick[] }
```

### Header live total value (client-side recompute, D-05 scope only)
```tsx
// components/header/Header.tsx — only the header total is client-recomputed;
// everything else in the header (cash_balance) comes straight from
// GET /api/portfolio, unmodified.
function useLiveTotalValue(positions: PositionView[], cashBalance: number) {
  const { prices } = usePriceStore()
  return useMemo(() => {
    const positionsValue = positions.reduce((sum, p) => {
      const tick = prices.get(p.ticker)
      const price = tick?.price ?? p.current_price ?? p.avg_cost // fallback chain, mirrors D-07
      return sum + p.quantity * price
    }, 0)
    return cashBalance + positionsValue
  }, [positions, cashBalance, prices])
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Tailwind v3 `tailwind.config.js` + `autoprefixer` | Tailwind v4 CSS-first `@theme` + `@tailwindcss/postcss` | Tailwind v4 (2025) | Theme customization moves out of JS config into `globals.css`; no `tailwind.config.js` file needed for this project's scope |
| Next.js Pages Router | App Router (`app/`) | Next.js 13+ | This is a greenfield project — App Router is the only sensible choice; matches D-10/D-12's directory conventions |

**Deprecated/outdated:**
- Manual `autoprefixer` + `postcss-import` wiring for Tailwind: superseded by `@tailwindcss/postcss` handling both in Tailwind v4.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `create-next-app@16.3.5 --tailwind` correctly scaffolds Tailwind v4 (CSS-first) wiring out of the box, rather than needing manual `@tailwindcss/postcss` setup | Standard Stack / Installation | Low — if the scaffold produces v3-style config instead, the fallback manual install command is already given; easily detected on first `npm run dev` |
| A2 | A 5-second grace window (Pattern 1 example) is a reasonable default for the yellow→red connection-dot transition | Architecture Patterns / Pattern 1 | Low — D-06 explicitly leaves exact thresholds to the executor/planner to tune; this is a starting point, not a locked value |
| A3 | No existing `frontend/` scaffolding conventions to reconcile with (greenfield) | Architecture / Recommended Project Structure | None — verified via `.planning/codebase/STRUCTURE.md:61-63,173-177` reading "frontend/ ... NOT YET BUILT" |

**If this table is empty:** N/A — see entries above. All are low-risk/easily-detected-at-execution-time assumptions, not decisions requiring upfront user confirmation.

## Open Questions

1. **Exact palette-to-Tailwind-token mapping beyond the three named accent colors**
   - What we know: PLAN.md §2 names three accents (`#ecad0a` yellow, `#209dd7` blue, `#753991` purple) and two background suggestions (`#0d1117`/`#1a1a2e`), plus "muted gray borders, no pure black."
   - What's unclear: Exact secondary/tertiary shades (hover states, disabled states, success/error green/red for the flash animation and P&L coloring) aren't specified.
   - Recommendation: Planner should let the executor pick standard Tailwind `green-500`/`red-500` (or similar) for flash/P&L coloring at 30% opacity (as used in Pattern 3's example) and treat `#0d1117` as the base `bg-terminal-bg` — low-risk, cosmetic-only choices.

2. **Whether `frontend/.env.development.local` (dev-only API base URL override) should be committed as `.env.example`**
   - What we know: `NEXT_PUBLIC_API_BASE_URL` is only needed in dev (empty/absent in the production static export served same-origin).
   - What's unclear: Whether the project wants a committed `frontend/.env.example` documenting this, analogous to the root `.env.example` (DEPLOY-04, out of scope for Phase 2).
   - Recommendation: Add a minimal `frontend/.env.example` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and a comment — cheap, prevents new-contributor confusion, doesn't conflict with any locked decision.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Node.js | Next.js dev/build tooling | ✓ | v22.13.0 | — |
| npm | Package installation | ✓ | 11.0.0 | — |
| Python/uv (backend, already running per Phase 1) | Local dev API target | ✓ (Phase 1 complete) | 3.12.12 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None configured yet for `frontend/` — greenfield |
| Config file | none — see Wave 0 |
| Quick run command | n/a (manual browser verification for this phase; TEST-04 frontend unit tests are Phase 6 scope per REQUIREMENTS.md traceability) |
| Full suite command | n/a |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| UI-01 | Watchlist flashes green/red on real SSE price change, not on heartbeat resend | manual (browser) | — | ❌ Wave 0 — no frontend test framework yet; automated coverage deferred to Phase 6 (TEST-04) |
| UI-06 | Positions table shows ticker/quantity/avg_cost/current_price/unrealized_pnl/pct_change, live | manual (browser) | — | ❌ Wave 0 |
| UI-07 | Trade bar buy/sell submits and reflects cash/position update with no confirmation dialog | manual (browser) | — | ❌ Wave 0 |
| UI-09 | Header shows live total value, cash, connection dot reflecting SSE state | manual (browser) | — | ❌ Wave 0 |
| UI-10 | Dark trading-terminal theme per PLAN.md §2 | manual (visual review) | — | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Manual browser check against the running `next dev` + backend `uv run uvicorn` pair (no automated frontend test runner exists yet).
- **Per wave merge:** Full manual walkthrough of the phase's 5 success criteria (watchlist flash, buy/sell, positions table, header, dark theme).
- **Phase gate:** All 5 PLAN.md-listed success criteria visually/functionally confirmed before `/gsd-verify-work`; formal automated frontend tests are explicitly Phase 6 scope (TEST-04) per REQUIREMENTS.md — do not block this phase on adding a test framework.

### Wave 0 Gaps
- No frontend test framework (Vitest/React Testing Library) exists yet. This is **expected and acceptable** — REQUIREMENTS.md's traceability table maps `TEST-04` (frontend unit tests) to Phase 6, not Phase 2. The planner should not add a testing-framework task to this phase; note it as explicitly deferred.
- `backend/tests/` already has 73+ passing tests covering everything this phase's frontend depends on (portfolio, trade, watchlist, stream) — no backend test gaps for this phase.

*(If no gaps: N/A — one documented, intentional gap above, consistent with the milestone's phase sequencing.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | No | Single hardcoded `user_id="default"`, no auth in this milestone (REQUIREMENTS.md "Out of Scope") |
| V3 Session Management | No | No sessions/cookies used anywhere in this phase |
| V4 Access Control | No | No access-control boundary — single user, no roles |
| V5 Input Validation | Yes | Ticker uppercase-normalization + quantity `type="number"` client-side (defense-in-depth UX only); the actual validation authority is the backend's Pydantic `TradeRequest` (`quantity: float = Field(gt=0)`) and `execute_trade()`'s cash/share checks — the frontend must never treat client-side validation as sufficient on its own |
| V6 Cryptography | No | No secrets, tokens, or crypto operations touch the frontend in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Reflected XSS via ticker/quantity input rendered back into the DOM | Tampering / Information Disclosure | React's default JSX text-node escaping (never use `dangerouslySetInnerHTML` for any user-supplied ticker string or trade error `detail` text) |
| Overly permissive dev-only CORS leaking into production | Elevation of Privilege (minor, given no auth) | Scope `allow_origins` to `http://localhost:3000` explicitly (Pattern 2), never `allow_origins=["*"]` with `allow_credentials=True`; confirm this middleware doesn't need to ship in the Phase 5 Docker image at all once same-origin — flag for Phase 5's research to revisit whether to strip it |
| Trusting client-computed portfolio math as authoritative | Tampering | N/A on the frontend itself (no write path uses client math) — enforced by design via D-04; call out in code review that no future change should let a client-supplied `total_value`/`unrealized_pnl` reach a mutation endpoint |

## Sources

### Primary (HIGH confidence)
- Context7 `/vercel/next.js` — static export (`output: 'export'`) configuration, unsupported-features list (rewrites/redirects/headers error in dev too), `next/image` incompatibility
- Context7 `/websites/tailwindcss` — Tailwind v4 Next.js installation (`@tailwindcss/postcss`), `@theme` CSS-first custom colors, dark mode patterns
- Context7 `/websites/fastapi_tiangolo` — `CORSMiddleware` constructor signature and usage example
- `backend/app/routes/portfolio.py`, `backend/app/routes/watchlist.py`, `backend/app/routes/stream.py`, `backend/app/portfolio/service.py`, `backend/app/market/base.py`, `backend/app/main.py` — read directly this session; all API contracts, field names, error strings, and enum values quoted above are verbatim
- `npm view <pkg> version` — direct registry queries for `next`, `react`, `react-dom`, `typescript`, `tailwindcss`, `@tailwindcss/postcss`, `eslint-config-next`, `@types/react`, `@types/node`
- `gsd_run query package-legitimacy check` — legitimacy verdicts for all 9 frontend packages

### Secondary (MEDIUM confidence)
- WebSearch "Next.js static export split frontend backend dev CORS EventSource cross-origin pattern" — cross-checked the env-var-API-base-URL + CORS pattern against general community practice (LogRocket, PropelAuth, GeeksforGeeks articles), consistent with the Context7-verified static-export constraints
- WebSearch "EventSource readyState onerror onopen reconnection behavior MDN" — `readyState` values (CONNECTING=0/OPEN=1/CLOSED=2), default retry timing (Chromium ~3000ms), no native `onreconnecting` event

### Tertiary (LOW confidence)
- None used as load-bearing claims in this document.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version verified against the live npm registry this session; package names are all extremely well-known, non-obscure libraries already named in PLAN.md
- Architecture: HIGH — backend contracts read verbatim from source; the static-export/CORS pitfall verified against official Next.js docs via Context7, not just training knowledge
- Pitfalls: HIGH — Pitfalls 1, 2, 4, 5 verified against source (backend code) or Context7 docs; Pitfall 3 is reasoned from the verified `execute_trade()` locking/snapshot behavior

**Research date:** 2026-09-17
**Valid until:** 2026-10-17 (30 days — frontend ecosystem versions move fast; re-verify `npm view` versions if planning is delayed)
