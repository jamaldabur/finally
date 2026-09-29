---
status: diagnosed
trigger: "the collapse button when collapsed isn't nice (the vertical 'Chat' label is broken, make it horizontal)"
created: 2026-09-21T14:00:00Z
updated: 2026-09-21T15:10:00Z
symptoms_prefilled: true
goal: find_root_cause_only
gap_id: G-03-4
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-29
  status: diagnosed
---

## Current Focus

hypothesis: CONFIRMED (two contributing causes, AND-gate fires). The collapsed "rail" is not a rail at all — it renders as a 48x59px chip pinned to the top-right corner, because `h-full` on ChatPanel's wrapper suppresses the flex `stretch` that gives every sibling column its full height. Inside that 59px chip the rotated "Chat" label is flush against the bottom border with zero padding, which is what reads as "broken." The vertical orientation is a second, independent contributor: it is correctly applied, but it mismatches the upright chevron directly above it and buys nothing, because "Chat" fits horizontally in the 48px rail with room to spare.
test: complete — measured in a real headless Chromium against the actual production build (frontend/out), not source inference
expecting: n/a — investigation concluded
next_action: none — goal is find_root_cause_only. Report delivered. Do NOT fix.

bug_class: Bohrbug (fully deterministic; layout is viewport-independent — the chip measures 59.05px at every viewport because its height is content-driven)

reasoning_checkpoint:
  hypothesis: "Two independent causes compound. (1) LAYOUT: ChatPanel.tsx:73's wrapper carries `h-full` (height:100%). Its containing block — page.tsx:23's `div.flex flex-1 gap-6 p-6` — has a *specified* height of `auto` (flex-1 sets flex-basis, not height), so the percentage resolves to auto = content height; and because the computed cross size is not `auto`, `align-items: stretch` is disabled, so the wrapper cannot be stretched either. Result: a 48x59px chip instead of an 841px rail. (2) ORIENTATION: `[writing-mode:vertical-rl]` is applied exactly as specified by 03-UI-SPEC.md, but inside the 59px chip the 25px rotated word is flush against the bottom border, and it sits under an upright horizontal chevron, so the control mixes two reading orientations."
  confirming_evidence:
    - "Real built app, headless Chromium, 1600x950: ChatPanel wrapper = 48 x 59.05px while its sibling `main` = 864 x 841px and the row flex container = 1600 x 889px. The rail is 782px shorter than the column it lives in."
    - "EXPERIMENT A — setting the wrapper to `height:auto` in the live page makes wrapper AND rail jump to 841px, matching `main` exactly. One property, whole defect."
    - "EXPERIMENT B — keeping `height:100%` and forcing `align-self:stretch` leaves it at 59.05px, proving stretch is disabled by the non-auto cross size (flexbox spec: stretch applies only when the computed cross size is `auto`), not merely unrequested."
    - "Compiled production CSS (frontend/out/_next/static/chunks/4360hqhpo7-hv.css) contains `.[writing-mode\\:vertical-rl]{writing-mode:vertical-rl}` and getComputedStyle reports writingMode='vertical-rl', textOrientation='mixed' — the arbitrary property compiles and applies correctly."
    - "Vertical label inline extent = 25.05px; horizontal 'Chat' at the same 12px/500 = 25.05px. Identical to two decimals — font metrics are fully preserved in vertical writing mode, letterSpacing='normal', nothing collapses."
    - "Rail inner width = 48 - 2x1px border = 46px. 'Chat' horizontal needs 25.05px, leaving ~10.5px each side. Even the spec's Micro/Badge role ('CHAT', 10px/600/tracking-wide) needs only 26.09px. No widening is required."
    - "AND-GATE TEST — horizontal label with `h-full` retained still renders a 48x50px chip. Doing only what the user literally asked for does not fix what the user actually saw."
  falsification_test: "Any of: (a) the writing-mode rule absent from the compiled bundle or overridden at computed-style level; (b) vertical text metrics differing from horizontal (collapsed letter-spacing / failed glyph rotation); (c) horizontal 'Chat' failing to fit inside 46px; (d) the wrapper measuring full column height, making the chip theory wrong. All four tested; all four came back negative."
  fix_rationale: "n/a — diagnosis only, no fix applied this session"
  blind_spots: "Measured in headless Chromium on Windows; headless disables ClearType subpixel AA for ALL text, so I could not measure whether rotated glyphs additionally lose subpixel rendering on the user's real desktop Chrome (a known platform behavior that would make the 12px rotated label look thinner/fuzzier than its horizontal twin). This can only aggravate, never cause, the defect — the geometry findings stand independently. I also could not observe the user's exact viewport, but the chip's height is content-driven and viewport-invariant. Stubbed API responses were used to hydrate the app; they affect sibling panel content, not the chat wrapper's height (verified: rail stayed chip-sized in a second, independently-built harness with different sibling content)."
  candidate_causes:
    - "code: `h-full` on ChatPanel's wrapper disables flex stretch and resolves to content height - CONFIRMED (primary)"
    - "design-contract/config: 03-UI-SPEC.md prescribes a rotated vertical label (Copywriting Contract + Dock placement) - CONFIRMED (secondary)"
    - "build/config: Tailwind v4 failing to emit or purge the arbitrary [writing-mode:vertical-rl] property - REFUTED against the production bundle"
    - "environment: font-stack / vertical-writing-mode glyph or letter-spacing breakage - REFUTED (vertical inline extent == horizontal width, 25.05px both)"
    - "data: n/a - the label is a fixed static string"
  and_gate: "YES. Fixing only the orientation leaves a 48x50px chip in the corner (measured). Fixing only the height leaves a rotated 25px word under an upright chevron in an otherwise-correct rail. Neither alone produces a rail that reads as designed, so root_cause is recorded as a set of two."

## Symptoms

expected: The collapsed chat rail should be clearly visible and readable — its "Chat" label should read naturally.
actual: "the collapse button when collapsed isn't nice (the vertical 'Chat' label is broken, make it horizontal)"
errors: none — purely visual, no console errors
reproduction: Collapse the chat panel on the built app. The right column becomes a 48x59px rounded chip in the top-right corner containing an upright `«` and, jammed against the bottom border, the word "Chat" rotated 90 degrees clockwise.
started: Present since Plan 03-03 (commit cea030e) introduced `h-full` on ChatPanel's root. Carried forward unchanged by 03-04 (01cea16) and 03-05 (5049593). Reported 2026-09-21 in round-2 UAT as G-03-4.

## Eliminated

- hypothesis: "Tailwind v4 silently fails to compile/emit the arbitrary [writing-mode:vertical-rl] property (escaping bug, typo, or content-scan purge), so the label never actually rotates / renders unstyled"
  evidence: "The production bundle frontend/out/_next/static/chunks/4360hqhpo7-hv.css contains exactly one writing-mode occurrence: `.\\[writing-mode\\:vertical-rl\\]{writing-mode:vertical-rl}`. Live getComputedStyle on the real rendered element returns writingMode='vertical-rl'. Nothing else in the cascade sets writing-mode, so there is no override. The property applies exactly as authored."
  timestamp: 2026-09-21T14:30:00Z

- hypothesis: "A font-rendering interaction between vertical-rl and the project's system-sans stack breaks the glyphs (failed rotation, collapsed letter-spacing, clipped glyphs), making the label look literally broken rather than merely rotated"
  evidence: "The rotated label's inline extent measures 25.05px; the same string rendered horizontally at the same 12px/font-weight 500 in the same stack measures 25.05px. Identical to two decimals — advance widths are fully preserved under rotation. computed textOrientation='mixed' (the correct value for Latin), letterSpacing='normal'. The visual 'jammed/clipped' impression comes from the label sitting flush against the chip's bottom border with zero padding, which is a box-height defect, not a text-rendering defect."
  timestamp: 2026-09-21T14:35:00Z

- hypothesis: "The 48px rail is simply too narrow for horizontal text, so the fix requires widening the rail beyond w-12 and re-checking the WCAG 2.5.8 reasoning from G-03-2"
  evidence: "Rail inner width is 46px (48 minus two 1px borders). 'Chat' at the existing Label role (12px/500) measures 25.05px — it fits with ~10.5px of clearance on each side. 'CHAT' at the spec's existing Micro/Badge role (10px/600, uppercase, tracking-wide) measures 26.09px, also fits. Rendered and confirmed visually. No widening is needed, so the Spacing Scale's `2xl | 48px | Collapsed rail width (w-12)` row stands unchanged and no new spacing exception is required. (Separately: 03-UI-SPEC.md's Spacing Exceptions 24x24 clause governs the COLLAPSE-direction header button, not the rail; the rail is the expand direction and clears 24x24 at any of these widths anyway.)"
  timestamp: 2026-09-21T14:50:00Z

- hypothesis: "The user's complaint is purely about reading orientation, so changing writing-mode to horizontal is a sufficient fix"
  evidence: "AND-gate test in the live page: setting the label to horizontal-tb while leaving `h-full` in place yields a 48x50px chip in the top-right corner — still not a rail, still 'not nice.' The orientation change alone addresses the words of the report but not the thing being looked at."
  timestamp: 2026-09-21T15:00:00Z

## Evidence

- timestamp: 2026-09-21T14:05:00Z
  checked: frontend/components/chat/ChatPanel.tsx collapsed branch (lines 71-105)
  found: "Wrapper is `flex h-full flex-shrink-0 overflow-hidden transition-[width] ... w-12`. Rail is `flex h-full w-full flex-col items-center justify-center gap-2 rounded-lg border border-terminal-text-muted bg-terminal-panel` with NO padding utility. Children: an `«` span with no font-size class (inherits 16px from body), the `[writing-mode:vertical-rl] text-xs font-medium` label, and the conditional unread dot."
  implication: "Zero padding on the rail means its content box height IS its content height exactly — so if the box ever sizes to content, the label lands flush on the border. Also, the chevron is upright at 16px while the label is rotated at 12px: two reading orientations inside one 48px control."

- timestamp: 2026-09-21T14:30:00Z
  checked: Production CSS bundle frontend/out/_next/static/chunks/4360hqhpo7-hv.css (18669 bytes, built 2026-09-21 14:13)
  found: "Exactly one writing-mode occurrence: `.\\[writing-mode\\:vertical-rl\\]{writing-mode:vertical-rl}`. The class survives Tailwind v4 content scanning and is emitted with correct escaping."
  implication: "Candidate cause 1 (silent non-application / purge / escaping bug) is dead. The rendered result IS the coded result."

- timestamp: 2026-09-21T14:40:00Z
  checked: "Real built app served from frontend/out and driven in headless Chromium at 1600x950 with stubbed /api responses; clicked the real Collapse button; measured getBoundingClientRect + getComputedStyle on the live DOM."
  found: |
    row flex container (page.tsx:23)  = 1600 x 889px, alignItems: normal
    main (page.tsx:29, no h-full)     =  864 x 841px   <- stretches correctly
    ChatPanel wrapper (h-full)        =   48 x  59.05px <- does NOT stretch
    rail button (h-full w-full)       =   48 x  59.05px
    label span                        =   16 x  25.05px, writingMode vertical-rl, 12px/16px, weight 500
    chevron span                      = 8.09 x  24px,    writingMode horizontal-tb, 16px/24px, weight 400
  implication: "The collapsed 'rail' is a 48x59px chip floating in the top-right corner, 782px shorter than the column beside it. Content math: 24 (chevron) + 8 (gap-2) + 25.05 (label) + 2 (borders) = 59.05 — an exact content-height fit with zero slack, which is why the rotated 't' grazes the bottom border."

- timestamp: 2026-09-21T14:45:00Z
  checked: "EXPERIMENT A / EXPERIMENT B — mutating only the wrapper's height in the live page"
  found: "A: `height:auto` -> wrapper 841px AND rail 841px (the inner `h-full` then resolves correctly, because a stretched flex item has a definite cross size). B: `height:100%` + forced `align-self:stretch` -> still 59.05px."
  implication: "Mechanism pinned exactly. `height:100%` does two harmful things at once: it resolves against a containing block whose *specified* height is `auto` (page.tsx:23 is `flex-1`, which sets flex-basis, not height) so it degrades to content height; and because the computed cross size is no longer `auto`, it disables `align-items: stretch`, which is the very thing that gives `main` and the left column their full height. Removing `h-full` is therefore not a workaround — it is the correct fix, and it makes ChatPanel consistent with every sibling."

- timestamp: 2026-09-21T14:50:00Z
  checked: "Text metrics in the app's real font stack (ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif)"
  found: "'Chat' @12px/500 = 25.05px wide. 'CHAT' @10px/600 uppercase tracking-wide = 26.09px. 'Chat' @10px/600 = 20.88px. Per-letter: C 7.45, h 6.98, a 6.27, t 4.34. Rail inner width = 46px."
  implication: "Horizontal 'Chat' fits the existing 48px rail with ~10.5px clearance per side — widening the rail (candidate fix c) is unnecessary, and letter-stacking (candidate fix a) would consume 4x the vertical space to solve a problem that does not exist."

- timestamp: 2026-09-21T14:55:00Z
  checked: "Six rendered variants of the collapsed rail in the real app (as-shipped / stretch+vertical / stretch+horizontal-12px / stretch+horizontal-badge-10px / stretch+letterstack / stretch+glyph-only)"
  found: "As-shipped: 48x59 chip, label jammed on the border. Stretch+vertical: a proper 48x841 rail, but the 25px rotated word still sits under an upright chevron — two orientations, reads as an afterthought. Stretch+horizontal-12px: `«` over 'Chat', both upright, centred, comfortable margins — reads as a designed vertical tab. Letterstack: legible but slow to read and 4x taller for no gain. Glyph-only: clean but removes the only word identifying the rail."
  implication: "Stretch + horizontal 12px label is the best variant. Glyph-only would regress G-03-2's OTHER original complaint ('the collapsed rail is hard to notice/find') for sighted users — the `aria-label=\"Expand chat panel\"` covers screen readers but not the visual affordance, so the word should stay."

- timestamp: 2026-09-21T15:05:00Z
  checked: "git log -L on ChatPanel.tsx's wrapper line; grep for h-full across frontend/"
  found: "`h-full` has been on ChatPanel's root since cea030e (Plan 03-03, the original chat panel) and was carried through 01cea16 (03-04) and 5049593 (03-05) unchanged. ChatPanel's wrapper is the ONLY child of page.tsx:23's row that specifies a height — the left column (`div.flex w-80 flex-shrink-0 flex-col gap-4`) and `<main className=\"flex-1 ...\">` both omit it and stretch correctly. PositionsTable.tsx:18 also uses `h-full`, but it works there because its parent `<main>` IS stretched and therefore has a definite height."
  implication: "Pre-existing defect from 03-03, not a regression introduced by 03-05 — which explains why 03-05's debug session and plan checker never flagged it: they were scoped to contrast/affordance/motion. The prior session (.planning/debug/chat-panel-collapse-toggle.md) even asserted the rail was 'full-column-height (~800px+)' — an inference it explicitly listed under blind_spots as unverified because no browser was driven. This session drove one and the inference was wrong."

- timestamp: 2026-09-21T15:08:00Z
  checked: "ADJACENT (not the reported symptom): expanded-panel behaviour with 28 hydrated messages"
  found: "The expanded panel grows to 2419px and the message list's `flex-1 overflow-y-auto` never scrolls (clientHeight == scrollHeight == 2312); the whole page scrolls instead (document scrollHeight 2528 vs 950 viewport). Removing `h-full` does NOT fix this — the row's height is still `auto`, so it simply grows to its tallest child."
  implication: "Separate, deeper issue: nothing in the html>body>page chain establishes a definite height, so no descendant can be 'full height with internal scroll'. This is the same family as the root cause but needs its own fix (a definite-height chain, e.g. h-screen + min-h-0), and it is NOT what G-03-4 reports. Flagging so a fix plan does not accidentally conflate the two or claim the scroll behaviour is fixed by the one-line change."

## Resolution

root_cause: "TWO contributing causes; the AND-gate fires. (1) PRIMARY — LAYOUT: `h-full` on ChatPanel.tsx:73's wrapper makes the collapsed rail render as a 48x59.05px chip in the top-right corner instead of a full-height 48x841px rail. `height:100%` resolves against page.tsx:23's `div.flex flex-1 gap-6 p-6`, whose *specified* height is `auto` (flex-1 sets flex-basis, not height), so it degrades to content height; and because the computed cross size is no longer `auto`, it simultaneously disables the `align-items: stretch` that gives every sibling column (`main`, the left rail) its full height. Proven by direct measurement plus two live mutations: height:auto -> 841px; height:100% + forced align-self:stretch -> still 59.05px. Because the rail button carries no padding, the chip's height is an exact content fit, leaving the rotated label flush against the bottom border — which is the 'broken' the user is describing. Introduced in Plan 03-03 (cea030e), carried unchanged through 03-04 and 03-05. (2) SECONDARY — ORIENTATION: `[writing-mode:vertical-rl]` is applied correctly (present in the production bundle, computed style confirms it, and vertical metrics match horizontal metrics to 0.01px, so there is no rendering bug) but it is the wrong call for this control: it puts a rotated 25px word directly beneath an upright 16px chevron inside a 48px box, mixing two reading orientations, and it buys nothing because 'Chat' fits horizontally in the 46px inner width with ~10.5px clearance per side. Fixing orientation alone still leaves a 48x50px chip (measured)."
fix: "" # diagnose-only - no fix applied
verification: "" # n/a
files_changed: []
