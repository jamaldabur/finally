import type { ConnectionStatus } from "@/lib/types";

const COLORS: Record<ConnectionStatus, string> = {
  connected: "bg-up",
  reconnecting: "bg-accent-yellow",
  disconnected: "bg-down",
};

const LABELS: Record<ConnectionStatus, string> = {
  connected: "Connected",
  reconnecting: "Reconnecting",
  disconnected: "Disconnected",
};

export default function ConnectionDot({ status }: { status: ConnectionStatus }) {
  return (
    <div className="flex items-center gap-2" data-testid="connection-dot" data-status={status}>
      <span
        className={`h-2.5 w-2.5 rounded-full ${COLORS[status]} ${
          status !== "disconnected" ? "animate-pulse" : ""
        }`}
      />
      <span className="text-xs text-muted">{LABELS[status]}</span>
    </div>
  );
}
