/**
 * Price-flash trigger and timing tests for `PriceCell` (Phase 6, TEST-04).
 *
 * Every case drives the real component through `render`/`rerender` with
 * distinct `price` props — never by inspecting a tick's `previous_price`
 * field, which stays stale-but-different forever after the first real move
 * (06-RESEARCH.md anti-pattern; `PriceCell.tsx`'s own docblock). The
 * component compares against its own `useRef` of the last rendered price,
 * so only a genuine prop-to-prop change can trigger a flash.
 */

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PriceCell } from "@/components/ui/PriceCell";

describe("PriceCell", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("renders the em-dash and no flash class when price is null", () => {
    render(<PriceCell price={null} direction={null} />);
    const span = screen.getByText("—");
    expect(span).not.toHaveClass("bg-green-500/30");
    expect(span).not.toHaveClass("bg-red-500/30");
  });

  it("renders the first non-null price with no flash", () => {
    render(<PriceCell price={190} direction={null} />);
    const span = screen.getByText("190.00");
    expect(span).not.toHaveClass("bg-green-500/30");
    expect(span).not.toHaveClass("bg-red-500/30");
  });

  it("adds the green flash class on a rise with direction up", () => {
    const { rerender } = render(<PriceCell price={190} direction="up" />);
    act(() => {
      rerender(<PriceCell price={191} direction="up" />);
    });
    expect(screen.getByText("191.00")).toHaveClass("bg-green-500/30");
  });

  it("adds the red flash class on a fall with direction down", () => {
    const { rerender } = render(<PriceCell price={190} direction="down" />);
    act(() => {
      rerender(<PriceCell price={189} direction="down" />);
    });
    expect(screen.getByText("189.00")).toHaveClass("bg-red-500/30");
  });

  it("does not re-trigger the flash on an unchanged-price heartbeat", () => {
    const { rerender } = render(<PriceCell price={190} direction="up" />);
    act(() => {
      rerender(<PriceCell price={191} direction="up" />);
    });
    // Let the first flash fully clear before the heartbeat re-render.
    act(() => {
      vi.advanceTimersByTime(500);
    });
    act(() => {
      // Same price, direction still "up" — a repeated heartbeat, not a
      // real change. Must not re-trigger the flash.
      rerender(<PriceCell price={191} direction="up" />);
    });
    const span = screen.getByText("191.00");
    expect(span).not.toHaveClass("bg-green-500/30");
    expect(span).not.toHaveClass("bg-red-500/30");
  });

  it("keeps the flash class present at 499ms and removes it at 500ms", () => {
    const { rerender } = render(<PriceCell price={190} direction="up" />);
    act(() => {
      rerender(<PriceCell price={191} direction="up" />);
    });
    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(screen.getByText("191.00")).toHaveClass("bg-green-500/30");

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByText("191.00")).not.toHaveClass("bg-green-500/30");
  });

  it("re-arms the flash timer on a second change, clearing the earlier one", () => {
    const { rerender } = render(<PriceCell price={190} direction="up" />);
    act(() => {
      rerender(<PriceCell price={191} direction="up" />);
    });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    act(() => {
      rerender(<PriceCell price={192} direction="up" />);
    });
    // 300ms (first change) + 200ms = 500ms total elapsed, but only 200ms
    // since the second change re-armed the timer — flash still present.
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.getByText("192.00")).toHaveClass("bg-green-500/30");

    // 300ms more brings total elapsed since the second change to 500ms.
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(screen.getByText("192.00")).not.toHaveClass("bg-green-500/30");
  });

  it("always carries the CSS fade transition classes", () => {
    render(<PriceCell price={190} direction={null} />);
    const span = screen.getByText("190.00");
    expect(span).toHaveClass("transition-colors");
    expect(span).toHaveClass("duration-500");
  });
});
