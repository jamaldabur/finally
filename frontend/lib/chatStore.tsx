"use client";

/**
 * Chat context. Hydrates conversation history from `GET /api/chat` on
 * mount and sends new messages via `POST /api/chat` (03-PATTERNS.md,
 * mirrors portfolioStore.tsx's shape). `messages === null` means the mount
 * hydrate has not resolved yet (drives "Loading conversation…"); `[]` means
 * hydrated and empty (drives the empty state) — these two states must stay
 * distinguishable, so `messages` is typed `ChatMessage[] | null`, never
 * defaulting to `[]`.
 *
 * `hydrateError` and `sendError` are separate fields, not one shared error
 * field, because a failed hydrate and a failed send render in different
 * places with different copy (03-UI-SPEC.md).
 */

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fetchChatHistory, postChatMessage } from "./api";
import { usePortfolio } from "./portfolioStore";
import type { ChatMessage } from "./types";

type ChatStoreValue = {
  messages: ChatMessage[] | null;
  hydrateError: string | null;
  sendError: string | null;
  isSending: boolean;
  sendMessage: (text: string) => Promise<boolean>;
  watchlistRevision: number;
};

const ChatContext = createContext<ChatStoreValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [hydrateError, setHydrateError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [watchlistRevision, setWatchlistRevision] = useState(0);
  // Guards against a double-submit firing two concurrent POSTs — read
  // synchronously before any await, mirroring portfolioStore.tsx's
  // isRefreshingRef and TradeBar's isSubmitting guard.
  const isSendingRef = useRef(false);
  // Guards against the mount-only hydrate fetch resolving *after*
  // sendMessage() has already started (or finished) — without this, a fast
  // send racing a slow GET /api/chat can have the hydrate's setMessages(
  // history) clobber the in-flight/just-sent exchange with a stale
  // pre-send snapshot (WR-01). Once a send has started this session, the
  // hydrate must never overwrite state again.
  const hasSentRef = useRef(false);
  const { refresh: refreshPortfolio } = usePortfolio();

  // Mount-only hydrate, written as a self-contained async IIFE (not a call
  // through an exported callback) so eslint-plugin-react-hooks 7.1.1's
  // set-state-in-effect rule sees a self-contained fetch-and-set, matching
  // portfolioStore.tsx's mount effect.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { messages: history } = await fetchChatHistory();
        if (cancelled || hasSentRef.current) return;
        setMessages(history);
        setHydrateError(null);
      } catch {
        if (cancelled || hasSentRef.current) return;
        setHydrateError("Failed to load conversation history.");
        setMessages([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function sendMessage(text: string): Promise<boolean> {
    if (isSendingRef.current) return false;
    isSendingRef.current = true;
    hasSentRef.current = true;

    const trimmed = text.trim();
    const clientId = crypto.randomUUID();
    const optimisticUserMessage: ChatMessage = {
      id: clientId,
      role: "user",
      content: trimmed,
      trades: [],
      watchlist_changes: [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...(prev ?? []), optimisticUserMessage]);
    setIsSending(true);
    setSendError(null);

    try {
      const response = await postChatMessage({ message: trimmed });
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.message,
        trades: response.trades,
        watchlist_changes: response.watchlist_changes,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...(prev ?? []), assistantMessage]);

      if (response.trades.some((t) => t.outcome === "executed")) {
        await refreshPortfolio();
      }
      if (
        response.watchlist_changes.some((w) => w.outcome === "executed")
      ) {
        setWatchlistRevision((rev) => rev + 1);
      }

      return true;
    } catch (e) {
      setSendError(
        e instanceof Error
          ? e.message
          : "Message failed to send. Check your connection and try again.",
      );
      // Roll the optimistic user message back out so a retry can't
      // duplicate it — the input keeps the typed text for the user.
      setMessages((prev) => (prev ?? []).filter((m) => m.id !== clientId));
      return false;
    } finally {
      setIsSending(false);
      isSendingRef.current = false;
    }
  }

  return (
    <ChatContext.Provider
      value={{
        messages,
        hydrateError,
        sendError,
        isSending,
        sendMessage,
        watchlistRevision,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatStoreValue {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChat must be used within ChatProvider");
  }
  return ctx;
}
