"use client";

/**
 * Chat panel shell: hydrating / hydrate-error / empty / populated
 * branching, mirroring WatchlistPanel.tsx's structure (03-PATTERNS.md).
 * Branch order matters: `messages === null` (hydrating) is checked before
 * `hydrateError`, which is checked before the empty/populated split — a
 * failed hydrate still renders the input below it so the panel stays
 * usable (CHAT-05 degrades gracefully, it doesn't gate current use).
 *
 * The panel also owns its own width (expanded `w-80`, collapsed `w-12`) —
 * `frontend/app/page.tsx` renders it as a bare third flex child with no
 * wrapper div, since it now has two widths instead of one. The collapsed
 * flag lives in `useState` only, for the session — it is never written to
 * any browser persistence API, so a reload always returns to expanded
 * (03-UI-SPEC.md's session-only collapse assumption).
 */

import { useState } from "react";
import { useChat } from "@/lib/chatStore";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";

export function ChatPanel() {
  const { messages, hydrateError, sendError, isSending } = useChat();
  const [collapsed, setCollapsed] = useState(false);
  // Message count captured at the moment the panel was collapsed; the
  // unread dot shows while collapsed whenever the live count exceeds this.
  // Held in state (not a ref) because it is read during render to derive
  // `hasUnread` — the project's react-hooks/refs lint rule disallows
  // reading `ref.current` at render time.
  const [collapsedAtCount, setCollapsedAtCount] = useState(0);

  const messageCount = messages?.length ?? 0;
  const hasUnread =
    collapsed && messages !== null && messageCount > collapsedAtCount;

  function handleCollapse() {
    setCollapsedAtCount(messageCount);
    setCollapsed(true);
  }

  function handleExpand() {
    setCollapsedAtCount(messageCount);
    setCollapsed(false);
  }

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={handleExpand}
        className="flex h-full w-12 flex-shrink-0 flex-col items-center justify-center gap-2 bg-terminal-panel border-l border-terminal-border"
      >
        <span className="text-xs font-medium text-terminal-text-muted [writing-mode:vertical-rl]">
          Chat
        </span>
        {hasUnread && (
          <span
            className="h-2 w-2 rounded-full bg-accent-yellow"
            aria-hidden="true"
          />
        )}
      </button>
    );
  }

  return (
    <section className="flex h-full w-80 flex-shrink-0 flex-col rounded-lg border border-terminal-border bg-terminal-panel">
      <div className="flex items-center justify-between p-4 pb-2 text-sm font-medium text-terminal-text-muted">
        <h2>AI Assistant</h2>
        <button
          type="button"
          onClick={handleCollapse}
          className="text-xs text-terminal-text-muted hover:text-terminal-text"
        >
          Collapse
        </button>
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
