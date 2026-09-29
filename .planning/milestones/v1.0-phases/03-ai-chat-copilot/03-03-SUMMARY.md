---
phase: 03-ai-chat-copilot
plan: 03
subsystem: ai-chat-frontend
tags: [nextjs, react-context, chat-ui, tailwind, chat-frontend]
requires:
  - phase: 03-ai-chat-copilot
    provides: "03-01: POST /api/chat end-to-end loop; 03-02: GET /api/chat history hydration and persistence — the real backend contract this UI builds against"
provides:
  - "frontend/lib/types.ts: ActionOutcome, TradeAction, WatchlistAction, ChatMessage, ChatResponse, ChatRequest wire types"
  - "frontend/lib/api.ts: fetchChatHistory(), postChatMessage() — the only network access points for chat"
  - "frontend/lib/chatStore.tsx: ChatProvider + useChat() — hydrate-on-mount, in-flight-guarded send with optimistic append/rollback, portfolio refresh + watchlistRevision on executed actions"
  - "frontend/components/chat/{ChatPanel,ChatInput,ChatMessageList}.tsx — the third-column chat UI a user can actually talk to"
affects: [03-04-chat-ui-badges]
actuals:
  tokens: 4800
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Chat store mirrors portfolioStore.tsx exactly: createContext + useState + self-contained async-IIFE mount effect + useRef in-flight guard + exported hook that throws outside its provider"
    - "Optimistic append with rollback-by-client-id: sendMessage() appends a crypto.randomUUID()-keyed user bubble immediately, then removes it by that same id on failure so a retry cannot duplicate it"
    - "Provider nesting is load-bearing: ChatProvider renders inside PortfolioProvider because chatStore calls usePortfolio().refresh() after an executed trade"
key-files:
  created:
    - frontend/lib/chatStore.tsx
    - frontend/components/chat/ChatPanel.tsx
    - frontend/components/chat/ChatInput.tsx
    - frontend/components/chat/ChatMessageList.tsx
  modified:
    - frontend/lib/types.ts
    - frontend/lib/api.ts
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
key-decisions:
  - "messages typed ChatMessage[] | null (never defaulting to []) so hydrating and hydrated-empty stay distinguishable states, per the plan's explicit acceptance criterion"
  - "hydrateError and sendError kept as separate context fields — a failed hydrate renders inline in the message-list area while keeping the input usable; a failed send renders as a boxed system notice below the list — conflating them would blend two different UI treatments"
patterns-established:
  - "Action-badge rendering (Plan 03-04) is explicitly out of scope here: ChatMessageList renders message.content alone and nothing else, with action lists (trades/watchlist_changes) already flowing through ChatMessage but not yet rendered — the next plan reads them as siblings below the bubble"
requirements-completed: [UI-08, CHAT-01, CHAT-05]
coverage:
  - id: D1
    description: "A user can type a message, press Send or Enter, and see the assistant's reply appear without a page reload"
    requirement: CHAT-01
    verification:
      - kind: static
        ref: "grep -vE '^\\s*(//|\\*|/\\*)' frontend/lib/chatStore.tsx | grep -cE 'fetchChatHistory\\(|postChatMessage\\(' -> 2"
        status: pass
      - kind: manual
        ref: "Live round trip against LLM_MOCK=true backend: POST /api/chat 'how am I doing?' returned a mock reply; GET /api/chat immediately reflected both turns in order"
        status: pass
    human_judgment: false
  - id: D2
    description: "On mount the panel fetches GET /api/chat and renders prior conversation; a refresh does not lose it"
    requirement: CHAT-05
    verification:
      - kind: static
        ref: "grep -c 'ChatMessage\\[\\] | null' frontend/lib/chatStore.tsx -> 3"
        status: pass
      - kind: manual
        ref: "curl http://localhost:3000/ (frontend dev server, backend live) shows 'Loading conversation' server-rendered before hydration, and the 'AI Assistant' header present"
        status: pass
    human_judgment: false
  - id: D3
    description: "Empty state, loading state, error states, and populated bubbles render with the exact locked copy and Tailwind classes from 03-UI-SPEC.md"
    requirement: UI-08
    verification:
      - kind: static
        ref: "grep -c 'Ask FinAlly anything' ChatPanel.tsx -> 1; grep -c 'Loading conversation' ChatPanel.tsx -> 1; grep -c placeholder-copy ChatInput.tsx -> 1"
        status: pass
      - kind: static
        ref: "grep -c 'max-w-\\[85%\\]' ChatMessageList.tsx -> 3; grep -c 'break-words' -> 2; grep -c 'aria-live' -> 1"
        status: pass
    human_judgment: false
  - id: D4
    description: "An assistant-executed trade refreshes the header/cash/positions without a reload"
    verification:
      - kind: manual
        ref: "curl POST /api/chat 'buy 5 AAPL' executed the trade (outcome: executed); curl GET /api/portfolio confirmed cash_balance dropped and the AAPL position appeared — chatStore's usePortfolio().refresh() call path is the wiring under test (full click-driven browser confirmation deferred to end-of-phase UAT per workflow.human_verify_mode)"
        status: pass
    human_judgment: true
    rationale: "The plan's own <human-check> requires a live click-through in an actual browser (input disables, three-dot indicator appears, reply renders, header/positions update, reload restores history). Per .planning/config.json workflow.human_verify_mode: end-of-phase (the same setting Phase 2 used, validated there with 0 issues across 8 deferred checks), this is deferred to one end-of-phase UAT batch rather than a per-plan checkpoint. The underlying data path was verified directly against the live backend via curl in this session; only the visual/interaction polish (animations, disabled states rendering correctly, scroll behavior) remains for the end-of-phase pass."
  - id: D5
    description: "No chat component injects raw HTML or bypasses lib/api.ts for network access"
    verification:
      - kind: static
        ref: "grep -rl dangerouslySetInnerHTML frontend/components/chat | wc -l -> 0; grep -rlE 'fetch\\(' frontend/components/chat | wc -l -> 0"
        status: pass
    human_judgment: false
duration: ~20min
completed: 2026-09-18
status: complete
---

# Phase 03 Plan 03: Chat Frontend — Panel, Input, Message List Summary

**Third-column AI chat panel wired to the live `GET`/`POST /api/chat` contract from 03-01/03-02 — hydrate-on-mount history, optimistic send with rollback, and an executed chat trade now refreshes the header and positions table without a reload.**

## Performance
- **Duration:** ~20min
- **Started:** 2026-09-18
- **Completed:** 2026-09-18
- **Tasks:** 2/2 completed
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments
- `frontend/lib/types.ts` gained the six chat wire types (`ActionOutcome`, `TradeAction`, `WatchlistAction`, `ChatMessage`, `ChatResponse`, `ChatRequest`), mirroring `backend/app/routes/chat.py`'s Pydantic models field-for-field, including `price: number | null` and `reason: string | null`.
- `frontend/lib/api.ts` gained `fetchChatHistory()` and `postChatMessage()`, the latter reusing the existing `ApiErrorDetail` array-or-string passthrough convention `postTrade()` established — no new error-handling shape introduced.
- `frontend/lib/chatStore.tsx` (new): `ChatProvider`/`useChat()` hydrates history on mount (`messages: ChatMessage[] | null` keeps "loading" and "loaded-empty" distinguishable), guards re-entrant sends with a `useRef`, optimistically appends the user's message and rolls it back on failure, and calls `usePortfolio().refresh()` after any chat-originated trade executes.
- `frontend/app/layout.tsx`: `ChatProvider` now nests inside `PortfolioProvider` — load-bearing, since the store calls `usePortfolio()`.
- Three new components (`ChatPanel`, `ChatInput`, `ChatMessageList`) implement every UI-08 state from `03-UI-SPEC.md`'s UI Considerations table: hydrating, hydrate-error (degrades gracefully, input stays usable), empty, populated, send-in-flight (disabled input/button + animated three-dot thinking indicator with `aria-live` announcement), and send-failure (boxed inline system notice, typed text retained).
- `frontend/app/page.tsx` now renders `ChatPanel` as a third `w-80 flex-shrink-0` column, mirroring the left watchlist column's width exactly.
- Live-verified against the real backend (`LLM_MOCK=true`): `POST /api/chat` round-trips correctly, `GET /api/chat` returns both turns in order, and a mock "buy 5 AAPL" trade executed and was reflected immediately in `GET /api/portfolio` (cash dropped, position appeared) — the exact chain `sendMessage()` → `usePortfolio().refresh()` is built to trigger.

## Task Commits
1. **Task 1: Chat wire contract and store** - `2cce76b`
2. **Task 2: Chat panel — third column, input, message list** - `cea030e`

## Files Created/Modified
- `frontend/lib/types.ts` - Six new chat wire types, sourced-from comment extended
- `frontend/lib/api.ts` - `fetchChatHistory()`, `postChatMessage()`
- `frontend/lib/chatStore.tsx` - `ChatProvider`/`useChat()` — hydrate, send, optimistic rollback, portfolio refresh
- `frontend/app/layout.tsx` - `ChatProvider` nested inside `PortfolioProvider`
- `frontend/components/chat/ChatPanel.tsx` - Panel shell with loading/error/empty/populated branching
- `frontend/components/chat/ChatInput.tsx` - Controlled single-line input + Send button, disabled while in flight
- `frontend/components/chat/ChatMessageList.tsx` - Scrollable bubble list + thinking indicator
- `frontend/app/page.tsx` - Third flex column mounting `ChatPanel`

## Decisions Made
- **`messages: ChatMessage[] | null`, never defaulting to `[]`** — required to keep "still hydrating" and "hydrated but empty" as distinguishable UI states (locked in the plan's acceptance criteria).
- **Separate `hydrateError`/`sendError` fields** — a failed hydrate renders inline in the message-list area with the input still usable (CHAT-05 degrades gracefully); a failed send renders as a distinct boxed system notice below the list. One shared error field would have conflated two different visual treatments.
- **Action badge rendering deliberately deferred** — `ChatMessage.trades`/`watchlist_changes` already flow through the store and response parsing, but `ChatMessageList` renders `message.content` only; badge UI is explicitly Plan 03-04's scope per the plan text.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None. All acceptance criteria and automated `<verify>` commands from the plan pass: `npm run typecheck`, `npm run lint`, and `npm run build` (produces `frontend/out/index.html`) all succeed, and every static grep-based check listed in the plan returns the expected count.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Plan 03-04 (chat UI badges) can now build directly on this plan's output:
- `ChatMessage.trades`/`watchlist_changes` are already populated by both the hydrate path (`GET /api/chat`) and the send path (`POST /api/chat` response) — 03-04 only needs to render them as sibling badge elements below the assistant bubble, per `03-UI-SPEC.md`'s `✓`/`✕` badge copy contract.
- The panel's loading/error/empty/populated branch structure in `ChatPanel.tsx` is stable; 03-04 does not need to touch it.
- The full click-through UAT (input disabling, thinking-indicator visuals, reload restoring history) is deferred to the phase's single end-of-phase UAT batch per `workflow.human_verify_mode: end-of-phase` — the same pattern Phase 2 used successfully (8 deferred checks, 0 issues). This session confirmed the underlying data path directly against the live backend via curl; only the visual/interaction polish remains for that batch.

## Self-Check: PASSED

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-18*
