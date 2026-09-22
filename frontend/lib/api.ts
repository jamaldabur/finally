/**
 * Single API access point — every `fetch()` call to the backend goes
 * through this module (02-RESEARCH.md Pattern 2, D-04). No component may
 * call `fetch` directly.
 */

import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  PortfolioHistoryResponse,
  PortfolioResponse,
  TradeRequest,
  TradeResponse,
  WatchlistEntry,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE}/api/portfolio`);
  if (!res.ok) {
    throw new Error(`GET /api/portfolio failed: ${res.status}`);
  }
  return res.json();
}

// `limit` is required rather than defaulted here: the display bound is a
// property of the surface doing the drawing (currently
// HISTORY_POINT_LIMIT, owned by portfolioHistoryStore.tsx), and a default
// on this shared module would let a second future caller silently inherit
// a number chosen for a panel it isn't rendering.
export async function fetchPortfolioHistory(
  limit: number,
): Promise<PortfolioHistoryResponse> {
  const res = await fetch(
    `${BASE}/api/portfolio/history?limit=${limit}`,
  );
  if (!res.ok) {
    throw new Error(`GET /api/portfolio/history failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchWatchlist(): Promise<{
  watchlist: WatchlistEntry[];
}> {
  const res = await fetch(`${BASE}/api/watchlist`);
  if (!res.ok) {
    throw new Error(`GET /api/watchlist failed: ${res.status}`);
  }
  return res.json();
}

// FastAPI's own Pydantic validation (422) returns `detail` as an array of
// error objects (`{msg, loc, type, input}`), while a manually-raised
// HTTPException (e.g. the 400 "Insufficient cash: ..." path in
// execute_trade()) returns `detail` as a plain string. Both shapes must be
// handled so the user always sees a readable message.
type ApiErrorDetail = string | { msg: string; loc?: (string | number)[] }[];

export async function postTrade(body: TradeRequest): Promise<TradeResponse> {
  const res = await fetch(`${BASE}/api/portfolio/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // The backend's own rejection text (e.g. "Insufficient cash: ...") is
    // the message the user must see (D-03) — never a generic substitute.
    // Fall back to "HTTP {status}" only when the body isn't JSON at all.
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

export async function fetchChatHistory(): Promise<{
  messages: ChatMessage[];
}> {
  const res = await fetch(`${BASE}/api/chat`);
  if (!res.ok) {
    throw new Error(`GET /api/chat failed: ${res.status}`);
  }
  return res.json();
}

// Per CHAT-04, POST /api/chat returns 200 with per-action outcome/reason
// even when a proposed trade or watchlist change is rejected — a proposed
// action failing is not a request failure. So `!res.ok` here means a
// transport or request-validation failure only (e.g. a blank message);
// action-level errors are read from the 200 body's trades[]/
// watchlist_changes[] `reason` fields, never from this error path.
export async function postChatMessage(
  body: ChatRequest,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
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
