/**
 * Single API access point — every `fetch()` call to the backend goes
 * through this module (02-RESEARCH.md Pattern 2, D-04). No component may
 * call `fetch` directly.
 */

import type {
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
