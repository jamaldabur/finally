/**
 * Scrollable interleaved message bubble list plus the transient "thinking"
 * indicator (03-UI-SPEC.md Layout & Interaction Contract). Renders
 * `message.content` as the bubble's entire text content and nothing else —
 * no outcome text, no status suffix, no concatenation with any action
 * field (PLAN.md §9 step 7, CHAT-04). Action badge rendering is Plan
 * 03-04's job and lives outside the bubble as a sibling; this component
 * has no knowledge of it. Text is rendered through JSX children only —
 * never through a raw-HTML injection prop — so React escapes any
 * LLM-authored markup (T-03-11).
 */

import type { ChatMessage } from "@/lib/types";

type ChatMessageListProps = {
  messages: ChatMessage[];
  isSending: boolean;
};

export function ChatMessageList({ messages, isSending }: ChatMessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-4">
      {messages.map((message) =>
        message.role === "user" ? (
          <div
            key={message.id}
            className="ml-auto bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 max-w-[85%] text-sm break-words whitespace-pre-wrap"
          >
            {message.content}
          </div>
        ) : (
          <div
            key={message.id}
            className="bg-terminal-panel border-l-2 border-accent-blue rounded-lg px-3 py-2 max-w-[85%] text-sm break-words whitespace-pre-wrap"
          >
            {message.content}
          </div>
        ),
      )}
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
