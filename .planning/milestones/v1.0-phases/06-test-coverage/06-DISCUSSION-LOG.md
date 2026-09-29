# Phase 6: Test Coverage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-27
**Phase:** 06-test-coverage
**Areas discussed:** Backend coverage strategy, Frontend test framework, E2E fresh-start & fixtures, CI / local-only scope

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Backend coverage strategy | Audit existing 228 tests vs. TEST-01/02/03, close gaps only | ✓ |
| Frontend test framework | Vitest+RTL vs Jest+RTL; SSE/EventSource mocking approach | ✓ |
| E2E fresh-start & fixtures | Fresh DB volume semantics; deterministic mocked chat triggers | ✓ |
| CI / local-only scope | GitHub Actions pipeline vs. local-only runnability | ✓ |

**User's choice:** "whatever you want" — deferred all four areas to Claude, matching the precedent set in Phase 2 and Phase 5 CONTEXT.md ("you choose everything, I trust you").

**Notes:** Before finalizing decisions, Claude scouted the actual codebase state rather than assuming a blank slate: found 228 passing backend tests already covering most of TEST-01/02/03 (including insufficient-cash/shares and malformed-LLM-response cases), zero frontend test infrastructure, and a `test/` E2E directory containing only stray untracked `node_modules`/`test-results` (safe to treat as empty). This grounding directly shaped D-01 (audit-and-close-gaps rather than rewrite) and D-03/D-04/D-05 (frontend framework choices made against a genuinely clean slate).

---

## Claude's Discretion

All four areas — backend coverage strategy (D-01, D-02), frontend test framework and mocking (D-03, D-04, D-05), E2E fresh-start semantics and fixture strategy (D-06, D-07, D-08), and CI scope (D-09) — were left to Claude's judgment per the user's "whatever you want" response. Full rationale for each decision is recorded in `06-CONTEXT.md`.

## Deferred Ideas

None — no scope-creep suggestions came up during this discussion.
