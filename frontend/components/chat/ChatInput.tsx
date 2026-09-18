"use client";

/**
 * Controlled single-line chat input with Send button, mirroring
 * TradeBar.tsx's isSubmitting-disable + try/catch-free-await shape
 * (03-PATTERNS.md). No multi-line support this phase — a plain `<input>`,
 * not a `<textarea>`, per the UI-SPEC. On a failed send the typed text is
 * NOT cleared, so the user can retry without retyping (backstop truth in
 * 03-03-PLAN.md must_haves).
 */

import { useState, type KeyboardEvent } from "react";
import { useChat } from "@/lib/chatStore";

export function ChatInput() {
  const [text, setText] = useState("");
  const { isSending, sendMessage } = useChat();

  async function submit() {
    if (isSending) return;
    const trimmed = text.trim();
    if (!trimmed) return;
    const sent = await sendMessage(trimmed);
    if (sent) {
      setText("");
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      void submit();
    }
  }

  return (
    <div className="border-t border-terminal-border p-3 flex gap-2">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your portfolio, or tell FinAlly to trade…"
        disabled={isSending}
        className="flex-1 rounded border border-terminal-border bg-terminal-bg px-2 py-1 text-sm text-terminal-text disabled:opacity-50"
      />
      <button
        type="button"
        onClick={() => void submit()}
        disabled={isSending || text.trim() === ""}
        className="rounded bg-accent-purple px-3 py-1 text-sm font-medium text-terminal-text disabled:opacity-50"
      >
        Send
      </button>
    </div>
  );
}
