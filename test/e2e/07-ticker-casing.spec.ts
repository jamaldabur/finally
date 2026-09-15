import { test, expect } from "@playwright/test";

// Regression coverage for a casing inconsistency the LLM engineer flagged:
// POST /api/watchlist normalizes ticker casing (`.strip().upper()` in
// backend/app/watchlist/service.py) before validating, but
// POST /api/portfolio/trade -> execute_trade previously did not — a
// lowercase ticker like "aapl" would look up nothing in the (uppercase-only)
// price cache and get spuriously rejected with "no price available for
// aapl". backend-engineer fixed execute_trade to normalize
// (backend/app/portfolio/service.py:73) the same way the watchlist path
// does. Both routes are now checked for consistent normalization.
test.describe("ticker casing consistency", () => {
  test("watchlist add normalizes case", async ({ request }) => {
    const res = await request.post("/api/watchlist", { data: { ticker: "msft" } });
    // MSFT is already on the default watchlist, so a normalized duplicate
    // add correctly reports "already on watchlist" — proving the ticker WAS
    // uppercased before the duplicate check ran.
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.detail).toMatch(/already on watchlist/i);
  });

  test("trade with a lowercase ticker executes against the uppercase symbol", async ({ request }) => {
    const res = await request.post("/api/portfolio/trade", {
      data: { ticker: "aapl", quantity: 1, side: "buy" },
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.ticker).toBe("AAPL");
    expect(body.side).toBe("buy");
    expect(body.quantity).toBe(1);
    expect(body.price).toBeGreaterThan(0);

    // The fill really landed against the normalized AAPL position, not a
    // separate lowercase-keyed one.
    const portfolioRes = await request.get("/api/portfolio");
    const portfolio = await portfolioRes.json();
    const aaplPosition = portfolio.positions.find((p: { ticker: string }) => p.ticker === "AAPL");
    expect(aaplPosition).toBeTruthy();
    expect(aaplPosition.quantity).toBeGreaterThanOrEqual(1);
  });
});
