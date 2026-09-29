# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-09-29
**Phases:** 6 | **Plans:** 34 | **Tasks:** 76

### What Was Built
- Complete backend trading engine: SQLite schema, portfolio math, market-order execution, watchlist mutation behind REST endpoints (Phase 1)
- Next.js dark-terminal frontend wiring live SSE prices, trade bar, positions table, and header to the backend (Phase 2)
- AI chat copilot via LiteLLM → OpenRouter, structured output, auto-executing trades/watchlist changes through the same validation path as manual actions (Phase 3)
- Portfolio visualization: sparklines, main chart, treemap heatmap, P&L history chart (Phase 4)
- Single-container Docker packaging (multi-stage Node→Python build), idempotent start/stop scripts for macOS/Linux and Windows (Phase 5)
- Full automated test coverage: 231 backend pytest, 111 frontend Vitest/RTL, 13-spec Playwright E2E suite (Phase 6)

### What Worked
- **Tracer-first / vertical-slice planning.** Every phase led with one thin, real, end-to-end slice (one BUY order end-to-end in Phase 1; one live price + one trade in Phase 2) before expanding. Phase 1's walking-skeleton tracer landed first and every later plan extended it without rework.
- **Deferring frontend test infrastructure to Phase 6** rather than bootstrapping it mid-Phase-2 for a single wave of UI work — avoided setup cost with no second consumer yet, and Phase 6 owned it project-wide from a clean slate.
- **Normalize-once, reuse-everywhere as a bug-class fix, not a point fix.** The G-03-6 data-loss bug (validator and executor independently re-deriving a normalized value, diverging on a padded string) was fixed by collapsing to one normalization call reused by both — this pattern prevented the *class* of validator/executor divergence, not just the one reported instance.
- **Live, non-mocked reproduction as the actual bar for "verified," not code inspection.** Repeatedly, code that looked structurally correct (05-04's `$args` guard, 05-05's host-argv cross-check) had a real bypass only a live invocation surfaced. The project's verification discipline increasingly insisted on live reproduction over structural grep as the gap-closure lineage matured.
- **Independent, non-trusting re-verification chains.** Phase 5's final gap-closure plan (05-06) was verified four separate times by four different roles (orchestrator, security auditor, code reviewer, phase verifier), each explicitly declining to trust the prior pass's narrative and re-deriving evidence itself (building fresh fault-injection harnesses, re-running live daemon reproductions). This caught nothing further wrong, but it's the reason the final "14/14, status: passed" verdict is trustworthy rather than assumed.

### What Was Inefficient
- **The Windows launcher argument-guard bug took 6 gap-closure waves (05-02 → 05-06) to genuinely close.** Each fix closed the specific reproduction the prior pass found but left a structurally similar bypass in the same validation logic (declared switch → silent acceptance → `$args`-only guard → colon-token bypass → host-argv cross-check → cross-check's own fail-open branch). A more adversarial first-pass threat model on the *class* of "PowerShell argument parsing is host-dependent and not fully enumerable" might have caught more of this in one or two waves instead of six.
- **A sandboxed executor agent silently cannot run PowerShell at all in this environment.** 05-06's executor did the right thing (documented the limitation honestly instead of claiming false success), but the phase lost real wall-clock time to the orchestrator having to re-derive the entire dynamic verification pass by hand afterward. Worth flagging early in any future PowerShell-heavy plan whether the executor's sandbox can invoke `powershell.exe` at all, rather than discovering it mid-plan.
- **Stale bookkeeping accumulated across phases**: Phase 5's own `/gsd-transition` silently never completed (ROADMAP.md kept reading "In Progress" for days across Phase 6's entire execution), and 8 diagnosed debug sessions from Phases 3-4 were never marked resolved even though their fixes shipped in named gap-closure plans. Neither was a real defect, but both required manual reconciliation at milestone close instead of being caught closer to when they happened.

### Patterns Established
- **Gap-closure plans get their own wave, numbered sequentially after the phase's main waves** (e.g. 05-03 through 05-06), each with a frontmatter `gap_closure: true` marker and an explicit list of gap IDs closed, rather than silently folded into a "fix" commit.
- **Threat register rows track their own re-opening history inline** (e.g. `T-05-08 (amended by 05-04, reopened 2026-09-24, residual reopened 2026-09-27)`), so the security record's own history is legible without cross-referencing commit logs.
- **PowerShell scripts stay pure ASCII, always** — Windows PowerShell 5.1's `-File` invocation reads a BOM-less script via the system codepage, not UTF-8; a stray em-dash or curly quote corrupted live execution invisibly to structural checks once.

### Key Lessons
1. Structural/static verification ("the code looks right") and dynamic verification ("the code behaves right when actually invoked") are not substitutes for each other — this project's most persistent bug class (the Windows argument guard) was only ever fully closed by live, adversarial, non-mocked reproduction, never by reading the diff.
2. When a subagent's sandbox blocks the exact verification a plan exists to produce, the honest move is to say so and hand off — not to claim partial success. That honesty is what let the orchestrator catch and complete the gap instead of shipping an unverified fix.
3. Independent re-verification (a different role, building its own evidence rather than reading the last one's) is cheap insurance against a false "done" — worth the extra pass on anything security- or data-loss-adjacent, even after the primary fix looks solid.
4. Bookkeeping debt (a stale roadmap status, an unmarked-resolved debug session) is easy to defer indefinitely because nothing forces the deferral to surface — until a milestone-close audit specifically goes looking for it. A periodic light-touch audit mid-milestone (not just at close) would have caught these sooner.

### Cost Observations
- Sessions: this milestone closed across multiple sessions spanning 2026-09-12 through 2026-09-29 (17 days).
- Notable: Phase 5's final gap-closure cycle (05-06 plus its re-verification chain) was disproportionately expensive relative to its code footprint (2 PowerShell files, ~70 changed lines) because of the number of independent verification passes required to trust it — a deliberate tradeoff for a security-relevant fix with a history of looking-fixed-but-wasn't, not a sign the process should default to that much rigor for every change.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | multi | 6 | First milestone — vertical-MVP roadmap structure, tracer-first plans, and independent multi-pass re-verification for security-relevant gap closures all established here |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 231 backend + 111 frontend + 13 E2E specs | Full trading loop (watch → trade → chat → visualize → package → verify) | 0 — no new runtime dependencies beyond what Phases 1-4 already introduced |

### Top Lessons (Verified Across Milestones)

1. Dynamic, live reproduction beats structural inspection for anything with host/environment-dependent behavior (v1.0).
2. Honest partial-completion reporting from a constrained agent is more valuable than a confident but unverified claim (v1.0).
