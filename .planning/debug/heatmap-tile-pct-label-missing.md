---
status: diagnosed
trigger: "I don't see % on all stocks in heatmap (I don't see it on NVDA)"
created: 2026-09-22T01:10:00Z
updated: 2026-09-22T01:45:00Z
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-29
  status: diagnosed
---

## Current Focus

hypothesis: CONFIRMED — `PCT_MIN_WIDTH = 64` is larger than the percentage label's real rendered
  width (30-46px at 10px/600 + 8px inset = 38-54px needed). Recharts' squarify emits full-height
  narrow columns in this panel's wide-and-short chart box, so the smallest holdings land in the dead
  band (48-62px wide) where the label fits but the gate rejects it.
test: headless Chrome (own user-data-dir, CDP) against the user's running dev server, emulating
  viewport widths 1920/1600/1440/1366/1280/1200/1152, reading the real tile rects + text nodes;
  plus `getComputedTextLength()` measurement of the actual label strings in the live SVG.
expecting: a tile wide enough for its text but narrower than 64px that drops the % — found at 1280
  (NVDA 60x158, ticker only) and 1366 (GOOGL 61x172, ticker only).
next_action: none — diagnose-only mode; hand root cause back to the planner.

reasoning_checkpoint:
  hypothesis: "The percentage label is suppressed because PCT_MIN_WIDTH=64 exceeds the label's actual rendered width (~34px) plus insets (~42px total), and squarify makes low-weight tiles tall-and-narrow (width-limited) in this panel's short chart box."
  confirming_evidence:
    - "Live render at 1280px viewport: NVDA tile is 60x158 px and its <g> contains only the text node 'NVDA' — no percentage. Exactly the user's report."
    - "Live render at 1366px viewport: GOOGL tile is 61x172 and shows only 'GOOGL'. Same failure, different ticker."
    - "getComputedTextLength() in the live SVG at 10px/600: '+6.27%'=34.27px, '-5.31%'=29.97px, '+17.17%'=36.53px, worst realistic '+999.99%'=45.67px. With TILE_INSET=8 the label needs 38-54px, not 64px."
    - "Live render at 1920px viewport: box 543x172, tiles 272x172 / 271x80 / 271x92 — every tile shows ticker AND %. The defect is width-regime-dependent, which is why it was not seen during implementation."
  falsification_test: "If the thresholds were correct, no tile with enough room for its text would drop it. A 60x158 tile (44px of inner width available, 34.3px of text) dropping the label refutes 'working as specified'."
  fix_rationale: "N/A this session (goal: find_root_cause_only). The fix direction is to gate on measured/estimated text extent instead of fixed rectangle constants."
  blind_spots: "The user's exact viewport width is unknown; 1280 reproduces their sentence verbatim but 1152-1400 all produce some unlabelled tile. Tiles were only exercised with the 3 real positions; 4+ positions were not enumerated (not needed — the failure is already reproduced)."
  candidate_causes:
    - "code: PCT_MIN_WIDTH/TICKER_MIN_WIDTH constants exceed real text metrics (CONFIRMED, primary)"
    - "config/layout: the h-60 panel in a 2-up flex row fixes the chart box at 158-172px tall, so squarify lays out along height and width becomes the binding dimension (CONFIRMED contributing condition, by design)"
    - "environment: browser window <=~1400px wide (CONFIRMED trigger condition)"
    - "data: backend returns positions ORDER BY ticker, not descending by value, which squarify assumes (REFUTED as a cause — see Eliminated)"
  and_gate: "yes — the symptom needs (a) an over-large width constant AND (b) a chart box short enough that squarify emits narrow full-height columns. (b) is the panel's normal geometry at common laptop widths; (a) is the defect."

## Symptoms

expected: Tiles sized by market value; pale->vivid fill capped at 10%; labels drop percentage first,
  then ticker, only on genuinely small tiles; hover tooltip shows weight and change.
actual: "I don't see % on all stocks in heatmap (I don't see it on NVDA)". Tiles render normally.
errors: none
reproduction: UAT Test 3 — hold positions of differing size/P&L and look at the heatmap. Deterministic
  repro: load the app at a 1280px-wide viewport with the three live positions.
started: UAT immediately after phase 04 execution (plan 04-03).

## Eliminated

- hypothesis: "Recharts 3.10.1 does not pass `ticker`/`pct_change` through to the `content` element
    (the risk flagged in 04-UAT Test 3)"
  evidence: recharts/es6/chart/Treemap.js `computeNode` spreads the raw datum (`{...node, ...}`) and
    `TreemapItem` spreads `nodeProps` into the cloned content element; live DOM shows correct
    per-tile fills derived from `pct_change` and correct ticker text. Props arrive.
  timestamp: T2

- hypothesis: "The tiles are genuinely too small — design working as specified"
  evidence: the failing tiles are 60x158 and 61x172 px (9.4-10.5k px^2, 23-28% portfolio weight) and
    the label they refuse to draw measures 30-37px. They are not small; they are narrow.
  timestamp: T5

- hypothesis: "Text is rendered but clipped / invisible / low-contrast"
  evidence: the `<text>` node for the percentage is entirely absent from the DOM on failing tiles
    (`texts: ["NVDA"]`), not present-but-hidden. Contrast is also identical for both labels, so it
    could not hide one and not the other.
  timestamp: T5

- hypothesis: "PCT_MIN_HEIGHT=42 is the binding constraint"
  evidence: every observed failing tile was 158-172px tall. Height never gated. (42 is still ~6px
    over-strict versus the real need of ~36px, but it is not this bug.)
  timestamp: T5

- hypothesis: "Unsorted input (backend `ORDER BY ticker`) is the cause — squarify assumes descending"
  evidence: replayed squarify with the same values sorted descending at 223x158 and 266x172; the
    smallest tile is still a 52-62px full-height strip that fails the 64px gate. Sorting only changes
    WHICH ticker loses its label, not whether one does.
  timestamp: T6

## Evidence

- timestamp: T1
  checked: frontend/components/charts/PortfolioHeatmap.tsx
  found: `TICKER_MIN_WIDTH=52 / TICKER_MIN_HEIGHT=26`, `PCT_MIN_WIDTH=64 / PCT_MIN_HEIGHT=42`,
    `TILE_INSET=8`; both labels gated by a fixed `width >= W && height >= H` rectangle test.
  implication: gates are constants, never compared against the text actually being drawn.

- timestamp: T2
  checked: recharts 3.10.1 es6/chart/Treemap.js (squarify, horizontalPosition, verticalPosition)
  found: `size = Math.min(rect.width, rect.height)`; `position()` picks vertical strips whenever
    `size !== rect.width`. Default aspectRatio = golden ratio, nodeInset/nodeGap = 0, treemap margin = 0.
  implication: in a wide-and-short box the algorithm emits full-height columns — width is the
    binding dimension for small holdings, exactly the dimension the pct gate over-specifies.

- timestamp: T3
  checked: db/finally.db (read-only) and live `GET http://localhost:8000/api/portfolio`
  found: three positions during UAT — AAPL 1.5 @183.93, GOOGL 1.0 @156.93, NVDA 1.0 @162.44
    (last trade 2026-09-21T21:47:52, UAT ran 00:00-00:50). Live weights AAPL 49.2%, NVDA 27.5%,
    GOOGL 23.3%.
  implication: only three tiles, none tiny; NVDA is the second-largest holding.

- timestamp: T4
  checked: rendered page in headless Chrome (own user-data-dir, CDP, stopped by PID afterwards)
  found: heatmap chart box measures panel_width - 34 by 172px (158px once the panel header wraps).
    Per emulated viewport width:
      1920 -> box 543x172; AAPL 272x172 (+17.27%), GOOGL 271x80 (-5.12%), NVDA 271x92 (+6.35%) — all labelled
      1600 -> box 383x172; all three labelled
      1440 -> box 303x172; tiles 152 / 70 / 81 wide x172 — all labelled (70 and 81 clear 64 by 6 and 17px)
      1366 -> box 266x172; GOOGL tile 61x172 shows "GOOGL" only, NO percentage
      1280 -> box 223x158; NVDA tile 60x158 shows "NVDA" only, NO percentage  <-- user's exact report
      1200 -> box 183x158; third tile 49x158 shows NO text at all (also fails TICKER_MIN_WIDTH=52)
      1152 -> box 178x158; third tile 48x158 shows NO text at all
  implication: the failure is a width cliff at 64px that the panel crosses at ~1400px viewport and
    below; a second cliff at 52px removes the ticker too below ~1220px.

- timestamp: T5
  checked: `getComputedTextLength()` on SVG text at fontSize 10 / fontWeight 600 with the app's own
    font stack (`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`)
  found: AAPL 24.17px, NVDA 27.83px, GOOGL 33.95px (longest ticker);
    "-5.31%" 29.97px, "+6.27%" 34.27px, "+17.17%" 36.53px, "-100.00%" 41.08px, "+999.99%" 45.67px.
  implication: with TILE_INSET=8 on the left, a percentage needs 38-54px of tile width (typically
    ~42px) — the gate demands 64px, i.e. ~22px (50%) more than typical. The ticker needs <=42px and
    the gate demands 52px. Both constants are over-strict; the pct one is over-strict enough to bite
    on tiles the layout routinely produces.

- timestamp: T6
  checked: .planning/phases/04-portfolio-visualization/04-RESEARCH.md (A2), 04-03-SUMMARY.md,
    04-UI-SPEC.md (UI Considerations, overflow row)
  found: UI-SPEC conditions the drop on "weight too small for its label to fit" and "text is never
    clipped". 04-RESEARCH A2 pre-flagged: "The exact pixel thresholds are unverified against real
    rendered text metrics — the executor should measure actual 10px/600 glyph width rather than trust
    these illustrative numbers verbatim." 04-03-SUMMARY recorded them as "tunable at UAT".
  implication: this is an implementation defect against the spec, not spec'd behaviour the user
    dislikes. The spec's own condition (label does not fit) is false for the failing tiles.

## Resolution

root_cause: >
  `PCT_MIN_WIDTH = 64` (and, one step further down, `TICKER_MIN_WIDTH = 52`) in
  frontend/components/charts/PortfolioHeatmap.tsx are fixed pixel constants that exceed the real
  rendered width of the text they gate — measured in the live app at 10px/600, a percentage label is
  30.0-45.7px wide and needs only ~42px of tile width including the 8px inset (54px worst case),
  while a ticker needs <=42px. Because Recharts' squarify lays tiles out along the SHORTER side of
  the chart box, and this panel's chart box is permanently short (158-172px tall, fixed by the `h-60`
  panel shell in a two-up row) while its width shrinks with the viewport, low-weight holdings become
  full-height columns 48-62px wide. Their width lands in the dead band between "fits the text" (~42px)
  and "passes the gate" (64px), so the percentage is suppressed on a 60x158 px tile holding 27.5% of
  the portfolio. That contradicts UI-SPEC 04's overflow rule, which drops a label only when the tile
  is "too small for its label to fit". Contributing (not causal) condition: a browser viewport at or
  below ~1400px wide — at 1920px every tile is >=271px wide and all labels appear, which is why the
  defect was not seen at implementation time.
fix: (not applied — diagnose-only session)
verification: (n/a)
files_changed: []
