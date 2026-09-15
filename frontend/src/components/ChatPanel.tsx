"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, getChatHistory, streamChatMessage } from "@/lib/api";
import type { ChatActions, ChatMessage, TradeAction, WatchlistChangeAction } from "@/lib/types";

// Runtime-only fields layered on top of the persisted ChatMessage shape while a
// reply is actively streaming in; history rows from GET /api/chat never set these.
interface DisplayMessage extends ChatMessage {
  streaming?: boolean;
  interrupted?: boolean;
}

function ActionBadge({ label, status, reason }: { label: string; status: "executed" | "error"; reason?: string | null }) {
  return (
    <span
      title={reason ?? undefined}
      className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full mr-1.5 mb-1.5 ${
        status === "executed" ? "bg-up/15 text-up" : "bg-down/15 text-down"
      }`}
    >
      {status === "executed" ? "✓" : "✗"} {label}
    </span>
  );
}

function tradeLabel(t: TradeAction): string {
  return `${t.side === "buy" ? "Buy" : "Sell"} ${t.quantity} ${t.ticker}`;
}

function watchlistLabel(w: WatchlistChangeAction): string {
  return `${w.action === "add" ? "Add" : "Remove"} ${w.ticker}`;
}

function ActionBadges({ actions }: { actions: ChatActions | null }) {
  if (!actions || (!actions.trades.length && !actions.watchlist_changes.length)) return null;
  return (
    <div className="mt-1 max-w-[90%]">
      {actions.trades.map((t, i) => (
        <ActionBadge key={`t-${i}`} label={tradeLabel(t)} status={t.status} reason={t.reason} />
      ))}
      {actions.watchlist_changes.map((w, i) => (
        <ActionBadge key={`w-${i}`} label={watchlistLabel(w)} status={w.status} reason={w.reason} />
      ))}
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-0.5" data-testid="chat-loading">
      <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" />
    </span>
  );
}

export default function ChatPanel({ onActionExecuted }: { onActionExecuted: () => void }) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatHistory()
      .then((history) => {
        // Prepend rather than replace: if the user already sent a message before
        // this resolved, history always predates it chronologically — replacing
        // would silently wipe out the in-progress conversation.
        setMessages((prev) => [...history, ...prev]);
      })
      .catch(() => {
        // Chat backend may not be up yet; leave history empty rather than block the UI.
      });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    const userMessage: DisplayMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
      actions: null,
      created_at: new Date().toISOString(),
    };
    const assistantId = `local-${Date.now()}-assistant`;
    const assistantPlaceholder: DisplayMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      actions: null,
      created_at: new Date().toISOString(),
      streaming: true,
    };
    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setInput("");
    setStreaming(true);

    const updateAssistant = (patch: Partial<DisplayMessage> | ((m: DisplayMessage) => Partial<DisplayMessage>)) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) } : m))
      );
    };

    try {
      await streamChatMessage(text, {
        onDelta: (chunk) => updateAssistant((m) => ({ content: m.content + chunk })),
        onDone: (result) => {
          updateAssistant({
            content: result.message,
            actions: { trades: result.trades, watchlist_changes: result.watchlist_changes },
            streaming: false,
          });
          if (result.trades.some((t) => t.status === "executed") || result.watchlist_changes.some((w) => w.status === "executed")) {
            onActionExecuted();
          }
        },
      });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Connection interrupted";
      updateAssistant((m) => ({
        content: m.content || `Sorry, something went wrong: ${message}`,
        streaming: false,
        interrupted: true,
      }));
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-4 pt-3.5 pb-3">
        <h2 className="text-sm font-semibold text-foreground">AI assistant</h2>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-2 space-y-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted leading-relaxed">
            Ask FinAlly about your portfolio, or tell it to trade for you — try &ldquo;buy 5 AAPL&rdquo; or &ldquo;how am I doing today?&rdquo;
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
            <span className="text-xs text-muted mb-1 px-1">{m.role === "user" ? "You" : "FinAlly"}</span>
            <div
              className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user" ? "bg-accent-blue text-white" : "bg-surface-raised text-foreground"
              }`}
            >
              {m.streaming && m.content === "" ? (
                <TypingDots />
              ) : (
                <>
                  {m.content}
                  {m.streaming && (
                    <span className="inline-block w-1.5 h-3.5 bg-current opacity-60 ml-0.5 align-middle animate-pulse" />
                  )}
                </>
              )}
            </div>
            {m.interrupted && (
              <span className="text-xs text-down mt-1 px-1">⚠ Connection interrupted — response may be incomplete.</span>
            )}
            <ActionBadges actions={m.actions} />
          </div>
        ))}
      </div>

      <form onSubmit={handleSend} className="flex gap-2 px-4 pt-2 pb-3.5">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message FinAlly…"
          className="flex-1 min-w-0 bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm transition-colors focus:outline-none focus:border-accent-blue focus-visible:ring-2 focus-visible:ring-accent-blue/40"
        />
        <button
          type="submit"
          disabled={streaming}
          className="px-4 py-2 text-sm font-semibold rounded-lg bg-accent-purple text-white transition-colors hover:bg-accent-purple/90 disabled:opacity-50 disabled:hover:bg-accent-purple focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
        >
          Send
        </button>
      </form>
    </div>
  );
}
