/**
 * Per-test `fetch` stub (Phase 6, TEST-04, D-05). Every frontend API call
 * funnels through `frontend/lib/api.ts`'s single chokepoint, so stubbing the
 * global `fetch` here covers every store's mount-time request without a
 * general-purpose HTTP-mocking library (mirrors the backend's "prefer stub
 * classes over mocking frameworks" convention — see
 * `.planning/codebase/TESTING.md`).
 *
 * Routes are keyed by `"<METHOD> <pathname>"` (the `?limit=` query on
 * `GET /api/portfolio/history` is intentionally ignored by the key so a
 * route registration does not need to special-case it — `frontend/lib/
 * api.ts`'s `fetchPortfolioHistory()` is the only caller that appends a
 * query string). Built-in defaults answer the four requests every provider
 * in `frontend/app/layout.tsx` issues on mount, with empty-but-valid shapes,
 * so a test that only cares about one store doesn't have to stub the other
 * three. An unrouted request is recorded and the returned promise rejects
 * loudly — never a silent empty 200 — so a typo'd or newly-added endpoint
 * fails a test immediately instead of returning misleading data.
 */

import { vi } from "vitest";
import type {
  ChatMessage,
  PortfolioHistoryResponse,
  PortfolioResponse,
  WatchlistEntry,
} from "@/lib/types";

export type FetchReply = { status?: number; body?: unknown };

export type RecordedCall = {
  method: string;
  path: string;
  search: string;
  body: unknown;
};

type RouteHandler =
  | FetchReply
  | FetchReply[]
  | ((call: RecordedCall) => FetchReply | Promise<FetchReply>);

export type Routes = Record<string, RouteHandler>;

export function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const DEFAULT_PORTFOLIO: PortfolioResponse = {
  cash_balance: 10000,
  positions: [],
  positions_value: 0,
  total_value: 10000,
  total_unrealized_pnl: 0,
};

const DEFAULT_HISTORY: PortfolioHistoryResponse = { snapshots: [] };
const DEFAULT_CHAT_HISTORY: { messages: ChatMessage[] } = { messages: [] };
const DEFAULT_WATCHLIST: { watchlist: WatchlistEntry[] } = { watchlist: [] };

const DEFAULT_ROUTES: Routes = {
  "GET /api/portfolio": { body: DEFAULT_PORTFOLIO },
  "GET /api/watchlist": { body: DEFAULT_WATCHLIST },
  "GET /api/chat": { body: DEFAULT_CHAT_HISTORY },
  "GET /api/portfolio/history": { body: DEFAULT_HISTORY },
};

/**
 * Installs a stubbed global `fetch` for the current test. Caller-supplied
 * `routes` override the built-in defaults key by key (a partial override
 * does not disturb the other three default routes).
 */
export function stubFetch(routes: Routes = {}): {
  calls: RecordedCall[];
  callsTo: (key: string) => RecordedCall[];
  unexpected: RecordedCall[];
} {
  const merged: Routes = { ...DEFAULT_ROUTES, ...routes };
  const arrayCursor = new Map<string, number>();
  const calls: RecordedCall[] = [];
  const unexpected: RecordedCall[] = [];

  const fetchImpl = async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const rawUrl =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const url = new URL(rawUrl, "http://stub.local");
    const method = (init?.method ?? "GET").toUpperCase();
    const path = url.pathname;
    const key = `${method} ${path}`;

    let body: unknown;
    if (typeof init?.body === "string" && init.body.length > 0) {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }

    const call: RecordedCall = { method, path, search: url.search, body };
    calls.push(call);

    const handler = merged[key];
    if (handler === undefined) {
      unexpected.push(call);
      throw new Error(`Unrouted fetch call: ${key}`);
    }

    let reply: FetchReply;
    if (typeof handler === "function") {
      reply = await handler(call);
    } else if (Array.isArray(handler)) {
      const idx = arrayCursor.get(key) ?? 0;
      const useIdx = Math.min(idx, handler.length - 1);
      arrayCursor.set(key, idx + 1);
      reply = handler[useIdx];
    } else {
      reply = handler;
    }

    const status = reply.status ?? 200;
    const responseBody =
      reply.body !== undefined ? JSON.stringify(reply.body) : "";
    return new Response(responseBody, {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };

  vi.stubGlobal("fetch", vi.fn(fetchImpl));

  return {
    calls,
    callsTo(key: string) {
      return calls.filter((c) => `${c.method} ${c.path}` === key);
    },
    unexpected,
  };
}
