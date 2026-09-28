/**
 * Per-outcome rendering tests for `ActionBadge` (Phase 6, TEST-04). Pure
 * rendering — no providers, no fetch, no stores — driven with typed
 * `TradeAction` / `WatchlistAction` props directly, mirroring the escaping
 * contract `ActionBadge.tsx`'s own docblock relies on (T-03-16).
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActionBadge } from "./ActionBadge";
import type { TradeAction, WatchlistAction } from "@/lib/types";

function trade(overrides: Partial<TradeAction> = {}): TradeAction {
  return {
    ticker: "AAPL",
    side: "buy",
    quantity: 2,
    price: 190,
    outcome: "executed",
    reason: null,
    ...overrides,
  };
}

function watchlistChange(
  overrides: Partial<WatchlistAction> = {},
): WatchlistAction {
  return {
    ticker: "PYPL",
    action: "add",
    outcome: "executed",
    reason: null,
    ...overrides,
  };
}

describe("ActionBadge", () => {
  it("renders an executed buy with its fill price and no alert role", () => {
    render(<ActionBadge kind="trade" action={trade()} />);

    const label = screen.getByText("✓ buy 2 AAPL @ $190.00");
    expect(label).toBeInTheDocument();
    expect(label.closest("div")).toHaveClass("text-gain");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders an executed sell with a null price and never the word null", () => {
    render(
      <ActionBadge
        kind="trade"
        action={trade({ side: "sell", quantity: 1, price: null })}
      />,
    );

    expect(screen.getByText("✓ sell 1 AAPL")).toBeInTheDocument();
    expect(screen.queryByText(/null/i)).not.toBeInTheDocument();
  });

  it("renders an errored buy with role alert and the verbatim reason", () => {
    render(
      <ActionBadge
        kind="trade"
        action={trade({
          quantity: 1000,
          price: null,
          outcome: "error",
          reason: "Insufficient cash: need $190000.00, have $10000.00",
        })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("✕ buy 1000 AAPL");
    expect(alert).toHaveTextContent(
      "Insufficient cash: need $190000.00, have $10000.00",
    );
  });

  it("renders an errored trade with a null reason and no dash separator", () => {
    render(
      <ActionBadge
        kind="trade"
        action={trade({ outcome: "error", price: null, reason: null })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("✕ buy 2 AAPL");
    expect(alert.textContent).not.toContain("—");
  });

  it("renders an executed watchlist add", () => {
    render(<ActionBadge kind="watchlist" action={watchlistChange()} />);

    expect(
      screen.getByText("✓ Added PYPL to watchlist"),
    ).toBeInTheDocument();
  });

  it("renders an executed watchlist remove", () => {
    render(
      <ActionBadge
        kind="watchlist"
        action={watchlistChange({ action: "remove" })}
      />,
    );

    expect(
      screen.getByText("✓ Removed PYPL from watchlist"),
    ).toBeInTheDocument();
  });

  it("renders an errored watchlist add with its reason", () => {
    render(
      <ActionBadge
        kind="watchlist"
        action={watchlistChange({
          ticker: "ZZZZ",
          outcome: "error",
          reason: "Unknown ticker: ZZZZ",
        })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("✕ Add ZZZZ");
    expect(alert).toHaveTextContent("Unknown ticker: ZZZZ");
  });

  it("renders an errored watchlist remove with its reason", () => {
    render(
      <ActionBadge
        kind="watchlist"
        action={watchlistChange({
          ticker: "ZZZZ",
          action: "remove",
          outcome: "error",
          reason: "Unknown ticker: ZZZZ",
        })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("✕ Remove ZZZZ");
    expect(alert).toHaveTextContent("Unknown ticker: ZZZZ");
  });

  it("renders markup inside a reason as literal text, creating no element", () => {
    render(
      <ActionBadge
        kind="trade"
        action={trade({
          outcome: "error",
          price: null,
          reason: "Rejected: <b>bold</b> ticker",
        })}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Rejected: <b>bold</b> ticker");
    expect(alert.querySelector("b")).toBeNull();
  });
});
