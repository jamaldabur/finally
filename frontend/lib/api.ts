/**
 * Single API access point — every `fetch()` call to the backend goes
 * through this module (02-RESEARCH.md Pattern 2, D-04). No component may
 * call `fetch` directly.
 */

import type { PortfolioResponse, TradeRequest, TradeResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch(`${BASE}/api/portfolio`);
  if (!res.ok) {
    throw new Error(`GET /api/portfolio failed: ${res.status}`);
  }
  return res.json();
}

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
    const parsed: { detail?: string } = await res
      .json()
      .catch(() => ({ detail: undefined }));
    throw new Error(parsed.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}
