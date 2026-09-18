/**
 * Scrollable interleaved message bubble list plus the transient "thinking"
 * indicator (03-UI-SPEC.md Layout & Interaction Contract). Renders
 * `message.content` as the bubble's entire text content and nothing else —
 * no outcome text, no status suffix, no concatenation with any action
 * field (PLAN.md §9 step 7, CHAT-04). Text is rendered through JSX children
 * only — never through a raw-HTML injection prop — so React escapes any
 * LLM-authored markup (T-03-11).
 *
 * Every assistant message's action outcomes render as an `ActionBadge`
 * stack directly below the bubble, as its sibling (never a child) — one
 * badge per `trades[]` item followed by one per `watchlist_changes[]` item,
 * in exactly the order the backend returned them. A message with no actions
 * renders no badge-stack element at all.
 *
 * Auto-scroll: pinned-to-bottom state is derived from the scroll container's
 * own scroll position (`scrollHeight - scrollTop - clientHeight <= 40`), not
 * from any prop. While pinned, new messages/sending-state changes scroll the
 * container to the bottom automatically; once the user scrolls up, new
 * activity instead surfaces the "New messages ↓" pill rather than yanking
 * their view back down.
 */

import { useEffect, useRef, useState } from "react";
import { ActionBadge } from "./ActionBadge";
import type { ChatMessage } from "@/lib/types";

type ChatMessageListProps = {
  messages: ChatMessage[];
  isSending: boolean;
};

export function ChatMessageList({ messages, isSending }: ChatMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pinned, setPinned] = useState(true);
  const [hasNewActivity, setHasNewActivity] = useState(false);
  // Previous (message count, sending-flag) pair, used only to detect "new
  // activity arrived" during render — React's "adjusting state when a prop
  // changes" pattern (calling setState conditionally during render, guarded
  // so it only fires once per change) — rather than a useEffect whose body
  // would just call setState synchronously
  // (react-hooks/set-state-in-effect).
  const [prevActivityKey, setPrevActivityKey] = useState({
    length: messages.length,
    isSending,
  });

  const activityChanged =
    prevActivityKey.length !== messages.length ||
    prevActivityKey.isSending !== isSending;

  if (activityChanged) {
    setPrevActivityKey({ length: messages.length, isSending });
    if (!pinned) {
      setHasNewActivity(true);
    }
  }

  // Once the user is back at the bottom, clear the pill — same
  // during-render derived-state pattern as above.
  if (pinned && hasNewActivity) {
    setHasNewActivity(false);
  }

  function scrollToBottom() {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }

  function handleScroll() {
    const el = containerRef.current;
    if (!el) return;
    setPinned(el.scrollHeight - el.scrollTop - el.clientHeight <= 40);
  }

  // Pure DOM side effect (no setState call) — scroll to the bottom
  // whenever pinned and new content arrives.
  useEffect(() => {
    if (pinned) {
      scrollToBottom();
    }
  }, [messages.length, isSending, pinned]);

  function handlePillClick() {
    scrollToBottom();
    setPinned(true);
    setHasNewActivity(false);
  }

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto flex flex-col gap-3 p-4"
      >
        {messages.map((message) => {
        if (message.role === "user") {
          return (
            <div
              key={message.id}
              className="ml-auto bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 max-w-[85%] text-sm break-words whitespace-pre-wrap"
            >
              {message.content}
            </div>
          );
        }

        const actionCount =
          message.trades.length + message.watchlist_changes.length;

        return (
          <div key={message.id} className="flex max-w-[85%] flex-col gap-1">
            <div className="bg-terminal-panel border-l-2 border-accent-blue rounded-lg px-3 py-2 text-sm break-words whitespace-pre-wrap">
              {message.content}
            </div>
            {actionCount > 0 && (
              <div className="flex flex-col gap-1">
                {message.trades.map((trade, index) => (
                  <ActionBadge
                    key={`${message.id}-trade-${index}`}
                    kind="trade"
                    action={trade}
                  />
                ))}
                {message.watchlist_changes.map((change, index) => (
                  <ActionBadge
                    key={`${message.id}-watchlist-${index}`}
                    kind="watchlist"
                    action={change}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
      {isSending && (
        <div className="bg-terminal-panel border-l-2 border-accent-blue rounded-lg px-3 py-2 max-w-[85%] flex gap-1 items-center">
          <span className="sr-only" aria-live="polite">
            FinAlly is thinking
          </span>
          <span
            className="h-1.5 w-1.5 rounded-full bg-accent-blue animate-pulse [animation-delay:0ms]"
            aria-hidden="true"
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-accent-blue animate-pulse [animation-delay:150ms]"
            aria-hidden="true"
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-accent-blue animate-pulse [animation-delay:300ms]"
            aria-hidden="true"
          />
        </div>
      )}
      </div>
      {hasNewActivity && (
        <button
          type="button"
          onClick={handlePillClick}
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-terminal-border bg-terminal-panel px-3 py-1 text-xs text-terminal-text"
        >
          New messages ↓
        </button>
      )}
    </div>
  );
}
