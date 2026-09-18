# Phase 03 — UI Review

**Audited:** 2026-09-18
**Baseline:** 03-UI-SPEC.md (design contract)
**Screenshots:** Not captured (no dev server at localhost:3000/5173/8080)
**Audit type:** Code-only visual and contract audit

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All UI copy matches contract exactly: empty state, loading, error, CTA, placeholder, badges |
| 2. Visuals | 4/4 | Clear visual hierarchy, proper element separation, Unicode-only glyphs, no icon library import |
| 3. Color | 4/4 | All accent colors used only per contract restriction (yellow: unread dot; blue: assistant only; purple: Send button only) |
| 4. Typography | 4/4 | Three weights (400/500/600) and declared sizes (xs/sm/[10px]) only; no divergent values |
| 5. Spacing | 4/4 | Layout contract matched exactly; bubble px-3 py-2, badge gap-1 px-2 py-0.5, panel w-80 expanded / w-12 collapsed |
| 6. Experience Design | 4/4 | Full state coverage: empty/loading/error/populated; interactions: auto-scroll, scroll pill, collapse/expand, portfolio/watchlist sync |

**Overall: 24/24**

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

All UI text strings match the design contract verbatim. No generic or divergent copy detected.

**Empty state:**
- Heading: "Ask FinAlly anything" ✓ (ChatPanel.tsx:96)
- Body: "Get portfolio analysis, or ask it to buy, sell, or update your watchlist." ✓ (ChatPanel.tsx:99-100)

**Loading states:**
- History hydrating: "Loading conversation…" ✓ (ChatPanel.tsx:83)
- Message sending: "FinAlly is thinking" (screen reader text) ✓ (ChatMessageList.tsx:142)

**Error states:**
- History hydrate failed: "Failed to load conversation history." ✓ (chatStore.tsx:66)
- Message send failed: "Message failed to send. Check your connection and try again." ✓ (chatStore.tsx:120)

**Interactive elements:**
- Primary CTA: "Send" button ✓ (ChatInput.tsx:52)
- Input placeholder: "Ask about your portfolio, or tell FinAlly to trade…" ✓ (ChatInput.tsx:42)
- Scroll-to-latest pill: "New messages ↓" ✓ (ChatMessageList.tsx:165)
- Collapsed rail label: "Chat" (vertical) ✓ (ChatPanel.tsx:55-57)

**Action badges:**
- Executed trade: "✓ {SIDE} {qty} {TICKER} @ {price}" format ✓ (ActionBadge.tsx:31)
- Executed watchlist: "✓ Added/Removed {TICKER} to watchlist" ✓ (ActionBadge.tsx:40-41)
- Error outcome: "✕ {SIDE} {qty} {TICKER} — {reason}" with verbatim backend reason ✓ (ActionBadge.tsx:32-33, 75-78)

**Key decision:** Badge reason text is rendered `normal-case` (line 75) rather than `uppercase`, a deliberate refinement from the UI-SPEC's single Micro/Badge role. This preserves readability of the verbatim reason string (often a full sentence) while keeping the label segment (glyph + action) in the full uppercase treatment. Documented in code comments per plan.

---

### Pillar 2: Visuals (4/4)

Visual hierarchy is clear, element differentiation is strong, and layout structure matches contract.

**Panel structure:**
- Expanded: w-80 (320px) flex column with header, scrollable message list, input row ✓
- Collapsed: w-12 (48px) vertical rail with "Chat" label and unread dot ✓
- Header row: "AI Assistant" heading + "Collapse" button, mirroring WatchlistPanel ✓

**Message bubbles:**
- User messages: right-aligned, bg-terminal-bg, border, px-3 py-2 ✓ (ChatMessageList.tsx:104)
- Assistant messages: left-aligned, bg-terminal-panel, border-l-2 border-accent-blue, px-3 py-2 ✓ (ChatMessageList.tsx:115)
- Action badge stack: siblings below assistant bubble, never inside it ✓ (ChatMessageList.tsx:118-135)

**Loading indicator:**
- Three animated dots (bg-accent-blue, animate-pulse) with staggered animation delays ✓ (ChatMessageList.tsx:144-156)
- Screen reader text: "FinAlly is thinking" with aria-live="polite" ✓ (ChatMessageList.tsx:141-143)

**Scroll-to-latest pill:**
- Positioned absolute bottom-center, shows only on scroll-up activity ✓ (ChatMessageList.tsx:159-167)
- Click scrolls to bottom and clears pill ✓ (ChatMessageList.tsx:85-89)

**Interactive states:**
- Send button: enabled while text present, disabled while sending ✓ (ChatInput.tsx:49-50)
- Input: disabled while in flight ✓ (ChatInput.tsx:43)
- All errors rendered with `role="alert"` ✓ (ChatPanel.tsx:88, 111; ActionBadge.tsx:57)

**Glyph usage:**
- Action badges: ✓ (executed) and ✕ (error) only; no icon imports ✓ (ActionBadge.tsx:22)
- Scroll pill: ↓ arrow text character ✓ (ChatMessageList.tsx:165)
- No icon library or @heroicons imports detected ✓

---

### Pillar 3: Color (4/4)

All accent colors used strictly per contract restriction. Semantic meaning preserved across the app.

**Accent yellow (#ecad0a):**
- Used ONLY for unread indicator dot on collapsed rail ✓ (ChatPanel.tsx:60)
- Count: 1 instance in chat components
- Matches contract restriction: "unread-message indicator dot on the collapsed chat rail (new)" ✓

**Accent blue (#209dd7):**
- Assistant message left border: border-l-2 border-accent-blue ✓ (ChatMessageList.tsx:115, 140)
- Thinking-indicator dots: bg-accent-blue ✓ (ChatMessageList.tsx:145-156)
- Count: 5 instances, all in assistant message context
- Matches contract: "assistant message left-border accent... and the color of the 'AI is thinking' loading-dots indicator" ✓

**Accent purple (#753991):**
- Send button: bg-accent-purple ✓ (ChatInput.tsx:50)
- Count: 1 instance
- Matches contract: "Chat input's Send button — reuses PLAN.md §2's explicit rule" ✓

**Semantic colors (gain/loss already in app):**
- Success (gain, #4ade80): Executed action badges use text-gain bg-gain/10 ✓ (ActionBadge.tsx:51)
- Destructive (loss, #f87171): Error copy and error badges use text-red-400 bg-red-400/10 ✓ (ActionBadge.tsx:52)
- Both reuse existing app-wide semantics (price up/down, P&L sign) ✓

**60/30/10 distribution:**
- Dominant (60%, terminal-bg): Page and bubble backgrounds ✓
- Secondary (30%, terminal-panel): Panel and assistant bubble backgrounds ✓
- Accent (10%, three colors above): Strictly limited per roles ✓

---

### Pillar 4: Typography (4/4)

Three font weights (400/500/600) and declared sizes (xs/sm/[10px]) only. No weight or size creep detected.

**Font weights in use:**
- 400 (regular): Body text, input, error copy, badge reason segment ✓
- 500 (medium): Panel header "AI Assistant" (Heading role) ✓
- 600 (semibold): Badge label segment (Micro/Badge role) ✓

**Font sizes in use:**
- text-xs (12px): Collapsed rail label "Chat" ✓ (ChatPanel.tsx:55)
- text-sm (14px): Message bubbles, empty state, error copy, Send button text ✓
- text-[10px] (10px): Badge label and reason segments (Micro/Badge role) ✓

**Coverage:**
- text-xs: 1 role (collapsed rail label) ✓
- text-sm: 3 roles (Body, Label implicit, input default) ✓
- text-[10px]: Micro/Badge role ✓
- No fonts outside declared set detected ✓

**Line height maintained:**
- Body role prose rendered at default (1.5 computed from globals) ✓
- Micro/Badge spans maintain density ✓

**Typography hierarchy locked:**
- Heading (AI Assistant): text-sm font-medium (14/500) ✓
- Body (messages, empty state): text-sm (14/400) ✓
- Label (input placeholder): implicit text-sm (14/400) ✓
- Micro/Badge: text-[10px] font-semibold (10/600) ✓

---

### Pillar 5: Spacing (4/4)

Layout & Interaction Contract matched exactly. All specified spacing values present and correct.

**Panel dimensions:**
- Expanded width: w-80 (320px) ✓ (ChatPanel.tsx:69)
- Collapsed rail width: w-12 (48px) ✓ (ChatPanel.tsx:53)
- Both match explicit contract: "48px-wide rail" and "w-80 (320px) — matches the left watchlist column's width" ✓

**Message list container:**
- Layout: `flex flex-col gap-3 p-4` (12px gaps, 16px padding) ✓ (ChatMessageList.tsx:96)
- Matches contract: `flex-1 overflow-y-auto flex flex-col gap-3 p-4` ✓

**User message bubble:**
- Spacing: `px-3 py-2 max-w-[85%]` (12px horizontal, 8px vertical) ✓ (ChatMessageList.tsx:104)
- Matches contract exactly ✓

**Assistant message bubble:**
- Spacing: `px-3 py-2 max-w-[85%]` (12px horizontal, 8px vertical) ✓ (ChatMessageList.tsx:115)
- Matches contract exactly ✓

**Action badge stack:**
- Stack container: `flex flex-col gap-1` (4px gaps) ✓ (ChatMessageList.tsx:119)
- Matches contract: "stacked `flex flex-col gap-1`" ✓

**Individual badge:**
- Spacing: `gap-1 rounded-full px-2 py-0.5` (4px/8px/2px) ✓ (ActionBadge.tsx:56)
- Matches contract exactly ✓

**Input row:**
- Layout: `border-t border-terminal-border p-3 flex gap-2` (12px padding, 8px flex gap) ✓ (ChatInput.tsx:36)
- Matches contract exactly ✓

**Input and button spacing:**
- Input: `px-2 py-1` (8px/4px) ✓ (ChatInput.tsx:44)
- Button: `px-3 py-1` (12px/4px) ✓ (ChatInput.tsx:50)
- Reasonable visual balance ✓

**Scroll-to-latest pill:**
- Spacing: `px-3 py-1` (12px/4px) ✓ (ChatMessageList.tsx:163)
- Positioned: `absolute bottom-3 left-1/2 -translate-x-1/2` ✓

**Panel header row:**
- Spacing: `p-4 pb-2` (16px with reduced bottom) ✓ (ChatPanel.tsx:70)
- Clear visual separation from message area ✓

---

### Pillar 6: Experience Design (4/4)

Comprehensive state coverage, proper interaction patterns, accessibility correctly marked.

**Empty states:**
- Message list (first load): "Ask FinAlly anything" heading + descriptive body ✓ (ChatPanel.tsx:93-102)
- Condition: `messages !== null && !hydrateError && messages.length === 0` ✓
- No badges rendered when zero actions ✓ (ChatMessageList.tsx:118 guards with `actionCount > 0`)

**Loading states:**
- History hydrating: "Loading conversation…" (ChatPanel.tsx:82-85) — condition: `messages === null` ✓
- Message sending: Three animated dots with `aria-live="polite"` announcement (ChatMessageList.tsx:139-157) ✓
- Input disabled while sending: `disabled={isSending}` ✓ (ChatInput.tsx:43)
- Send button disabled while sending: `disabled={isSending || text.trim() === ""}` ✓ (ChatInput.tsx:49)

**Error states:**
- History hydrate failure: Red alert text in message list area, input remains enabled (ChatPanel.tsx:87-90) ✓
  - Condition: `messages !== null && hydrateError` (hydrate degraded gracefully) ✓
- Message send failure: Centered boxed alert below message list (ChatPanel.tsx:109-115) ✓
  - Error text sourced from catch block (chatStore.tsx:117-121) ✓
  - Typed text retained for retry (ChatInput line 26 only clears on `sent`) ✓
- Action execution failure: Error badge with outcome "error" and verbatim reason (ActionBadge.tsx:32, 50-52) ✓

**Interaction patterns:**
- Send on Enter key: `if (event.key === "Enter") { void submit(); }` ✓ (ChatInput.tsx:30-32)
- Send on button click: `onClick={() => void submit()}` ✓ (ChatInput.tsx:48)
- Optimistic append: User message added immediately, rolled back by UUID on failure (chatStore.tsx:81-88, 124) ✓
- Portfolio refresh on executed trade: `if (response.trades.some((t) => t.outcome === "executed")) { await refreshPortfolio(); }` ✓ (chatStore.tsx:106-108)
- Watchlist live-sync on change: `setWatchlistRevision((rev) => rev + 1)` triggers WatchlistPanel refetch (chatStore.tsx:110-113) ✓

**Auto-scroll behavior:**
- Pinned-to-bottom state derived from scroll position: `scrollHeight - scrollTop - clientHeight <= 40` ✓ (ChatMessageList.tsx:74)
- Auto-scroll while pinned: `useEffect(() => { if (pinned) scrollToBottom(); }` ✓ (ChatMessageList.tsx:79-83)
- Scroll-to-latest pill shown only on scroll-up during activity ✓ (ChatMessageList.tsx:52-56)
- Pill click scrolls to bottom and clears: `handlePillClick()` ✓ (ChatMessageList.tsx:85-89)

**Collapse/expand behavior:**
- Toggles between full panel (w-80) and rail (w-12) ✓ (ChatPanel.tsx:48-121)
- Unread indicator dot tracks new messages while collapsed ✓ (ChatPanel.tsx:34-36)
- Collapsed state held in React `useState` only, no persistence (ChatPanel.tsx:26, 31-32)
- Session-only: reload returns to expanded ✓ (matching contract assumption)

**Accessibility:**
- Thinking indicator marked `aria-live="polite"` + `sr-only` ✓ (ChatMessageList.tsx:141-143)
- Error alerts marked `role="alert"` ✓ (ChatPanel.tsx:88, 111; ActionBadge.tsx:57)
- Unread dot marked `aria-hidden="true"` (visual-only) ✓ (ChatPanel.tsx:61)
- No HTML injection: zero `dangerouslySetInnerHTML` usage ✓
- No hardcoded network access: zero direct `fetch()` in components ✓

**Action rendering:**
- ActionBadge reads ONLY from `action.outcome` and `action.reason` (backend-computed truth) ✓ (ActionBadge.tsx:21, 67-78)
- Reason text is JSX children with no JS transformation (no slice/toUpperCase/etc.) ✓ (ActionBadge.tsx:75)
- Each action independent badge (no aggregation) ✓ (ChatMessageList.tsx:120-133)
- Badge order matches backend order ✓ (trades then watchlist_changes, in iteration order)

---

## Files Audited

### Chat Frontend Components
- `frontend/components/chat/ChatPanel.tsx` (122 lines)
- `frontend/components/chat/ChatInput.tsx` (57 lines)
- `frontend/components/chat/ChatMessageList.tsx` (171 lines)
- `frontend/components/chat/ActionBadge.tsx` (83 lines)

### Chat Store & Types
- `frontend/lib/chatStore.tsx` (155 lines)
- `frontend/lib/api.ts` (partial, chat routes only)
- `frontend/lib/types.ts` (chat types: ChatMessage, ChatResponse, ActionOutcome, TradeAction, WatchlistAction)

### Layout Integration
- `frontend/app/page.tsx` (third flex child integration)
- `frontend/app/globals.css` (color tokens, font family, theme)
- `frontend/app/layout.tsx` (ChatProvider nesting)

### TypeScript & Linting
- `npm run typecheck` — 0 errors ✓
- All imports properly typed ✓
- No explicit `any` types in chat code ✓

---

## Summary

**Phase 03 (AI Chat Copilot) UI implementation is production-ready.**

All 6 pillars score 4/4 against the UI-SPEC.md design contract:
1. **Copywriting:** Every UI string matches contract exactly (empty/load/error/CTA/placeholder/badges)
2. **Visuals:** Clear hierarchy, proper element separation, Unicode glyphs only, no icon library
3. **Color:** Accents used strictly per restriction; semantic colors (gain/loss) consistent with app
4. **Typography:** Three weights (400/500/600), declared sizes only (xs/sm/[10px])
5. **Spacing:** Layout contract matched exactly; all dimensions, gaps, padding per contract
6. **Experience Design:** Full state coverage (empty/load/error/populated), interactions (send/scroll/collapse), accessibility marked

**No issues to report. No fixes required.**

The implementation demonstrates:
- Adherence to design system without over-engineering
- Accessibility best practices (aria-live, role="alert", sr-only)
- Proper separation of concerns (ActionBadge reads outcome only, never prose)
- State management patterns (optimistic send with rollback, portfolio/watchlist sync)
- Responsive collapse/expand behavior with session-only persistence
- Full TypeScript safety with 0 type errors

---

*UI Review completed: 2026-09-18*
*Baseline: 03-UI-SPEC.md*
*Verdict: PASS — Ready for Phase 04 UAT or production deployment*
