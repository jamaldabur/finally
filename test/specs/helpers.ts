import type { Page, Locator } from "@playwright/test";
import { expect } from "@playwright/test";

/**
 * Shared locators and readers for the E2E specs (Task 3, 06-05-PLAN.md).
 * `01-fresh-start.spec.ts` stays self-contained as the harness's own smoke
 * test and does not use these — this file exists for every spec added
 * after it (Plan 06-06 extends it further), so each helper here is kept
 * small and independent rather than assuming a particular spec's flow.
 */

// The ten tickers backend/app/market/simulator.py's DEFAULT_WATCHLIST seeds
// on a fresh database (root PLAN.md §7).
export const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
] as const;

/** The section carrying the exact heading "Watchlist" (WatchlistPanel.tsx). */
export function watchlistSection(page: Page): Locator {
  return page.locator("section", {
    has: page.getByRole("heading", { name: "Watchlist", exact: true }),
  });
}

/**
 * A row button within the watchlist section whose accessible name starts
 * with `ticker` followed by a word boundary (WatchlistRow.tsx renders the
 * ticker as the row's first text node, so this never matches a ticker
 * that is merely a substring of another, e.g. "V" vs "NVDA").
 */
export function watchlistRow(page: Page, ticker: string): Locator {
  return watchlistSection(page).getByRole("button", {
    name: new RegExp(`^${ticker}\\b`),
  });
}

/**
 * The header's connection-status text, exactly one of Connected,
 * Reconnecting or Disconnected (ConnectionDot.tsx — a visible label, not
 * color alone).
 */
export function connectionStatus(page: Page): Locator {
  return page.getByText(/^(Connected|Reconnecting|Disconnected)$/, {
    exact: true,
  });
}

async function readHeaderDollarFigure(
  page: Page,
  label: "Cash" | "Total Value",
): Promise<number> {
  const headerText = await page.locator("header").innerText();
  const match = headerText.match(
    new RegExp(`${label}\\s*\\$([0-9]+(?:\\.[0-9]+)?)`),
  );
  if (!match) {
    throw new Error(
      `Could not find "${label} $<amount>" in header text: ${headerText}`,
    );
  }
  return Number(match[1]);
}

/** Parses the header's rendered "Cash $X.XX" figure into a number. */
export function readCash(page: Page): Promise<number> {
  return readHeaderDollarFigure(page, "Cash");
}

/** Parses the header's rendered "Total Value $X.XX" figure into a number. */
export function readTotalValue(page: Page): Promise<number> {
  return readHeaderDollarFigure(page, "Total Value");
}

/**
 * Captures the watchlist section's rendered text once, then polls until it
 * differs — proves the SSE stream is actually delivering ticks rather than
 * asserting on a single render. No fixed sleep.
 */
export async function waitForPricesToMove(
  page: Page,
  timeoutMs = 15_000,
): Promise<void> {
  const section = watchlistSection(page);
  const initialText = await section.innerText();
  await expect
    .poll(async () => section.innerText(), { timeout: timeoutMs })
    .not.toBe(initialText);
}

/**
 * Trading, positions, chat, API and heatmap helpers (Plan 06-06). Kept
 * independent from the Plan 06-05 helpers above — no rename of existing
 * exports.
 */

/** The section carrying the exact heading "Positions" (PositionsTable.tsx). */
export function positionsSection(page: Page): Locator {
  return page.locator("section", {
    has: page.getByRole("heading", { name: "Positions", exact: true }),
  });
}

/**
 * A positions table body row that has a cell whose exact text is `ticker`
 * (PositionsRow.tsx renders the ticker as its own `<td>`, so this never
 * partial-matches a longer ticker).
 */
export function positionRow(page: Page, ticker: string): Locator {
  return positionsSection(page)
    .locator("tbody tr")
    .filter({ has: page.getByText(ticker, { exact: true }) });
}

/**
 * Fills the trade bar's exact-labelled "Ticker"/"Quantity" inputs and clicks
 * the exact "Buy"/"Sell" button (TradeBar.tsx). Does not wait for the
 * resulting portfolio refresh — callers assert on whatever settles next.
 */
export async function tradeViaBar(
  page: Page,
  side: "buy" | "sell",
  ticker: string,
  quantity: number | string,
): Promise<void> {
  await page.getByLabel("Ticker", { exact: true }).fill(ticker);
  await page.getByLabel("Quantity", { exact: true }).fill(String(quantity));
  await page
    .getByRole("button", { name: side === "buy" ? "Buy" : "Sell", exact: true })
    .click();
}

/**
 * Parses a rendered money string (e.g. "$1,234.56", "+$12.30") into a
 * number. Throws on anything that doesn't reduce to a finite number, so a
 * spec never silently compares against NaN.
 */
export function parseMoney(text: string): number {
  const stripped = text.replace(/[$,+]/g, "").trim();
  const value = Number(stripped);
  if (!Number.isFinite(value)) {
    throw new Error(`parseMoney: could not parse "${text}"`);
  }
  return value;
}

/** Mirrors backend/app/routes/portfolio.py's PortfolioResponse wire shape. */
export type PortfolioJson = {
  cash_balance: number;
  total_value: number;
  positions: {
    ticker: string;
    quantity: number;
    avg_cost: number;
    current_price: number | null;
    market_value: number;
    unrealized_pnl: number;
    pct_change: number;
  }[];
};

/** GET /api/portfolio's parsed body, after asserting the response is OK. */
export async function apiPortfolio(page: Page): Promise<PortfolioJson> {
  const res = await page.request.get("/api/portfolio");
  expect(res.ok()).toBeTruthy();
  return res.json();
}
