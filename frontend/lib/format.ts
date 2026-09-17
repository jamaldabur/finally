/**
 * Pure display formatting helpers, used everywhere a number the backend
 * already computed is rendered. These format values — they never round,
 * re-derive, or otherwise alter a value's magnitude. The backend
 * (compute_portfolio_view) is the sole source of truth for the underlying
 * numbers; see D-04.
 */

export function formatCurrency(n: number): string {
  return `$${n.toFixed(2)}`;
}

export function formatSignedCurrency(n: number): string {
  const sign = n >= 0 ? "+" : "-";
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

export function formatPercent(n: number): string {
  const sign = n >= 0 ? "+" : "-";
  return `${sign}${Math.abs(n).toFixed(2)}%`;
}
