/**
 * TypeScript mirrors of the backend's wire-format response/request shapes.
 *
 * These fields keep the backend's snake_case naming (avg_cost, current_price,
 * etc.) because they are wire-format keys, not local TypeScript identifiers —
 * D-11's camelCase convention governs identifiers this frontend authors, not
 * JSON the backend already publishes. Nullability is preserved exactly from
 * source; do not widen or narrow without re-checking the backend route.
 *
 * Sources (verbatim, 02-PATTERNS.md / 02-RESEARCH.md / 03-PATTERNS.md):
 * - backend/app/routes/portfolio.py (PositionViewResponse, PortfolioResponse,
 *   TradeRequest, TradeResponse)
 * - backend/app/routes/watchlist.py (WatchlistEntryResponse)
 * - backend/app/routes/stream.py (_serialize_tick), backend/app/market/base.py
 *   (ChangeDirection)
 * - backend/app/routes/chat.py (ChatRequest, ChatResponse, ChatMessageResponse,
 *   ChatHistoryResponse, TradeActionResponse, WatchlistActionResponse)
 * - backend/app/routes/portfolio.py (SnapshotResponse, PortfolioHistoryResponse)
 */

export type PositionView = {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number;
  unrealized_pnl: number;
  pct_change: number;
};

export type PortfolioResponse = {
  cash_balance: number;
  positions: PositionView[];
  positions_value: number;
  total_value: number;
  total_unrealized_pnl: number;
};

export type SnapshotResponse = {
  total_value: number;
  recorded_at: string;
};

export type PortfolioHistoryResponse = {
  snapshots: SnapshotResponse[];
};

export type TradeRequest = {
  ticker: string;
  side: "buy" | "sell";
  quantity: number; // must be > 0 — backend Pydantic Field(gt=0)
};

export type TradeResponse = {
  trade: {
    id: string;
    ticker: string;
    side: string;
    quantity: number;
    price: number;
    executed_at: string;
  };
  cash_balance: number;
  // null when a sell fully closes the position
  position: { ticker: string; quantity: number; avg_cost: number } | null;
};

export type WatchlistEntry = {
  ticker: string;
  price: number | null; // null if not yet streamed
  previous_price: number | null;
  direction: "up" | "down" | "unchanged" | null;
  timestamp: string | null;
};

export type PriceTick = {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: string;
  direction: "up" | "down" | "unchanged";
};

export type PricesEvent = { ticks: PriceTick[] };

// Chat (Phase 3). ActionOutcome captures the shared outcome/reason shape
// every LLM-proposed action carries — `reason` is null on success and the
// backend's verbatim rejection text on error (mirrors postTrade()'s D-03
// error-passthrough convention). `price` on TradeAction is null when the
// action errored before a fill price ever existed.
export type ActionOutcome = {
  outcome: "executed" | "error";
  reason: string | null;
};

export type TradeAction = ActionOutcome & {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number | null;
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

export type ChatRequest = {
  message: string;
};
