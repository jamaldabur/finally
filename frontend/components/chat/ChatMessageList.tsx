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
 */

import { ActionBadge } from "./ActionBadge";
import type { ChatMessage } from "@/lib/types";

type ChatMessageListProps = {
  messages: ChatMessage[];
  isSending: boolean;
};

export function ChatMessageList({ messages, isSending }: ChatMessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-4">
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
  );
}
