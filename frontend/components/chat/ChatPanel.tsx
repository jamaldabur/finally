"use client";

/**
 * Chat panel shell: hydrating / hydrate-error / empty / populated
 * branching, mirroring WatchlistPanel.tsx's structure (03-PATTERNS.md).
 * Branch order matters: `messages === null` (hydrating) is checked before
 * `hydrateError`, which is checked before the empty/populated split — a
 * failed hydrate still renders the input below it so the panel stays
 * usable (CHAT-05 degrades gracefully, it doesn't gate current use).
 */

import { useChat } from "@/lib/chatStore";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";

export function ChatPanel() {
  const { messages, hydrateError, sendError, isSending } = useChat();

  return (
    <section className="flex h-full flex-col rounded-lg border border-terminal-border bg-terminal-panel">
      <div className="flex items-center justify-between p-4 pb-2 text-sm font-medium text-terminal-text-muted">
        <h2>AI Assistant</h2>
      </div>

      {messages === null && (
        <p className="p-4 text-sm text-terminal-text-muted">
          Loading conversation&hellip;
        </p>
      )}

      {messages !== null && hydrateError && (
        <p className="p-4 text-sm text-red-400" role="alert">
          {hydrateError}
        </p>
      )}

      {messages !== null && !hydrateError && messages.length === 0 && (
        <div className="p-4 flex flex-col gap-1">
          <h3 className="text-sm font-medium text-terminal-text">
            Ask FinAlly anything
          </h3>
          <p className="text-sm text-terminal-text-muted">
            Get portfolio analysis, or ask it to buy, sell, or update your
            watchlist.
          </p>
        </div>
      )}

      {messages !== null && !hydrateError && messages.length > 0 && (
        <ChatMessageList messages={messages} isSending={isSending} />
      )}

      {sendError && (
        <p
          className="mx-4 mb-2 rounded border border-terminal-border px-3 py-2 text-center text-sm text-red-400"
          role="alert"
        >
          {sendError}
        </p>
      )}

      <ChatInput />
    </section>
  );
}
