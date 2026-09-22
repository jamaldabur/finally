# Phase 5: Docker Packaging & Deployment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 5-docker-packaging-deployment
**Areas discussed:** SQLite volume strategy, dev-only CORS middleware, start/stop script behavior, docker-compose.yml inclusion

---

## Gray areas presented

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite volume strategy | Bind-mount `db/` vs named Docker volume, given Windows host path-translation implications | |
| Dev-only CORS middleware | Strip in prod, gate behind env var, or leave as-is — flagged directly in `main.py`'s own comment as a Phase 5 decision | |
| Start/stop script behavior | Auto-open browser? Rebuild detection? Re-run idempotency behavior? | |
| docker-compose.yml inclusion | Include the optional convenience wrapper or skip it, since REQUIREMENTS.md doesn't require it | |

**User's choice:** "You decide, choose the best" (free-text response to the multi-select prompt) — deferred all four areas to Claude's judgment in one turn, rather than discussing individually.
**Notes:** Same pattern as Phase 2's discussion, where the user also deferred all gray areas to Claude ("You choose everything, I trust you").

---

## Claude's Discretion

All four presented areas, decided and recorded in `05-CONTEXT.md`:

- **SQLite volume strategy** → bind-mount the repo's `db/` directory (resolves a literal PLAN.md §4 vs §11 inconsistency in favor of §4's more specific directory-structure spec); absolute-path resolution in both scripts for Windows Docker Desktop reliability (D-01, D-02)
- **Dev-only CORS middleware** → left in place unconditionally; inert in same-origin Docker deployment, not worth the added complexity of gating it (D-03)
- **Start/stop script behavior** → build-if-missing-or-`--build`, no-op idempotent re-runs in both directions, best-effort browser auto-open, `.env` existence check with a pointer to `.env.example` (D-06 through D-09)
- **docker-compose.yml** → not created this phase; optional per PLAN.md §11 and not required by DEPLOY-01..04 (D-10)

Two additional implementation decisions were made without a separate gray-area prompt, since PLAN.md leaves them effectively unambiguous once the above were settled:
- Static frontend serving via `StaticFiles(directory="static", html=True)` mounted after all API routers (D-04) — PLAN.md §3 already specifies this architecture directly.
- Container `HEALTHCHECK` against `GET /api/health` via Python's stdlib rather than `curl`, since `python:3.12-slim` doesn't ship `curl` (D-11).

## Deferred Ideas

None — no scope-creep suggestions came up during this discussion; the user deferred implementation choices rather than proposing new capabilities.
