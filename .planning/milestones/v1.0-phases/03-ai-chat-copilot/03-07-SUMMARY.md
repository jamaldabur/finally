---
phase: 03-ai-chat-copilot
plan: 07
subsystem: frontend-chat-ui
tags: [react, tailwind, flexbox, layout, accessibility, ui-spec-amendment]

requires:
  - phase: 03-ai-chat-copilot
    provides: "Plan 03-05's collapsible chat panel — contrast fix, chevrons, hover states, aria-expanded, width transition, nullable unread baseline"
provides:
  - "Collapsed chat rail that stretches to the body row's full column height instead of rendering as a 48x59px content-sized chip"
  - "Upright, horizontal rail label (RAIL_LABEL constant) sharing its reading orientation with the chevron above it, replacing the rotated vertical-rl label"
  - "03-UI-SPEC.md amended (entries 6-7) to state the rail's height explicitly and specify horizontal label orientation, closing the specification silence that let the height defect pass review"
affects: [03-ai-chat-copilot-verification, frontend-layout-conventions]

actuals:
  tokens: 2700
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Flex-item height comes from the parent row's default stretch, not from a percentage height on the item itself — a non-auto computed cross size disables stretch outright rather than merely leaving it unrequested"
    - "Design-contract silence about a measurable property (height) is itself a defect class — the Dock placement bullet now states the rail's height explicitly so review has something to check"

key-files:
  created: []
  modified:
    - frontend/components/chat/ChatPanel.tsx
    - .planning/phases/03-ai-chat-copilot/03-UI-SPEC.md

key-decisions:
  - "Removed h-full from ChatPanel's wrapper rather than adding a compensating override (align-self, inline style) — the debug session's live experiments proved a non-auto cross size disables stretch outright, so no override recovers it; the fix is removing the height, not adding a different one"
  - "Left frontend/app/page.tsx untouched — the fix is fully contained in ChatPanel's own wrapper, and the adjacent long-conversation page-scroll defect needs a different, deeper fix (a definite-height chain from the document root) that is explicitly out of this gap's scope"
  - "Did not widen the 48px rail or shrink/drop the label — the debug session measured the horizontal label fits the existing 46px inner width with ~10px clearance per side, so no Spacing Scale change was needed"

patterns-established:
  - "Named constant for rail-adjacent copy (RAIL_LABEL) mirrors the existing EXPAND_GLYPH/COLLAPSE_GLYPH convention, keeping 03-UI-SPEC.md's Copywriting Contract greppable against the code"

requirements-completed: [UI-08]

coverage:
  - id: D1
    description: "03-UI-SPEC.md amended: Copywriting Contract rail-label row and Dock placement bullet both specify horizontal/upright label and explicit full-column-height rail, recorded in Amendments entries 6-7 against G-03-4"
    requirement: "UI-08"
    verification:
      - kind: other
        ref: "grep gates in 03-07-PLAN.md Task 1 <verify> (Amendments count=1, G-03-4 present, rotated wording absent, horizontal/full-column-height wording present, Spacing Scale/status/sign-off untouched) — all 9 gates PASS"
        status: pass
    human_judgment: false
  - id: D2
    description: "ChatPanel.tsx wrapper no longer declares a height utility, relying on the parent row's default stretch; rail button and expanded section keep their own h-full w-full"
    requirement: "UI-08"
    verification:
      - kind: other
        ref: "grep gates in 03-07-PLAN.md Task 2 <verify>: no h-full/transition-[width] co-occurrence, h-full w-full count=2, no self-stretch/align-self/inline-style, page.tsx unchanged — all structural gates PASS"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run typecheck && lint && build (static export produced, frontend/out/index.html present)"
        status: pass
    human_judgment: true
    rationale: "This project has no frontend test runner or headless-browser harness (confirmed in 03-07-PLAN.md planner_assumptions #4), so no automated check can render the DOM and measure the rail's actual pixel height. The automated gates assert the cause (no height declared, no compensating override); only a human browser check can confirm the effect (the rail visually spans full column height). Deferred to end-of-phase UAT per this project's `human_verify_mode: end-of-phase` convention, matching how Phase 2 and Plan 03-05's visual checks were handled."
  - id: D3
    description: "Rail label reads upright and horizontal via a named RAIL_LABEL constant, no vertical-rl anywhere in the file"
    requirement: "UI-08"
    verification:
      - kind: other
        ref: "grep gates: no vertical-rl occurrence, RAIL_LABEL count=2 (declared + rendered), w-12 rail width preserved"
        status: pass
    human_judgment: true
    rationale: "Same as D2 — visual reading orientation and label legibility is a human-observable property; the grep gates prove the CSS property was removed and the string constant is wired, not that it renders legibly on screen. Deferred to end-of-phase UAT."

duration: ~20min
completed: 2026-09-21
status: complete
---

# Phase 03 Plan 07: Collapsed Chat Rail Full-Height Fix Summary

**Removed the `h-full` percentage height that made ChatPanel's collapsed rail render as a 48x59px corner chip instead of a full-column-height rail, and swapped the rail label from rotated `writing-mode:vertical-rl` text to an upright `RAIL_LABEL` constant — closing G-03-4, the last gap-closure item in Phase 3.**

## Performance
- **Duration:** ~20min
- **Started:** 2026-09-21 (session start)
- **Completed:** 2026-09-21T18:52:27+03:00
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Diagnosed root cause (from `.planning/debug/collapsed-rail-vertical-label.md`) fixed at the source: `h-full` on the wrapper resolved against a row with `auto` specified height and disabled `align-items: stretch`, the exact mechanism giving every sibling column its height. Removing it — with no compensating override — lets the row's default stretch size the wrapper correctly.
- Rail label now reads upright and horizontal via a new `RAIL_LABEL` module constant, matching the existing `EXPAND_GLYPH`/`COLLAPSE_GLYPH` convention, sharing orientation with the chevron above it.
- `03-UI-SPEC.md`'s Dock placement bullet and Copywriting Contract row now state the rail's height and label orientation explicitly, closing the specification silence that let the original height defect pass review undetected.
- Everything Plan 03-05 delivered (contrast edge, hover states, both `aria-expanded` attributes, width transition + reduced-motion opt-out, reserved yellow unread dot) verified intact via unchanged grep gates.

## Task Commits
1. **Task 1: Amend 03-UI-SPEC.md so the rail's label orientation and its height are both specified correctly** - `51e37c7` (docs)
2. **Task 2: Let the chat column stretch, and stand the rail's label upright** - `48f0da5` (fix)

## Files Created/Modified
- `.planning/phases/03-ai-chat-copilot/03-UI-SPEC.md` - Copywriting Contract rail-label row and Dock placement collapsed bullet corrected; Amendments section extended with entries 6-7 naming G-03-4
- `frontend/components/chat/ChatPanel.tsx` - `h-full` removed from the width-owning wrapper; `RAIL_LABEL` constant added and rendered in place of the rotated inline "Chat" string; head comment extended to record the mechanism and measured before/after so the height is not reintroduced

## Decisions Made
- Removed the height rather than adding a compensating `align-self`/inline-style override — the debug session's live EXPERIMENT B proved that combination still measures 59.05px, since a non-auto computed cross size disables stretch outright.
- Left `frontend/app/page.tsx` untouched, as required — the fix is fully contained in ChatPanel's own wrapper.
- Kept the rail at its existing 48px width and the label at its existing 12px Label role — the debug session's font-metric measurements showed the horizontal label fits with ~10px clearance per side, so no Spacing Scale change was warranted.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' automated `<verify>` gates (9 for Task 1, 17 for Task 2 including typecheck/lint/build) all passed on the first attempt with no fix cycles needed.

## Issues Encountered

None.

## User Setup Required
None - no external service configuration required.

## Known Follow-Up (explicitly out of scope for this plan)

The expanded chat panel still has no internal scroll boundary on a long hydrated conversation — the whole page scrolls instead of the message list scrolling internally within the panel. The debug session measured this as a separate, deeper defect: nothing in the `html > body > page` chain establishes a definite height, so no descendant can be "full height with internal scroll." Removing `h-full` from ChatPanel's wrapper (this plan's fix) does NOT fix it — the row's height is still `auto`, so it simply grows to its tallest child. The correct fix is a definite-height chain from the document root down (e.g. `h-screen` + `min-h-0` threaded through the layout), touching `globals.css` and `page.tsx`, which is out of scope here per the plan's explicit exclusion. Should be filed as its own gap if round-3 UAT reproduces it.

## Next Phase Readiness

This was the last remaining gap-closure plan in Phase 3 (G-03-4, following G-03-5/G-03-6 closed by Plan 03-08 and G-03-1/G-03-2 closed by Plan 03-05). All automated verification for both tasks passed. The visual/height effect of this fix (D2/D3 above) requires a human browser check per this project's `human_verify_mode: end-of-phase` convention — deferred to the end-of-phase UAT batch, alongside the known page-scroll follow-up noted above. Phase 3 verification (`03-VERIFICATION.md`) can now run against a complete gap-closure set.

---
*Phase: 03-ai-chat-copilot*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: frontend/components/chat/ChatPanel.tsx
- FOUND: .planning/phases/03-ai-chat-copilot/03-UI-SPEC.md
- FOUND: .planning/phases/03-ai-chat-copilot/03-07-SUMMARY.md
- FOUND: commit 51e37c7
- FOUND: commit 48f0da5
