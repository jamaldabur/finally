"use client";

/**
 * Chat panel shell: hydrating / hydrate-error / empty / populated
 * branching, mirroring WatchlistPanel.tsx's structure (03-PATTERNS.md).
 * Branch order matters: `messages === null` (hydrating) is checked before
 * `hydrateError`, which is checked before the empty/populated split — a
 * failed hydrate still renders the input below it so the panel stays
 * usable (CHAT-05 degrades gracefully, it doesn't gate current use).
 *
 * The component returns exactly ONE root element: a persistent width-
 * owning wrapper whose collapsed/expanded children are conditionally
 * rendered INSIDE it, never as two disjoint top-level `return`s. CSS
 * cannot interpolate a width across an unmount/remount, and the pre-03-05
 * version returned the rail and the panel from two separate `return`
 * statements — that structural split is precisely why no width animation
 * was possible and the toggle read as an instant, broken swap (G-03-1,
 * G-03-2; see 03-UI-SPEC.md Amendments). Now the wrapper owns `w-12`/
 * `w-80` plus the width transition, and the rail/section are both
 * `h-full w-full` children that simply fill whatever width it is given.
 *
 * The collapsed flag lives in `useState` only, for the session — it is
 * never written to any browser persistence API, so a reload always
 * returns to expanded (03-UI-SPEC.md's session-only collapse assumption).
 */

import { useState } from "react";
import { useChat } from "@/lib/chatStore";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";

// Directional chevrons for the collapse control (03-UI-SPEC.md Amendments:
// plain Unicode glyphs are sanctioned for directional affordances, same as
// the action-badge glyphs elsewhere — no icon-library import). Declared as
// named constants rather than inline literals so the no-icon-set rule
// stays auditable and the two directions cannot drift apart.
const EXPAND_GLYPH = "«"; // « LEFT-POINTING DOUBLE ANGLE QUOTATION MARK — points toward the panel opening
const COLLAPSE_GLYPH = "»"; // » RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK — points toward the panel closing

export function ChatPanel() {
  const { messages, hydrateError, sendError, isSending } = useChat();
  const [collapsed, setCollapsed] = useState(false);
  // Nullable unread baseline: the message count captured at the moment the
  // panel was collapsed, or null when no baseline is armed. A null
  // baseline can never produce a dot — that's the fix for the G-03-2 false
  // positive, where the old non-nullable baseline captured 0 when collapse
  // happened before the mount-time hydrate resolved, then flagged the
  // entire pre-existing conversation as "unread" once it landed. Held in
  // state (not a ref) because it is read during render to derive
  // `hasUnread` — the project's react-hooks/refs lint rule disallows
  // reading `ref.current` at render time.
  const [unreadBaseline, setUnreadBaseline] = useState<number | null>(null);

  const messageCount = messages?.length ?? 0;
  const hasUnread =
    collapsed && unreadBaseline !== null && messageCount > unreadBaseline;

  function handleCollapse() {
    // Only arm a baseline once hydration has actually resolved; collapsing
    // while `messages` is still null leaves the baseline null, so no dot
    // can ever fire for history that predates this collapse.
    setUnreadBaseline(messages !== null ? messageCount : null);
    setCollapsed(true);
  }

  function handleExpand() {
    setUnreadBaseline(null);
    setCollapsed(false);
  }

  return (
    <div
      className={`flex h-full flex-shrink-0 overflow-hidden transition-[width] duration-200 ease-out motion-reduce:transition-none ${collapsed ? "w-12" : "w-80"}`}
    >
      {collapsed ? (
        <button
          type="button"
          onClick={handleExpand}
          aria-expanded={false}
          aria-label="Expand chat panel"
          // Rail surface stays the panel token; the edge uses the
          // muted-text token instead of the border token, because
          // muted-text measures ~6.2:1 against the page background while
          // the border token measures 1.551:1 and the panel fill alone
          // measures 1.109:1 — both fail the WCAG 1.4.11 3:1 floor for
          // non-text UI components (03-UI-SPEC.md Amendments, G-03-2).
          className={[
            "flex h-full w-full flex-col items-center justify-center gap-2 rounded-lg border border-terminal-text-muted bg-terminal-panel",
            "hover:border-terminal-text",
            "hover:bg-terminal-border",
          ].join(" ")}
        >
          <span aria-hidden="true" className="text-terminal-text">
            {EXPAND_GLYPH}
          </span>
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
      ) : (
        <section className="flex h-full w-full flex-col rounded-lg border border-terminal-border bg-terminal-panel">
          <div className="flex items-center justify-between p-4 pb-2 text-sm font-medium text-terminal-text-muted">
            <h2>AI Assistant</h2>
            <button
              type="button"
              onClick={handleCollapse}
              aria-expanded={true}
              className="flex min-h-6 min-w-6 items-center gap-1 rounded border border-terminal-border px-2 py-1 text-xs text-terminal-text-muted hover:border-terminal-text hover:bg-terminal-border hover:text-terminal-text"
            >
              Collapse
              <span aria-hidden="true">{COLLAPSE_GLYPH}</span>
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
      )}
    </div>
  );
}
