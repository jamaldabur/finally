---
phase: 03-ai-chat-copilot
plan: 04
subsystem: ai-chat-frontend
tags: [nextjs, react, chat-ui, tailwind, action-outcome, collapse-panel, sse-watchlist-sync]
requires:
  - phase: 03-ai-chat-copilot
    provides: "03-03: chat wire contract, ChatProvider/useChat store (trades/watchlist_changes already flowing through ChatMessage, watchlistRevision field), ChatPanel/ChatMessageList shells"
provides:
  - "frontend/components/chat/ActionBadge.tsx: one honest executed/error pill per trade or watchlist action, driven solely by the backend's outcome field"
  - "Badge stacks rendered as siblings below assistant bubbles in ChatMessageList, in exact backend order"
  - "ChatPanel collapse rail (w-12) with session-only collapsed state and an accent-yellow unread indicator"
  - "ChatMessageList auto-scroll while pinned to bottom, plus a 'New messages' scroll-to-latest pill when scrolled up"
  - "WatchlistPanel re-fetches on watchlistRevision so assistant-driven watchlist changes appear without a reload"
affects: [04-visualization-dashboard]
actuals:
  tokens: 4400
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Outcome-driven rendering: ActionBadge reads only action.outcome/action.reason (backend-computed truth), never the model's message prose — closes the T-03-15 spoofing threat"
    - "Verbatim reason rendering: reason strings pass through as JSX children with zero JS string transformation (no slice/substring/case-change) — closes T-03-16 tampering"
    - "Split typography role: badge label keeps full Micro/Badge treatment (uppercase/10px/tracking-wide); the reason span is deliberately normal-case so a long rejection sentence stays readable — a documented refinement of the UI-SPEC's single Micro/Badge rule"
    - "Derived-state-during-render for scroll-pill visibility (no useEffect setState) to satisfy eslint-plugin-react-hooks set-state-in-effect, mirroring the portfolioStore/WatchlistPanel pattern already established"
    - "Panel owns its own width (w-80 expanded / w-12 collapsed) instead of the parent wrapping it in a fixed-width div, since it now has two widths"
key-files:
  created:
    - frontend/components/chat/ActionBadge.tsx
  modified:
    - frontend/components/chat/ChatMessageList.tsx
    - frontend/components/chat/ChatPanel.tsx
    - frontend/components/watchlist/WatchlistPanel.tsx
    - frontend/app/page.tsx
key-decisions:
  - "Badge reason span uses normal-case despite the UI-SPEC's single Micro/Badge role covering the whole pill — uppercasing a full rejection sentence would make the one string the user most needs to read the least readable; the label segment still carries the full Micro/Badge treatment"
  - "Collapsed-flag and collapsed-at-message-count both held in useState (not useRef) so they can be read during render to derive hasUnread, per the project's react-hooks rule against reading ref.current at render time"
  - "Scroll-pinned/new-activity state derived during render (React's conditional-setState-during-render pattern) rather than in a useEffect body, avoiding a set-state-in-effect lint violation while keeping the actual DOM scroll mutation in a real useEffect"
patterns-established:
  - "Action outcome is a UI trust boundary: any future action type added to the chat response must render through the same outcome-only, verbatim-reason ActionBadge contract, never through model-authored text"
requirements-completed: [UI-08, CHAT-04]
coverage:
  - id: D1
    description: "Each LLM-requested action renders as its own inline badge below the assistant bubble, colored and worded per the backend's outcome and verbatim reason"
    requirement: CHAT-04
    verification:
      - kind: automated_ui
        ref: "npm --prefix frontend run typecheck && npm --prefix frontend run lint -> both clean"
        status: pass
      - kind: automated_ui
        ref: "grep -c 'to watchlist' / 'from watchlist' ActionBadge.tsx -> both >=1; grep -c formatCurrency -> >=1; grep -c text-gain|bg-gain -> >=1; grep -c text-red-400 -> >=1; negative grep for .slice(/.substring(/.toUpperCase(/.toLowerCase( -> none found"
        status: pass
      - kind: automated_ui
        ref: "grep -rl dangerouslySetInnerHTML frontend/components/chat -> 0 files"
        status: pass
    human_judgment: false
  - id: D2
    description: "A message with zero actions renders no badge-stack container; a mix of executed/error outcomes renders one badge per action in backend order"
    requirement: UI-08
    verification:
      - kind: automated_ui
        ref: "ChatMessageList.tsx renders the badge stack only when trades.length + watchlist_changes.length > 0, mapping both arrays in source order with message-id+index keys (read during diff review)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The chat panel collapses to a 48px rail with a session-only flag and an unread accent-yellow dot, and expands again on click"
    requirement: UI-08
    verification:
      - kind: automated_ui
        ref: "grep -c w-12 / w-80 ChatPanel.tsx -> both >=1; negative grep for localStorage|sessionStorage in ChatPanel.tsx -> none found; grep -c accent-yellow ChatPanel.tsx -> 1"
        status: pass
      - kind: automated_ui
        ref: "npm --prefix frontend run build && test -f frontend/out/index.html -> build succeeds, static export present"
        status: pass
    human_judgment: false
  - id: D4
    description: "Long scrollback auto-scrolls when pinned to bottom and shows a 'New messages' pill when the user has scrolled up during new activity; clicking it scrolls to latest"
    requirement: UI-08
    verification:
      - kind: automated_ui
        ref: "grep -c 'New messages' ChatMessageList.tsx -> 1; grep -c onScroll|scrollHeight ChatMessageList.tsx -> 3"
        status: pass
    human_judgment: false
  - id: D5
    description: "An assistant-executed watchlist change appears in the watchlist panel without a page reload"
    requirement: UI-08
    verification:
      - kind: automated_ui
        ref: "grep -c watchlistRevision WatchlistPanel.tsx -> 2 (read from useChat(), present in the fetch effect's dependency array)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full click-through UAT: buy/reject badges render correctly with a live backend, collapse/expand works, the scroll pill appears/clears correctly, watchlist auto-updates on an AI-driven add, and a reload restores expanded state plus full history with badges"
    verification: []
    human_judgment: true
    rationale: "Deferred to the phase's single end-of-phase UAT batch per workflow.human_verify_mode=end-of-phase (.planning/config.json), the same pattern used by sibling plan 03-03 and validated successfully in Phase 2 (8 deferred checks, 0 issues). All automated typecheck/lint/build/grep verification for this plan already passed in this session."
duration: ~30min (across an interrupted session; see Issues Encountered)
completed: 2026-09-18
status: complete
---

# Phase 03 Plan 04: Action Outcome Badges & Chat Panel Polish Summary

**Per-action executed/error badges driven solely by the backend's outcome and verbatim reason — never the model's own prose — plus the chat panel's collapse rail, scroll-to-latest pill, and a watchlist that now reflects AI-driven changes without a reload.**

## Performance
- **Duration:** ~30min of active work, across a session interrupted by a platform rate limit (see Issues Encountered)
- **Started:** 2026-09-18
- **Completed:** 2026-09-18
- **Tasks:** 2/2 completed
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- `frontend/components/chat/ActionBadge.tsx` (new): renders one pill per trade or watchlist action, built entirely from `action.outcome`/`action.reason` — the backend's computed truth — with zero JS transformation applied to the verbatim reason string, closing the T-03-15 (spoofing) and T-03-16 (tampering) threats from the plan's threat register.
- `ChatMessageList.tsx` renders a badge stack (`flex flex-col gap-1`) as a sibling below each assistant bubble, one `ActionBadge` per `trades[]` item followed by one per `watchlist_changes[]` item, in exact backend order; a message with no actions renders no stack element at all.
- `ChatMessageList.tsx` also gained scroll-position tracking (`onScroll` computing pinned-to-bottom), auto-scroll while pinned, and a "New messages ↓" pill that appears only when the user has scrolled up during new activity — clicking it scrolls to latest and clears the pill.
- `ChatPanel.tsx` now owns its own width: `w-80` expanded, `w-12` collapsed rail with a vertical "Chat" label and an `accent-yellow` unread dot that tracks messages arriving while collapsed. The collapsed flag lives in `useState` only — no browser persistence — so a reload always returns to expanded.
- `frontend/app/page.tsx` drops the fixed-width wrapper it previously placed around `ChatPanel`, now that the panel owns both of its own widths.
- `WatchlistPanel.tsx` reads `watchlistRevision` from `useChat()` and adds it to its existing mount-effect's dependency array, so an assistant-driven ticker add/remove appears in the watchlist immediately, closing the "manage the watchlist through natural language" capability from root PLAN.md §2.
- All automated verification passed in this session: `npm --prefix frontend run typecheck`, `lint`, and `build` (producing `frontend/out/index.html`) all succeed, and every grep-based acceptance check from both tasks returns its expected result.

## Task Commits
1. **Task 1: ActionBadge — one honest verdict per action, rendered outside the bubble** - `79e376e`
2. **Task 2: Finish the panel — collapse rail, scroll-to-latest pill, and a watchlist that keeps up** - `01cea16`

## Files Created/Modified
- `frontend/components/chat/ActionBadge.tsx` - Executed/error outcome pill for one trade or watchlist action
- `frontend/components/chat/ChatMessageList.tsx` - Badge stacks, scroll tracking, auto-scroll, scroll-to-latest pill
- `frontend/components/chat/ChatPanel.tsx` - Collapse rail, unread indicator, own-width ownership
- `frontend/components/watchlist/WatchlistPanel.tsx` - `watchlistRevision` dependency for live watchlist sync
- `frontend/app/page.tsx` - Dropped fixed-width wrapper around `ChatPanel`

## Decisions Made
- **Badge reason span is `normal-case`, deliberately diverging from the UI-SPEC's single Micro/Badge role for the whole pill** — uppercasing a full rejection sentence (e.g. a cash-sufficiency message) would make the one string the user most needs to read the least readable. The label segment (glyph + side/qty/ticker or Added/Removed phrase) keeps the full Micro/Badge treatment; only the verbatim reason segment is exempted. Documented inline in `ActionBadge.tsx` per the plan's instruction.
- **Collapsed flag and collapsed-at-count both held in `useState`, not `useRef`** — both values are read during render to derive `hasUnread`, and the project's `react-hooks` rule disallows reading `ref.current` at render time.
- **Scroll-pin/new-activity flags derived during render rather than in a `useEffect` body** — follows the same conditional-setState-during-render pattern already established for `portfolioStore.tsx`/`WatchlistPanel.tsx` to avoid an `eslint-plugin-react-hooks` set-state-in-effect violation, while the actual DOM scroll mutation (`el.scrollTop = ...`) stays in a real `useEffect` with no setState call.

## Deviations from Plan
None — plan executed exactly as written. The session interruption noted below is a process note about how execution was split across two agent invocations, not a change to what was built or how.

## Issues Encountered
The prior executor session completed Task 1 (`79e376e`) and fully implemented Task 2 in the working tree, but was interrupted by a platform rate limit before it could commit Task 2 or write this SUMMARY. This continuation session read the plan's Task 2 `<action>` and the working-tree diff, confirmed the implementation matched intent exactly (collapse rail widths, unread dot, scroll pill, watchlist dependency), re-ran all automated verification (`typecheck`, `lint`, `build`, and every acceptance-criteria grep) as independent confirmation, and committed the work. No rework was needed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Phase 3 (AI Chat Copilot) is now fully executed — all 4 plans (03-01 through 03-04) complete. The full agentic loop from root PLAN.md §2 (watch → decide → chat → execute → see it reflected) is wired end-to-end: the LLM's structured trades/watchlist_changes execute through the same validated code path as manual actions, their true outcomes render as honest per-action badges separate from the model's own prose, and both the portfolio (via `usePortfolio().refresh()`, Plan 03-03) and the watchlist (via `watchlistRevision`, this plan) reflect assistant-driven changes without a reload.

Ready for phase-goal verification. One deferred item carries into the phase's end-of-phase UAT batch: the full click-through of this plan's `<human-check>` (buy/reject badges, collapse/expand, scroll pill, watchlist live-update, reload persistence) — consistent with the same `workflow.human_verify_mode: end-of-phase` deferral pattern already used by sibling plan 03-03 and validated in Phase 2 with zero issues across 8 deferred checks.

## Self-Check: PASSED

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-18*
