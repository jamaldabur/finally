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

/** The chat input, found by its placeholder text (ChatInput.tsx). */
export function chatInput(page: Page): Locator {
  return page.getByPlaceholder(/Ask about your portfolio/);
}

/**
 * Assistant chat bubbles (ChatMessageList.tsx) whose text starts with the
 * `[LLM_MOCK]` prefix — excludes the visually-identical "thinking" indicator
 * bubble, which carries no such text.
 */
function mockChatBubbles(page: Page): Locator {
  return page.locator(".border-l-2.border-accent-blue", {
    hasText: /^\[LLM_MOCK\]/,
  });
}

/**
 * Sends a chat message and waits for the reply: fills the input, presses
 * Enter, then waits until the number of `[LLM_MOCK]`-prefixed bubbles has
 * grown by one and the input is enabled and empty again — so callers never
 * race the response.
 */
export async function sendChat(page: Page, text: string): Promise<void> {
  // ChatProvider's mount-time GET /api/chat hydrate can still be in flight
  // here (found live: counting bubbles before it lands reads a stale 0,
  // then the hydrate's history AND this send's own reply both land at
  // once, jumping straight past `before + 1`). "Loading conversation…"
  // only renders while `messages === null`, so waiting for it to be gone
  // is a deterministic hydrate-complete barrier; it resolves immediately
  // if hydration already finished.
  await expect(page.getByText("Loading conversation…")).toHaveCount(0);

  const bubbles = mockChatBubbles(page);
  const before = await bubbles.count();

  const input = chatInput(page);
  await input.fill(text);
  // ChatInput.tsx's Send button is disabled while `text.trim() === ""`,
  // driven by the exact same React state Enter's keydown handler closes
  // over. Waiting for it to become enabled is a deterministic barrier
  // proving the typed value has actually landed in that state before Enter
  // fires — without it, under this page's constant ~500ms SSE-driven
  // re-render churn, Enter can race a still-in-flight state commit and
  // silently no-op (found live: input kept its typed text, no message
  // sent, no error — Rule 1 fix, not a fixed sleep).
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toBeEnabled();
  await input.press("Enter");

  await expect
    .poll(async () => bubbles.count(), { timeout: 20_000 })
    .toBe(before + 1);
  await expect(input).toBeEnabled();
  await expect(input).toHaveValue("");
}
