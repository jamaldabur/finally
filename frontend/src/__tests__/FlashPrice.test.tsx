import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import FlashPrice from "@/components/FlashPrice";

const fmt = (v: number) => `$${v}`;

describe("FlashPrice", () => {
  it("does not flash on initial render with an unchanged direction", () => {
    const { container } = render(<FlashPrice price={100} direction="unchanged" format={fmt} />);
    const el = container.querySelector("span");
    expect(el?.className).not.toMatch(/flash-(up|down)/);
  });

  it("flashes green on a genuine upward price change", () => {
    const { container, rerender } = render(<FlashPrice price={100} direction="unchanged" format={fmt} />);
    rerender(<FlashPrice price={105} direction="up" format={fmt} />);
    const el = container.querySelector("span");
    expect(el?.className).toMatch(/flash-up/);
  });

  it("flashes red on a genuine downward price change", () => {
    const { container, rerender } = render(<FlashPrice price={100} direction="unchanged" format={fmt} />);
    rerender(<FlashPrice price={95} direction="down" format={fmt} />);
    const el = container.querySelector("span");
    expect(el?.className).toMatch(/flash-down/);
  });

  it("does not re-trigger the flash animation on a repeated unchanged heartbeat", () => {
    const { container, rerender } = render(<FlashPrice price={100} direction="unchanged" format={fmt} />);
    rerender(<FlashPrice price={105} direction="up" format={fmt} />);
    const afterChange = container.querySelector("span");

    // Same price re-sent as an "unchanged" heartbeat, as the backend does every ~500ms.
    rerender(<FlashPrice price={105} direction="unchanged" format={fmt} />);
    const afterHeartbeat = container.querySelector("span");

    expect(afterHeartbeat).toBe(afterChange); // same DOM node: animation was not restarted
  });

  it("renders the formatted price", () => {
    const { getByText } = render(<FlashPrice price={42} direction="unchanged" format={fmt} />);
    expect(getByText("$42")).toBeInTheDocument();
  });
});
