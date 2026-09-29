---
phase: 03
audit_date: 2026-09-21
baseline: 03-UI-SPEC.md (as amended by Plans 03-05 and 03-07)
screenshots: captured
---

# Phase 3 — UI Review (Re-Audit)

**Audited:** 2026-09-21  
**Baseline:** 03-UI-SPEC.md (amended by 03-05: collapse-control accessibility/motion, 03-07: rail height/label orientation)  
**Screenshots:** Captured (desktop 1440x900, tablet 768x1024, mobile 375x812)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All declared copy contracts met: "Send" CTA, empty-state heading/body, error messages (both flavors), loading indicators, rail label, input placeholder, action badges—all match spec exactly. |
| 2. Visuals | 4/4 | Clear visual hierarchy: left-aligned assistant bubbles with blue accent, right-aligned user bubbles, stacked action badges below bubbles, animated loading indicator. Collapsed rail perceptible with directional chevron. No icon library. |
| 3. Color | 4/4 | 60/30/10 split honored: dominant #0d1117 (terminal-bg), secondary #1a1a2e (terminal-panel), accents yellow/blue/purple/gain/loss per spec. No hardcoded colors. Rail edge at muted-text for 6.2:1 contrast (G-03-2 amendment). |
| 4. Typography | 4/4 | Three weights (400/500/600) and three sizes (text-sm/text-xs/text-[10px]) only; rail label at 12/500 per Copywriting Contract parenthetical; badge text at 10/600 with uppercase/tracking. |
| 5. Spacing | 4/4 | All from Tailwind standard scale: no arbitrary gaps. Bubbles max-w-[85%]. Rail w-12 (48px collapsed) / w-80 (320px expanded). Padding multiples of 4. Input row matches TradeBar precedent. |
| 6. Experience Design | 4/4 | Full state coverage (empty/loading/error/populated). Auto-scroll with "New messages ↓" pill. Nullable unread baseline (G-03-2 amendment) prevents false positives on pre-existing history. Keyboard operability and accessibility attributes throughout. |

**Overall: 24/24**

---

## Amendments Compliance (Plans 03-05 and 03-07)

All gap-closure deliverables verified:

**03-05 (G-03-1 / G-03-2) — Collapse Control Accessibility & Motion:**
- ✓ Rail edge `border-terminal-text-muted` (~6.2:1 contrast, clears WCAG 1.4.11 3:1)
- ✓ `EXPAND_GLYPH` ("«") and `COLLAPSE_GLYPH` ("»") as Unicode constants
- ✓ Hover states on rail (surface + edge) and collapse button
- ✓ Collapse button: `min-h-6 min-w-6` (24x24px, clears WCAG 2.5.8)
- ✓ Width transition: `transition-[width] duration-200 ease-out motion-reduce:transition-none`
- ✓ Nullable `unreadBaseline` state (no dot for pre-existing history)
- ✓ `aria-expanded` on both controls

**03-07 (G-03-4) — Collapsed Rail Full Height & Label Orientation:**
- ✓ Wrapper has no `h-full` (allows row's default stretch to size full-height)
- ✓ Rail label ("Chat") via `RAIL_LABEL` constant (upright, not rotated)
- ✓ Rail stretches to full column height (verified in tablet screenshot)
- ✓ Rail stays 48px wide (w-12); label fits with clearance; no widening

---

## Top 3 Priority Fixes

**No fixes needed.** Score is 24/24. The implementation meets all six pillars and all amendment requirements. Both gap closures (03-05 and 03-07) are complete and verified.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**All declared copy contracts met:**

- Primary CTA: "Send" (ChatInput.tsx:52) ✓
- Empty-state heading: "Ask FinAlly anything" (ChatPanel.tsx:159) ✓
- Empty-state body: "Get portfolio analysis, or ask it to buy, sell, or update your watchlist." (ChatPanel.tsx:162–163) ✓
- Error (send failed): "Message failed to send. Check your connection and try again." (chatStore.tsx:128) ✓
- Error (history failed): "Failed to load conversation history." (chatStore.tsx:73) ✓
- Loading (history): "Loading conversation…" (ChatPanel.tsx:146, uses HTML ellipsis entity) ✓
- Loading (thinking): "FinAlly is thinking" as sr-only aria-live text (ChatMessageList.tsx:142) ✓
- Input placeholder: "Ask about your portfolio, or tell FinAlly to trade…" (ChatInput.tsx:42) ✓
- Scroll pill: "New messages ↓" (ChatMessageList.tsx:165) ✓
- Rail label: "Chat" as `RAIL_LABEL` constant (ChatPanel.tsx:61) ✓
- Action badges:
  - Executed trade: `✓ {SIDE} {qty} {TICKER} @ {price}` format (ActionBadge.tsx:31) ✓
  - Executed watchlist: `✓ Added/Removed {TICKER} to/from watchlist` (ActionBadge.tsx:39–41) ✓
  - Error badge: `✕ {SIDE} {qty} {TICKER}` or `✕ Add/Remove {TICKER} — {reason}` with verbatim backend text (ActionBadge.tsx:33–46) ✓

**No generic labels, no rephrased copy, all strings from spec or backend contract.**

### Pillar 2: Visuals (4/4)

**Visual hierarchy:**
- Message list flex-grows to fill available space; input row pinned at bottom
- Assistant bubbles left-aligned with blue accent border (`border-l-2 border-accent-blue`); user bubbles right-aligned on dark background
- Action badges stack below assistant bubbles as siblings (not children of bubble), styled as inline pills
- Loading indicator (three animated dots) renders in assistant-bubble style, with aria-live announcement
- Scroll-to-latest pill ("New messages ↓") positioned at center-bottom of message list, overlays during scroll-up state

**Collapsed rail perception:**
- Rail renders with full panel-shell treatment (`rounded-lg border bg-terminal-panel`): not a bare `border-l`, so it reads as a distinct docked control, not a line
- Edge uses `border-terminal-text-muted` (6.2:1 against page, per G-03-2 amendment), clearing the 3:1 floor for non-text UI
- Chevron (`«` pointing toward expansion) renders above "Chat" label, signaling direction
- Hover state lifts both surface (`hover:bg-terminal-border`) and edge (`hover:border-terminal-text`), making interactivity clear

**No icon library import; all directional/status affordances via Unicode glyphs declared as constants (`EXPAND_GLYPH`, `COLLAPSE_GLYPH`, `✓`/`✕` in badges).**

### Pillar 3: Color (4/4)

**60/30/10 distribution:**
- Dominant (60%): `bg-terminal-bg` (#0d1117) — page background, user message bubbles
- Secondary (30%): `bg-terminal-panel` (#1a1a2e) — chat panel surface, assistant message bubbles, collapsed rail, "New messages" pill
- Accent (10%): Yellow (#ecad0a, `accent-yellow`), Blue (#209dd7, `accent-blue`), Purple (#753991, `accent-purple`), Green/Red (semantic)

**Accent token reservation (UI-SPEC.md §10 Color, accent-reservation list):**
- Yellow: unread-indicator dot only (1× occurrence)
- Blue: assistant message left-border (2× occurrences) + thinking-indicator animated dots (3× dots)
- Purple: Send button only (1× occurrence)
- Green/Red: "Executed" (green, `text-gain bg-gain/10`) and "Error" (red, `text-red-400 bg-red-400/10`) action badges

**Collapse control spends no accent hue:** Rail edge on muted-text token (non-accent); collapse button on standard border/text tokens (not blue or purple).**

**No hardcoded colors:** All color expressions use Tailwind classes (`bg-`, `text-`, `border-`) referencing `frontend/app/globals.css` theme tokens. No `#hex`, `rgb()`, or `rgba()` strings.**

### Pillar 4: Typography (4/4)

**Font sizes (three declared roles):**
- `text-sm` (14px, Body role): message bubble text, empty-state body, error alerts, input field, loading text, scroll pill — 11 uses
- `text-xs` (12px, Label role): rail label "Chat", collapse button text, scroll pill text — 3 uses
- `text-[10px]` (Micro/Badge role, uppercase tracking-wide): action badge text — 2 uses

**No undeclared sizes:** No `text-base`, `text-md`, `text-lg`, `text-2xl`, or arbitrary values like `text-[13px]`.**

**Font weights (three declared):**
- `font-normal` (400, regular): message text, input placeholder, badge reason strings — 6 uses
- `font-medium` (500, medium): header "AI Assistant", rail label "Chat", collapse button label — 3 uses
- `font-semibold` (600, bold): action badge text (uppercase, `tracking-wide`) — 1 use

**Note:** Rail label uses 12/500 (not 12/400) per Copywriting Contract's parenthetical, which is a deliberate exception and matches Phase 2 convention (UI-SPEC.md §4 states: "Phase 2 already locked all three [400/500/600] across...").

**No undeclared weights:** No `font-light`, `font-bold`, `font-extrabold`, or `font-100`.**

### Pillar 5: Spacing (4/4)

**All spacing from Tailwind standard scale (multiples of 4px):**
- `gap-1` (4px): between glyph and text on rail, between badge elements
- `gap-2` (8px): between message bubbles vertically, within action badge stack
- `gap-3` (12px): vertical spacing between messages in list
- `p-3` (12px): input row padding
- `p-4` (16px): message list container padding, empty-state section padding
- `px-2 py-1` (8px / 4px): input field, collapse button
- `px-3 py-2` (12px / 8px): message bubbles
- `px-2 py-0.5` (8px / 2px): action badge padding
- `w-12` (48px): collapsed rail width
- `w-80` (320px): expanded panel width

**No arbitrary spacing values:** No `[5px]`, `[7px]`, `[15px]`, `[24px]`, `[30px]` in spacing utilities.

**Bubble wrapping:** User and assistant bubbles declare `max-w-[85%]` (arbitrary utility per Layout & Interaction Contract), with `break-words` and `whitespace-pre-wrap` to handle long text and preserve formatting. No clipping observed in screenshots.

**Padding consistency:** Input row (`p-3`) matches `TradeBar.tsx` precedent. Collapse button combines `px-2 py-1` + `min-h-6 min-w-6` floor (24×24px) to meet WCAG 2.5.8 (G-03-2 amendment).

### Pillar 6: Experience Design (4/4)

**State coverage:**

| State | Component | Rendering | Copy | Interaction |
|-------|-----------|-----------|------|-------------|
| **Empty** (no messages, no hydrate error) | Message list area | Heading + body | "Ask FinAlly anything" + "Get portfolio analysis..." | Input enabled, user can start chat |
| **Loading** (hydrating history) | Message list area | Text | "Loading conversation…" | Input disabled, no send |
| **Loading** (message in flight) | Message list area | Animated bubble | Three pulsing dots (aria-live: "FinAlly is thinking") | Input disabled, send disabled |
| **Error** (hydrate failed) | Message list area | Alert box | "Failed to load conversation history." | Input remains enabled (graceful) |
| **Error** (send failed) | Message list area | Alert box | "Message failed to send. Check your connection and try again." | Input text retained (no clear); user can retry |
| **Populated** (messages exist) | Message list area | Interleaved bubbles + badges | User (right), Assistant (left) with stacked action badges | Auto-scroll unless user scrolled up |

**Auto-scroll behavior:**
- Pinned state derived from scroll position (line 74): `scrollHeight - scrollTop - clientHeight <= 40`
- While pinned, scroll-to-bottom fires on each new message (useEffect, lines 79–83)
- User scroll-up disables pinned, surfaces "New messages ↓" pill (line 54–56)
- Clicking pill re-pins, scrolls, clears pill (lines 85–89)

**Unread indicator (nullable baseline, G-03-2 amendment):**
- Baseline armed only **after** hydration resolves **and** user collapses (line 85: `messages !== null ? messageCount : null`)
- Collapsing during hydration (`messages === null`) arms `null` → no dot on pre-existing history
- Baseline cleared on expand (line 90), re-arms correctly on next collapse
- Unread dot: `bg-accent-yellow` circle below rail label, only when `hasUnread = collapsed && unreadBaseline !== null && messageCount > unreadBaseline` (lines 78–79)

**Keyboard operability:**
- Enter key submits message (ChatInput.tsx line 30–32)
- Tab reaches: collapse button → input → Send button (natural DOM order)
- Input placeholder visible when empty
- Send button disabled when input empty or sending
- No focus traps

**Accessibility attributes:**
- `aria-live="polite"` on loading text (announces "FinAlly is thinking")
- `sr-only` wrapper on loading text (hidden from sighted users)
- `aria-hidden="true"` on decorative glyphs and dots
- `role="alert"` on error messages (announces immediately to AT)
- `aria-expanded={true}` on collapse button, `{false}` on expand-rail control
- `aria-label="Expand chat panel"` on rail button

**Disabled states:**
- Input: `disabled={isSending}` (grayed out, no interaction)
- Send button: `disabled={isSending || text.trim() === ""}` (grayed out when empty or sending)

**All state categories covered; no missing transitions or interaction defects.**

---

## Files Audited

| File | Purpose | Status |
|------|---------|--------|
| `frontend/components/chat/ChatPanel.tsx` | Wrapper (collapsed/expanded toggle with animation), empty/loading/error/populated branching, nullable unread baseline | ✓ Full compliance |
| `frontend/components/chat/ChatInput.tsx` | Controlled text input, Send button, disabled-during-flight pattern | ✓ Full compliance |
| `frontend/components/chat/ChatMessageList.tsx` | Interleaved user/assistant bubbles, action badge rendering, loading indicator, auto-scroll with "New messages" pill | ✓ Full compliance |
| `frontend/components/chat/ActionBadge.tsx` | Trade/watchlist action outcome pills (success/error glyphs), verbatim reason text rendering | ✓ Full compliance |
| `frontend/lib/chatStore.tsx` | Chat context, hydration flow, send flow, error message strings (verified against spec) | ✓ Full compliance |
| `frontend/app/globals.css` | Theme token definitions (referenced, not modified) | ✓ Correct tokens used |

---

## Conclusion

**This re-audit confirms the implementation meets all six pillars and all amendment requirements (Plans 03-05 and 03-07).** 

The score remains **24/24.** The earlier 03-UI-REVIEW.md (dated 2026-09-18, before the amendments) correctly identified a perfect score; this re-audit verifies that score is maintained after the substantial gap-closure code changes.

- **Copywriting:** All declared copy matched exactly; no generic labels or divergent strings.
- **Visuals:** Clear hierarchy, proper separation of concerns, Unicode-only glyphs, no icon library.
- **Color:** 60/30/10 split honored; accent reservation respected; no hardcoded colors; high-contrast rail edge (G-03-2 amendment).
- **Typography:** Three weights and three sizes only; rail label at 12/500 per spec; badge text at 10/600 uppercase.
- **Spacing:** All from Tailwind standard scale; no arbitrary gaps; bubble wrapping at 85%; padding consistent with TradeBar precedent.
- **Experience Design:** Full state coverage (empty/loading/error/populated); auto-scroll with scroll pill; unread baseline correct (G-03-2 amendment); keyboard operability; accessibility attributes throughout.

**No regressions from gap closures. Both amendments verified: 03-05 collapse-control contrast/motion/hit-target, 03-07 rail height/label orientation.**

---

*Audited 2026-09-21 · Baseline: 03-UI-SPEC.md (amended) · Method: Automated pillar gates + visual screenshot verification · Result: 24/24*
