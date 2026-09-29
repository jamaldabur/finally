"use client";

/**
 * Shared connection-status primitive (D-12): green/yellow/red dot reading
 * the `ConnectionStatus` value derived in `lib/priceStore.tsx` from real
 * `EventSource` `onopen`/`onerror`/`readyState` transitions (D-06). Each
 * state carries a visible text label (not color alone) so the indicator is
 * readable, and each color class is a complete literal string so
 * Tailwind's scanner emits it.
 */

import type { ConnectionStatus } from "@/lib/priceStore";

const STATUS_CONFIG: Record<
  ConnectionStatus,
  { dotClass: string; label: string }
> = {
  connected: { dotClass: "bg-green-500", label: "Connected" },
  reconnecting: { dotClass: "bg-yellow-500", label: "Reconnecting" },
  disconnected: { dotClass: "bg-red-500", label: "Disconnected" },
};

export function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const { dotClass, label } = STATUS_CONFIG[status];

  return (
    <span
      className="flex items-center gap-2 text-xs text-terminal-text-muted"
      title={label}
    >
      <span
        className={`h-2.5 w-2.5 rounded-full ${dotClass}`}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
