/**
 * TypeScript mirrors of the backend's wire-format response/request shapes.
 *
 * These fields keep the backend's snake_case naming (avg_cost, current_price,
 * etc.) because they are wire-format keys, not local TypeScript identifiers —
 * D-11's camelCase convention governs identifiers this frontend authors, not
 * JSON the backend already publishes. Nullability is preserved exactly from
 * source; do not widen or narrow without re-checking the backend route.
 *
 * Sources (verbatim, 02-PATTERNS.md / 02-RESEARCH.md):
 * - backend/app/routes/portfolio.py (PositionViewResponse, PortfolioResponse,
 *   TradeRequest, TradeResponse)
 * - backend/app/routes/watchlist.py (WatchlistEntryResponse)
 * - backend/app/routes/stream.py (_serialize_tick), backend/app/market/base.py
 *   (ChangeDirection)
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
