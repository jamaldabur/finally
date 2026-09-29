# Phase 3: AI Chat Copilot - Pattern Map

**Mapped:** 2026-09-17
**Files analyzed:** 13
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/llm/schema.py` | model | transform | `backend/app/portfolio/service.py` (dataclass shapes) | role-match |
| `backend/app/llm/client.py` | service | request-response (external API) | `backend/app/market/factory.py` (env-var gated construction) + `.claude/skills/litellm-stream/SKILL.md` | role-match |
| `backend/app/llm/mock.py` | service | transform | `backend/app/market/factory.py` (env-var branching) | partial |
| `backend/app/db/chat_messages.py` (extend) | model/db | CRUD | `backend/app/db/trades.py` | exact |
| `backend/app/portfolio/service.py` (extend `execute_trade`) | service | CRUD | itself (existing file, add guard) | exact |
| `backend/app/routes/chat.py` | route/controller | request-response | `backend/app/routes/portfolio.py` + `backend/app/routes/watchlist.py` | exact |
| `backend/tests/routes/test_chat.py` | test | request-response | `backend/tests/routes/test_portfolio.py` | exact |
| `backend/tests/db/test_chat_messages.py` (extend) | test | CRUD | existing (schema-only) file + `backend/tests/db` trades test pattern | exact |
| `backend/tests/llm/test_client.py`, `test_mock.py` | test | request-response | `backend/tests/routes/test_portfolio.py` (mocking/monkeypatch conventions) | role-match |
| `backend/tests/portfolio/test_service.py` (extend) | test | CRUD | existing file (add regression test) | exact |
| `frontend/lib/types.ts` (extend) | model | transform | itself — existing `PortfolioResponse`/`WatchlistEntry` shapes | exact |
| `frontend/lib/api.ts` (extend) | service | request-response | itself — `fetchPortfolio()`/`postTrade()` | exact |
| `frontend/lib/chatStore.tsx` | provider/store | request-response | `frontend/lib/portfolioStore.tsx` | exact |
| `frontend/components/chat/ChatPanel.tsx` | component | request-response | `frontend/components/watchlist/WatchlistPanel.tsx` | exact |
| `frontend/components/chat/ChatInput.tsx` | component | request-response | `frontend/components/trade-bar/TradeBar.tsx` | exact |
| `frontend/components/chat/ChatMessageList.tsx`, `ActionBadge.tsx` | component | transform | `frontend/components/watchlist/WatchlistPanel.tsx` (list rendering) | role-match |
| `frontend/app/page.tsx` (modify — add third column) | component | transform | itself — existing two-column layout | exact |

## Pattern Assignments

### `backend/app/routes/chat.py` (route, request-response)

**Analog:** `backend/app/routes/portfolio.py` (full file read above) and `backend/app/routes/watchlist.py`

**Module docstring / layering pattern** (portfolio.py lines 1-9):
```python
"""POST /api/portfolio/trade, GET /api/portfolio, GET /api/portfolio/history
— market order execution and portfolio reads (PLAN.md §8 "Portfolio").

The only module in the request path permitted to raise HTTPException;
app/portfolio/service.py returns a structured TradeResult that this route
translates into HTTP (01-RESEARCH.md Pattern 3).
"""
```
Copy this exact framing for `chat.py`'s docstring: "The only module in the chat request path permitted to raise HTTPException; `app/llm/` and `app/db/chat_messages.py` return plain data, this route translates failures into HTTP."

**Imports pattern** (portfolio.py lines 1-21):
```python
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..db import portfolio_snapshots
from ..portfolio.service import compute_portfolio_view, execute_trade

router = APIRouter()
```
Mirror exactly, substituting `from ..db import chat_messages`, `from ..llm.client import call_llm_structured` (or mock), `from ..portfolio.service import execute_trade, compute_portfolio_view`, `from ..db.watchlist import add_watchlist_ticker, remove_watchlist_ticker, get_watchlist_entries`.

**Request/response Pydantic models** (portfolio.py lines 24-76): every route in this codebase declares a `BaseModel` per request/response shape, field-validated at the Pydantic layer (`Field(min_length=1)`, `Field(gt=0)`, `Literal[...]`). Do the same for `ChatRequest`, `ChatMessageResponse`, `ActionOutcome`, `ChatResponse`.

**Route handler + HTTPException translation** (portfolio.py lines 114-126):
```python
@router.post("/api/portfolio/trade")
async def post_trade(body: TradeRequest, request: Request) -> TradeResponse:
    result = await execute_trade(...)
    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.reason)
    ...
```
`POST /api/chat` follows the same shape but must NOT raise `HTTPException` for individual trade/watchlist action failures (CHAT-04 — those become per-action `outcome` annotations in the 200 response body, not HTTP errors). Only raise `HTTPException` for a genuine request-level failure (e.g. malformed body — handled by Pydantic automatically).

**Ticker normalization pattern** (watchlist.py lines 53-54, 96-99):
```python
def _normalize(ticker: str) -> str:
    return ticker.strip().upper()

...
ticker = _normalize(body.ticker)
if not await request.app.state.market_source.is_valid_ticker(ticker):
    raise HTTPException(status_code=400, detail=f"Unknown ticker: {ticker}")
added = await add_watchlist_ticker(ticker)
```
Reuse this exact normalize-then-validate-then-mutate sequence when applying LLM-proposed `watchlist_changes[]` items — call `add_watchlist_ticker`/`remove_watchlist_ticker` directly (no re-validation duplication), annotate `executed`/`error` per Pattern below instead of raising.

---

### `backend/app/portfolio/service.py` (extend `execute_trade`, CRUD)

**Analog:** itself — `backend/app/portfolio/service.py` lines 135-207 (full `execute_trade` read above)

Add a guard as the very first check inside `execute_trade()`, before the `is_valid_ticker` check (lines 149-151), following the file's existing `TradeResult(status="error", reason=..., trade=None, cash_balance=None, position=None)` return shape used throughout:
```python
# New guard — closes the gap described in 03-RESEARCH.md Pitfall 2
if not isinstance(quantity, (int, float)) or quantity <= 0 or not math.isfinite(quantity):
    return TradeResult(
        status="error",
        reason=f"Invalid quantity: {quantity!r}",
        trade=None,
        cash_balance=None,
        position=None,
    )
if side not in ("buy", "sell"):
    return TradeResult(
        status="error",
        reason=f"Invalid side: {side!r}",
        trade=None,
        cash_balance=None,
        position=None,
    )
```
Requires `import math` added to the existing import block (lines 11-22).

---

### `backend/app/llm/client.py` (service, request-response)

**Analog:** `.claude/skills/litellm-stream/SKILL.md` (project-mandated, verbatim) + `backend/app/market/factory.py` (env-var gated construction pattern)

**LiteLLM structured-output call** (SKILL.md lines 36-46, adapted to async per this codebase's async-first convention documented in `.claude/CLAUDE.md` "Async Patterns"):
```python
from litellm import acompletion
import litellm

litellm.enable_json_schema_validation = True
MODEL = "openrouter/openai/gpt-oss-120b"

async def call_llm_structured(messages: list[dict], schema: type[BaseModel]) -> str:
    response = await acompletion(
        model=MODEL, messages=messages, response_format=schema,
        reasoning_effort="low", stream=True,
    )
    json_string = ""
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            json_string += content
    return json_string
```

**Env-var gating pattern** (`backend/app/market/factory.py`, full file):
```python
import os

def build_market_data_source() -> MarketDataSource:
    """... if MASSIVE_API_KEY is set and non-empty, use Massive;
    otherwise use the simulator. Nothing else in the app should
    re-check this env var — call this once at startup ..."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveMarketDataSource(api_key=api_key)
    return SimulatorMarketDataSource()
```
Mirror this exact `os.environ.get(..., "").strip()` truthiness-check style for the `LLM_MOCK` gate in `chat.py`/`client.py` — check once (e.g. at the top of the chat route handler or in a small `is_mock_mode() -> bool` helper), not scattered `os.environ` reads.

---

### `backend/app/llm/schema.py` (model, transform)

No direct analog (first Pydantic `response_format`-schema module in this codebase) — mirror the codebase's existing frozen-dataclass/Pydantic BaseModel conventions from `backend/app/portfolio/service.py` lines 27-45 (`TradeResult`, `PortfolioView` — `@dataclass(frozen=True)`) for internal shapes, and `backend/app/routes/portfolio.py` lines 24-76 for the Pydantic `BaseModel` conventions (`Field(min_length=1)`, `Literal[...]`) for the LLM-facing `response_format` schema itself, since it must be a `pydantic.BaseModel` subclass per the skill.

---

### `backend/app/db/chat_messages.py` (extend — add `insert_message`/`get_messages`)

**Analog:** `backend/app/db/trades.py` (full file read above) — near-identical shape already called out by RESEARCH.md Code Example §4.

**Full CRUD pattern to copy** (trades.py lines 30-96):
```python
@dataclass(frozen=True)
class Trade:
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str

def _insert_trade_sync(ticker, side, quantity, price, user_id) -> Trade:
    trade_id = str(uuid.uuid4())
    executed_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("INSERT INTO trades (...) VALUES (...)", (...))
    return Trade(...)

def _get_trades_sync(user_id: str) -> list[Trade]:
    with _connect() as conn:
        rows = conn.execute("SELECT ... WHERE user_id = ? ORDER BY executed_at ASC", (user_id,)).fetchall()
    return [Trade(...) for row in rows]

async def insert_trade(ticker, side, quantity, price, user_id=DEFAULT_USER_ID) -> Trade:
    return await asyncio.to_thread(_insert_trade_sync, ticker, side, quantity, price, user_id)

async def get_trades(user_id=DEFAULT_USER_ID) -> list[Trade]:
    return await asyncio.to_thread(_get_trades_sync, user_id)
```
Apply identically for `ChatMessage` dataclass (`id, role, content, actions, created_at`), `insert_message()`, `get_messages(limit=50)` — the existing `chat_messages.py` already has `_connect` import and `_SCHEMA`/`_init_db_sync`/`init_db()` (lines 1-42) in place; add the dataclass + sync helpers + async wrappers below the existing `init_db()`, following `trades.py`'s exact ordering (dataclass → sync helpers → async init → async CRUD).

**`get_messages` needs a LIMIT clause** (trades.py's `_get_trades_sync` has none — trades are never pruned per PLAN.md §7, but chat history should cap per RESEARCH.md Pitfall 5): add `ORDER BY created_at ASC LIMIT ?` with the `limit` param, still following the same `with _connect() as conn: rows = conn.execute(...).fetchall()` shape.

---

### Frontend: `frontend/lib/chatStore.tsx` (provider/store, request-response)

**Analog:** `frontend/lib/portfolioStore.tsx` (full file read above)

**Context + mount-fetch + exported hook pattern** (lines 1-113):
```tsx
"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { fetchPortfolio } from "./api";
import type { PortfolioResponse } from "./types";

type PortfolioStoreValue = {
  portfolio: PortfolioResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const PortfolioContext = createContext<PortfolioStoreValue | null>(null);

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await fetchPortfolio();
        if (cancelled) return;
        setPortfolio(next);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load portfolio");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <PortfolioContext.Provider value={{ portfolio, loading, error, refresh }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio(): PortfolioStoreValue {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error("usePortfolio must be used within PortfolioProvider");
  return ctx;
}
```
For `chatStore.tsx`: substitute `fetchChatHistory()` for the mount effect (CHAT-05 hydrate), add a `sendMessage(text: string): Promise<void>` method (calls `postChatMessage`, appends both the user message and the assistant response + actions to local `messages` state — no periodic-refresh interval needed since chat state only changes via explicit send, unlike portfolio's 5s poll at lines 93-98). Use the same `isRefreshingRef`-style in-flight guard for the "input disabled while in flight" UI-08 requirement.

---

### Frontend: `frontend/lib/api.ts` (extend, request-response)

**Analog:** itself — `fetchPortfolio()` (lines 16-22) and `postTrade()` (lines 41-60)

**GET pattern** (lines 16-22):
```typescript
export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE}/api/portfolio`);
  if (!res.ok) {
    throw new Error(`GET /api/portfolio failed: ${res.status}`);
  }
  return res.json();
}
```
Copy verbatim for `fetchChatHistory(): Promise<{messages: ChatMessage[]}>`.

**POST pattern with backend-error-passthrough** (lines 34-60) — this is the load-bearing pattern; the UI-SPEC's error-badge copy contract explicitly requires "the verbatim string returned by `execute_trade()`... never a rephrased or generic substitute", mirroring this exact existing convention:
```typescript
type ApiErrorDetail = string | { msg: string; loc?: (string | number)[] }[];

export async function postTrade(body: TradeRequest): Promise<TradeResponse> {
  const res = await fetch(`${BASE}/api/portfolio/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const parsed: { detail?: ApiErrorDetail } = await res.json().catch(() => ({ detail: undefined }));
    const message = Array.isArray(parsed.detail)
      ? parsed.detail.map((e) => e.msg).join("; ")
      : (parsed.detail ?? `HTTP ${res.status}`);
    throw new Error(message);
  }
  return res.json();
}
```
Copy verbatim for `postChatMessage(body: {message: string}): Promise<ChatResponse>` — note `POST /api/chat` per CHAT-04 returns 200 with per-action `outcome`/`reason` fields even when a proposed trade fails, so this `!res.ok` error path only fires for genuine transport/validation failures, not action-level errors (those are read from the 200 response body's `trades[].reason`/`watchlist_changes[].reason` directly by `ActionBadge.tsx`, per the UI-SPEC's verbatim-reason requirement).

---

### Frontend: `frontend/lib/types.ts` (extend, transform)

**Analog:** itself — existing type shapes (full file read above), module docstring convention at lines 1-16 (wire-format mirrors, snake_case preserved, sourced-from comment block).

Add `ChatMessage`, `ChatResponse`, `ActionOutcome` types following the exact same snake_case-preserving, nullability-preserving style as `WatchlistEntry` (lines 56-62) and `TradeResponse` (lines 42-54):
```typescript
export type ActionOutcome = {
  outcome: "executed" | "error";
  reason: string | null;
};

export type TradeAction = ActionOutcome & {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number | null; // null on error before a fill price exists
};

export type WatchlistAction = ActionOutcome & {
  ticker: string;
  action: "add" | "remove";
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  trades: TradeAction[];
  watchlist_changes: WatchlistAction[];
  created_at: string;
};

export type ChatResponse = {
  message: string;
  trades: TradeAction[];
  watchlist_changes: WatchlistAction[];
};
```
Extend the sourced-from comment block at the top of the file to add `backend/app/routes/chat.py`.

---

### Frontend: `frontend/components/chat/ChatPanel.tsx` (component, request-response)

**Analog:** `frontend/components/watchlist/WatchlistPanel.tsx` (full file read above)

**Panel shell + loading/error/empty branching** (lines 1-79):
```tsx
"use client";
import { useEffect, useState } from "react";
import { fetchWatchlist } from "@/lib/api";

export function WatchlistPanel() {
  const [entries, setEntries] = useState<WatchlistEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { watchlist } = await fetchWatchlist();
        if (!cancelled) { setEntries(watchlist); setError(null); }
      } catch (e) {
        if (!cancelled) { setError(...); setEntries([]); }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
      <div className="mb-2 flex items-center justify-between text-sm font-medium text-terminal-text-muted">
        <h2>Watchlist</h2>
        <span className="text-xs">Chg. since open</span>
      </div>
      {entries === null && <p className="text-sm text-terminal-text-muted">Loading watchlist&hellip;</p>}
      {entries !== null && error && <p className="text-sm text-red-400" role="alert">{error}</p>}
      {entries !== null && !error && entries.length === 0 && <p>...</p>}
      {entries !== null && entries.length > 0 && (
        <div className="flex flex-col">{entries.map((entry) => <WatchlistRow key={entry.ticker} entry={entry} />)}</div>
      )}
    </section>
  );
}
```
`ChatPanel.tsx` uses `useChat()` (from `chatStore.tsx`, via `<ChatProvider>` at the app root — same pattern as `PortfolioProvider` must already wrap `page.tsx` for `usePortfolio()` to work) instead of local `useEffect`+`fetchWatchlist`, but the loading/error/empty ternary-branching structure and `rounded-lg border border-terminal-border bg-terminal-panel` shell is identical. Per UI-SPEC's Layout & Interaction Contract, this panel additionally needs expand/collapse local state (`useState<boolean>`, session-only, no localStorage) — not present in any existing panel, this is the one genuinely new structural element.

---

### Frontend: `frontend/components/chat/ChatInput.tsx` (component, request-response)

**Analog:** `frontend/components/trade-bar/TradeBar.tsx` (full file read above)

**Controlled-input + isSubmitting-disable + inline-error pattern** (lines 1-114):
```tsx
"use client";
import { useState } from "react";
import { postTrade } from "@/lib/api";
import { usePortfolio } from "@/lib/portfolioStore";

export function TradeBar() {
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(side: Side) {
    if (isSubmitting) return;
    ...
    setIsSubmitting(true);
    try {
      await postTrade({...});
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trade failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-lg border border-terminal-border bg-terminal-panel p-4">
      ...
      <input ... disabled={isSubmitting} className="rounded border border-terminal-border bg-terminal-bg px-2 py-1 text-sm text-terminal-text disabled:opacity-50" />
      <button ... disabled={isSubmitting} className="... bg-accent-purple ... disabled:opacity-50">Buy</button>
      {error && <p className="mt-2 text-sm text-red-400" role="alert">{error}</p>}
    </section>
  );
}
```
`ChatInput.tsx` mirrors this exact `isSubmitting`-guard + try/catch/finally + `disabled:opacity-50` input-disable shape, substituting `sendMessage()` (from `useChat()`) for `postTrade()`, single Send button styled `bg-accent-purple` (per UI-SPEC Color contract — purple reserved for Buy/Sell + Send), and per UI-SPEC's "retry text retention" assumption, do NOT clear the input text on error (unlike TradeBar which doesn't clear ticker either, only `quantity` on success at line 48).

---

## Shared Patterns

### Env-var gated branching (`LLM_MOCK`)
**Source:** `backend/app/market/factory.py` (full file)
**Apply to:** `backend/app/llm/client.py`, `backend/app/routes/chat.py`
```python
api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
if api_key:
    return MassiveMarketDataSource(api_key=api_key)
return SimulatorMarketDataSource()
```
Use identical `os.environ.get("LLM_MOCK", "").strip().lower() == "true"` truthiness check, read once per request (or once at a module boundary), never scattered.

### asyncio.to_thread for sync DB work
**Source:** `backend/app/db/trades.py` lines 89-96 (and `backend/app/db/chat_messages.py` lines 36-42, `.claude/CLAUDE.md` "Async Patterns": "Database access wrapped via `asyncio.to_thread()`")
**Apply to:** `backend/app/db/chat_messages.py`'s new `insert_message`/`get_messages`
```python
async def insert_trade(...) -> Trade:
    return await asyncio.to_thread(_insert_trade_sync, ...)
```

### Structured `TradeResult`-style outcome dataclass
**Source:** `backend/app/portfolio/service.py` lines 126-133
```python
@dataclass(frozen=True)
class TradeResult:
    status: Literal["executed", "error"]
    reason: str | None
    trade: Trade | None
    cash_balance: float | None
    position: Position | None
```
**Apply to:** the new `AnnotatedAction` shape for chat (per RESEARCH.md Code Example §3) — same `status`/`outcome` + `reason` vocabulary, so trade-bar and chat-originated trades read identically on the frontend.

### Backend-error-verbatim-passthrough (never rephrase)
**Source:** `frontend/lib/api.ts` lines 34-60 (`postTrade`'s `ApiErrorDetail` handling) — and UI-SPEC's explicit callback to "the existing D-03 convention already locked in `frontend/lib/api.ts`'s `postTrade()`"
**Apply to:** `ActionBadge.tsx`'s error-badge rendering: `{reason}` must be the exact string from `execute_trade()`/`add_watchlist_ticker()`/`remove_watchlist_ticker()`, never rephrased.

### Route layering: only routes/ raises HTTPException
**Source:** `backend/app/routes/portfolio.py` docstring lines 1-9, `backend/app/routes/watchlist.py` docstring lines 1-11
**Apply to:** `backend/app/routes/chat.py` — all business logic (LLM call, action execution) lives in `app/llm/` and reuses `app/portfolio/service.py`/`app/db/watchlist.py`; only `chat.py` may `raise HTTPException`.

## No Analog Found

None — every file in this phase's scope has a close, tracked analog in the existing backend/frontend codebase.

## Metadata

**Analog search scope:** `backend/app/routes/`, `backend/app/db/`, `backend/app/portfolio/`, `backend/app/market/`, `frontend/lib/`, `frontend/components/`, `.claude/skills/litellm-stream/`
**Files scanned:** 13 (all confirmed git-tracked via `git ls-files`)
**Pattern extraction date:** 2026-09-17
