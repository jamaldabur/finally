import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ConnectionDot from "@/components/ConnectionDot";

describe("ConnectionDot", () => {
  it.each([
    ["connected", "Connected"],
    ["reconnecting", "Reconnecting"],
    ["disconnected", "Disconnected"],
  ] as const)("labels %s as %s", (status, label) => {
    render(<ConnectionDot status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
