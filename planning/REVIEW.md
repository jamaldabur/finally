# REVIEW.md

This file accumulates review passes over the project. Each section below is a distinct pass, kept in full and in chronological order.

---

# Review 1: PLAN.md Specification Review

Fresh pass over `planning/PLAN.md` looking for ambiguities, cross-section inconsistencies, missing specification that would let two implementers build incompatible things, and simplification opportunities. Organized by severity, with section references back to PLAN.md.

---

## A. Inconsistencies (doc contradicts itself)

### A1. The watchlist ticker whitelist contradicts the LLM example (§6 vs §9)
§6 says: "Only tickers with a defined seed price/sector are supported. Watchlist additions... for an unrecognized ticker are rejected with an error." The only tickers given seed price/sector in §6 are the 10 default tickers (AAPL/GOOGL/MSFT/AMZN/NVDA/META, JPM/V, TSLA/NFLX) — which are also the entire default watchlist (§7). If that's really the full universe, **no ticker can ever be successfully added** — every add attempt is either already on the watchlist or unrecognized.

Yet §9's structured-output example shows the LLM adding `PYPL`, a ticker with no defined seed/sector anywhere in the doc. As written, that example call would always be rejected with an error, which seems unintentional.

**Needs a decision**: either (a) define a larger fixed universe of supported tickers (e.g. 30-50 symbols with seed price + sector) and pick the §9 example from it, or (b) change the §9 example to a ticker actually outside the seed 10 but pull it from that expanded list. Right now Backend and Frontend/LLM-prompt implementers have no shared source of truth for "which tickers are addable," and will likely build incompatible assumptions.

### A2. Does the ticker whitelist apply when using real market data (Massive)? (§6)
The rejection rule in §6 is stated under "Simulator (Default)," but §9's watchlist-validation function is described as one single code path regardless of data source. If `MASSIVE_API_KEY` is set, does the whitelist still cap the app at 10(ish) hardcoded tickers, or can users watch any real symbol Massive can quote? As written the restriction reads as global, which would make the Massive integration pointless (why integrate a real data API you can only ever point at 10 fixed tickers?). Worth an explicit sentence either way.

### A3. Docker persistence mechanism: named volume vs. bind mount (§4 vs §11)
§4 says: "`db/` at the top level is the runtime volume mount point... persists across container restarts via Docker volume," implying the local `./db` directory is bind-mounted.

§11's example command is: `docker run -v finally-data:/app/db ...` — this is a **named Docker volume** (`finally-data`), not a bind mount of the local `db/` directory. A named volume is an opaque Docker-managed store; a student would not see `finally.db` appear in their local `db/` folder with this command, which contradicts §4's framing (and the `db/.gitkeep` / "SQLite file lives here at runtime" language in the directory tree). Pick one — a bind mount (`-v ./db:/app/db`) better matches the "zero config, self-contained, file the student can see/back up" spirit described elsewhere — and make §4, §11, and the start scripts consistent.

### A4. `docker-compose.yml` role contradicts its own rationale (§3 vs §4)
§3's rationale table states "Single Docker container | Students run one command; no docker-compose for production, no service orchestration." §4 then lists `docker-compose.yml` at the project root as "Optional convenience wrapper" with no further qualification. If it's dev-only tooling, say so explicitly next to the table row so it doesn't read as walking back the "no docker-compose" decision; if it's meant for something else, say what.

### A5. "Canvas-based charting library preferred (Lightweight Charts or Recharts)" (§10)
Recharts is SVG-based, not canvas-based — the two named options don't both satisfy the stated constraint. Either drop the "canvas-based" qualifier, drop Recharts from the list, or rephrase (e.g. "a performant charting library — Lightweight Charts (canvas) preferred, Recharts acceptable for simpler charts").

### A6. Automatic browser launch: guaranteed vs. optional (§2 vs §11)
§2 "First Launch" states as fact: "A browser opens to `http://localhost:8000`." §11 describes the start script as "Optionally opens the browser." If it's actually optional/best-effort (e.g. `open`/`start` may not be available in all environments), §2 should be softened to match, otherwise the two sections describe different guaranteed behavior.

---

## B. Missing specification (would let two implementers diverge)

### B1. Trading a ticker not on the watchlist (§8, §10, §6)
The price cache only holds prices for "tickers known to the system," described elsewhere as equivalent to the watchlist (§6, SSE section). `POST /api/portfolio/trade` takes `{ticker, quantity, side}` with no stated restriction to watchlist membership, and the Trade Bar (§10) doesn't say whether the ticker field is constrained to current watchlist entries. If a user (or the LLM) submits a trade for a ticker that isn't being watched, where does the fill price come from? Options: (a) trades are restricted to watchlist tickers only (reject otherwise), (b) an unwatched ticker is implicitly added to the watchlist as part of the trade, (c) price is fetched on-demand outside the cache. This needs an explicit rule — it affects backend validation, the trade bar UI, and the LLM's trade-execution behavior.

### B2. SSE event wire format is underspecified (§6, "SSE Streaming")
The doc says the server "pushes an event for all tickers known to the system at a regular cadence" and each event "contains ticker, price, previous price, timestamp, and change direction." It's not clear whether:
- this is **one SSE event per tick containing an array of all tickers**, or **one SSE event per ticker** (many events per tick), and
- what the literal field names/JSON shape are, and
- what values "change direction" takes (e.g. `"up" | "down" | "unchanged"`? or an omitted field when unchanged?).

Frontend and backend are built by different agents against this contract — an explicit example payload would prevent drift.

### B3. "Recent conversation history" has no bound (§9 step 2, §8 `GET /api/chat`)
Both the prompt-construction step and the hydration endpoint refer to "recent"/"recent conversation history" without a count or time window. Since `chat_messages` grows unboundedly (no pruning, matching the `portfolio_snapshots` policy), this needs an explicit cap (e.g. "last 20 messages") both to bound LLM context/cost per request and to bound what `GET /api/chat` returns on page load.

### B4. `GET /api/portfolio/history` has no range/limit (§7, §8)
`portfolio_snapshots` rows are explicitly never pruned and accumulate every 30s plus on every trade. `GET /api/portfolio/history` has no stated limit, offset, or time-range parameter, so a long-running session could return an ever-growing payload on every chart load. Worth at least a default limit or downsampling note, or an explicit "return everything, acceptable for demo scope" statement so implementers don't disagree.

### B5. LLM mock response behavior is unspecified but load-bearing for E2E tests (§5, §9, §12)
`LLM_MOCK=true` must "return deterministic mock responses," and one required E2E scenario is "AI chat (mocked): send a message, receive a response, trade execution appears inline" — meaning the mock must, for *some* known input, emit an actual `trades` action, not just message text. But nothing in §9 specifies the mock's decision logic (keyword matching on the user's message? fixed canned response regardless of input? a special test-only trigger phrase?). Since the Backend agent builds the mock and a different test-writing agent builds the E2E scenario, they need a shared contract for at least one deterministic "this input produces a trade action" case — otherwise the two are likely to disagree independently.

### B6. HTTP status/error-body convention for validation failures (§8, §9)
Nothing specifies the response shape/status code when a trade or watchlist action fails validation (insufficient cash, selling more than owned, duplicate watchlist add, removing a ticker not on the watchlist, unrecognized ticker). §8 only calls out 400 for the unrecognized-ticker watchlist case. Since the same validation function backs both the direct REST endpoints (§8) and the chat auto-execution annotation (§9 step 7, "executed" vs "error" + reason), a single documented error shape (status code + body field names) would keep the trade bar's error handling and the chat panel's inline badges consistent.

### B7. Position lifecycle at zero quantity (§7 `positions`)
When a sell reduces a position's `quantity` to 0, is the row deleted, or retained with `quantity=0`? This affects the positions table, the heatmap (a 0-weight rectangle?), and whether a `UNIQUE(user_id, ticker)` re-buy after a full exit is a fresh INSERT or an UPDATE. Also unstated: `avg_cost` recalculation method on partial sells — presumably unchanged (standard weighted-average-cost behavior, where only buys move `avg_cost`), but this should be said explicitly since it's the crux of the P&L math the unit tests (§12) are supposed to cover.

### B8. `OPENROUTER_API_KEY` is marked "Required" but the app has key features that don't need it (§5)
Watchlist, prices, and portfolio/trading work with no LLM involved, and `LLM_MOCK=true` bypasses OpenRouter entirely. Should the app fail to start if the key is absent and `LLM_MOCK` is false, or only fail lazily when `/api/chat` is actually called? "Required" as currently worded suggests a hard startup dependency that the rest of the spec doesn't otherwise justify.

### B9. Main chart's data source on ticker switch (§2 vs §10)
§2 states sparklines are "accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)" — implying no backend history endpoint feeds them. §10's "Main chart area" doesn't restate this, so it's implicit rather than confirmed that the big chart draws from the same in-browser SSE buffer (and therefore also starts sparse on first load / right after selecting a ticker that hasn't accumulated many ticks yet). Worth one explicit sentence so no implementer builds a `/api/prices/history/{ticker}` endpoint that the rest of the spec doesn't otherwise mention, and so the empty-chart-on-load behavior is understood as intentional, not a bug.

### B10. `watchlist_changes.action` enum not fully stated (§9)
The example only shows `"action": "add"`. §8's DELETE endpoint implies removal is also a valid LLM-driven action ("Manage the watchlist" via chat, §2), but the schema section never explicitly enumerates `"add" | "remove"`. Small gap, easy fix.

### B11. GBM parameters' configuration mechanism (§6)
"Configurable drift and volatility per ticker" doesn't say *where* — hardcoded per-ticker constants in the simulator module, a config file, or env vars? Given "Simulator... no external dependencies" is a stated virtue, a hardcoded per-ticker table is probably intended, but it's worth pinning down so the ticker-universe question (A1) and this land in the same place.

---

## C. Simplification opportunities

1. **Resolve A1/A2 together with one concrete list.** Add a short explicit table of the full supported-ticker universe (symbol, seed price, sector) to §6 or §7 — even if it's larger than the default 10 — so both the simulator seed data and any watchlist-add validation (manual, and the §9 LLM example) reference the same list. This single addition would close A1, A2, and B11 at once.

2. **Pick bind-mount over named volume** for the SQLite file (resolves A3) — it's more in keeping with "self-contained, zero config" and lets a student inspect/back up `finally.db` directly, which the rest of the doc's framing (`db/.gitkeep`, "SQLite file lives here at runtime") already assumes.

3. **Define one error-response shape once** (e.g. `{"error": "insufficient_cash", "detail": "..."}` with 400) and reference it from both §8 (trade/watchlist endpoints) and §9 (chat action annotation), rather than leaving each call site to invent its own. Removes B6 and keeps the "one validation function, two entry points" design (§9 step 6) honest all the way to the wire format.

4. **Give the SSE payload a two-line JSON example** (resolves B2) — this is cheap to add and is the single highest-leverage clarification for keeping the Frontend and Backend agents' contracts aligned, since SSE is the most continuously-active integration surface in the app.

5. **State the chat-history window as a number** (resolves B3) in one place (e.g. "the last 20 messages, oldest first") and have both §8's `GET /api/chat` and §9 step 2 reference that same number, rather than each independently deciding what "recent" means.

---

## Summary

Most of the plan is internally solid and unusually precise for a spec of this size (the SSE flash-vs-heartbeat distinction, the heatmap color-saturation cap, and the single-validation-path design for trades/watchlist are all good examples of ambiguity pre-empted correctly). The issues found cluster around two areas that were specified in one section but not carried through consistently to the sections that depend on them:

- **The ticker universe** (A1, A2, B11) — the simulator's whitelist rule and the LLM's example action directly contradict each other, and this is the one finding likely to actually break a demo (an agent following §9 literally will build an LLM that tries to add PYPL and always gets an error back).
- **Docker persistence** (A3, A4) — the volume-mount example contradicts the directory-structure narrative, which matters because start/stop scripts, the Dockerfile, and the "data persists across restarts" promise all depend on picking one mechanism.

Everything else is either a missing bound/format on an otherwise-clear feature (B2–B10) or a small wording contradiction (A5, A6) that's quick to fix. None of the frontend visual/UX sections (§2, §10 layout) or the testing strategy's scenario list (§12) have structural problems — the gaps there are in the *supporting* mock/data contracts (B5) rather than the test list itself.

---

# Review 2: Stop-Hook Automation Experiment (Abandoned) (2026-09-12)

This session tried to automate change review by wiring a `Stop`-event hook to spawn a review agent on every turn, writing results to `planning/REVIEW.md` automatically. The implementation went through two shapes: first an inline `type: "agent"` hook in `.claude/settings.json`, then migrated into a dedicated local plugin (`independent-reviewer/`, registered via a root `.claude-plugin/marketplace.json`).

Across repeated test runs, in both shapes, the hook's spawned review agent consistently completed its analysis of the diff but was denied `Write`/`Edit`/`Bash`/`PowerShell` tool access in "don't-ask" permission mode. This held regardless of: a `tools` array on the hook (not part of the documented hook schema), an explicit `permissions.allow` grant (`Write`/`Edit` scoped to `planning/REVIEW.md`), a `/hooks` config reload mid-session, or moving the hook into a plugin. The restriction appeared structural to `type: "agent"` Stop hooks specifically, not something fixable through configuration — likely an intentional guardrail against unattended, automatically-triggered agents writing files with no human present to approve.

A stray uncommitted deletion of `independent-reviewer/hooks/hooks.json` (while the plugin remained enabled in `settings.json`) briefly left the config in a broken, half-removed state.

**Outcome**: The entire experiment was abandoned rather than fixed. The plugin directory, its marketplace registration, and the related `enabledPlugins`/`permissions` entries in `.claude/settings.json` were all fully reverted together — nothing from this experiment remains in the working tree. In its place, a manually-invoked `.claude/agents/change-reviewer.md` subagent now serves the same "review changes, write to REVIEW.md" purpose (see Review 3) — it inherits full session permissions and isn't subject to the same restriction, at the cost of needing to be invoked explicitly rather than firing automatically. Full config JSON and the permission-troubleshooting timeline are preserved in git history around commit `adc4509` if ever needed.

---

# Review 3: Comprehensive Project Review (2026-09-12)

Full pass over the project as it currently stands: `planning/PLAN.md`, the actual directory/file structure, the Claude Code configuration (`.claude/settings.json`, `.claude/agents/`, `.claude/commands/`, `.claude/skills/`), and any implementation code that exists. This is broader than a diff-since-last-commit review — it looks at the repo as a whole, cross-checking the plan against what's actually been built. **`frontend/` and effectively all of `backend/` are not yet implemented** — this is expected at the scaffolding stage and is called out below as status, not treated as a defect.

## Resolution note: the independent-reviewer plugin incident (Review 2) is closed

Review 2 covers a Stop-hook automation experiment that hit an unresolvable permission restriction and, along the way, briefly left `independent-reviewer/hooks/hooks.json` deleted while the plugin remained enabled in `.claude/settings.json` — an inconsistent half-deleted configuration. That situation no longer exists. The entire `independent-reviewer/` plugin directory, the root `.claude-plugin/marketplace.json` registration, the `independent-reviewer@jamal-plugins` entry in `enabledPlugins`, and the `permissions.allow` block added to support it have all been removed together as one clean revert (confirmed via `git status` and `git diff HEAD -- .claude/settings.json`: the working tree shows `.claude-plugin/marketplace.json`, `independent-reviewer/.claude-plugin/plugin.json`, and `independent-reviewer/hooks/hooks.json` all deleted, and `.claude/settings.json` reduced back to exactly:

```json
{
  "enabledPlugins": {
    "frontend-design@claude-plugins-official": true,
    "context7@claude-plugins-official": true,
    "playwright@claude-plugins-official": true
  }
}
```

— the same three plugins present at the initial commit, no hooks, no permissions block). The underlying goal (a Stop-hook-triggered automated reviewer) was abandoned rather than fixed, after repeated confirmed failures getting an agent-type Stop hook to obtain write access. In its place, a manually-invocable `.claude/agents/change-reviewer.md` subagent now exists (see below) — this is the mechanism actually producing this review. Nothing here needs further action; it's recorded for continuity so a future reader doesn't re-open a closed issue.

---

## A. Claude Code configuration review

### A1. `change-reviewer` agent is minimal but functional
`.claude/agents/change-reviewer.md` defines a subagent with just a `name`, one-line `description`, and a single-sentence body ("This subagent reviews all changes since the last commit and write feedback to planning/REVIEW.md"). It has no explicit `tools:` restriction in frontmatter, so it inherits full tool access — which is exactly what the earlier Stop-hook approach was denied and needed. This is a reasonable, working replacement for the abandoned automated-hook design, at the cost of requiring a human (or orchestrating agent) to invoke it explicitly rather than firing automatically on every Stop. Minor: the body has a grammar slip ("write feedback" should be "writes feedback" for subject-verb agreement, or reword as an imperative) — cosmetic only.

### A2. Two independent "review a doc" entry points with overlapping purpose
There are now two separate mechanisms that both produce doc/code review output into `planning/`:
- `.claude/commands/doc-review.md` — a slash command (`/doc-review $ARGUMENTS`) that reviews a named planning doc and appends questions/clarifications/simplification opportunities to a new section at its end.
- `.claude/agents/change-reviewer.md` — a subagent that reviews git changes since last commit and writes to `planning/REVIEW.md` specifically.

These don't conflict, but they're easy to confuse (both "review and append a section"), and only one of them (`change-reviewer`) is pinned to a specific output file. Worth a one-line note somewhere (README or a CLAUDE.md aside) clarifying that `/doc-review` targets arbitrary planning docs in-place while `change-reviewer` always targets `REVIEW.md`, so a future contributor doesn't run the wrong one expecting the other's behavior.

### A3. `enabledPlugins` set is sensible for current stage, `playwright` MCP currently failing to connect
The three enabled plugins (`frontend-design`, `context7`, `playwright`) map cleanly to the project's known needs: frontend visual design guidance, up-to-date library docs, and browser automation for the E2E tests described in PLAN.md §12. Not a repo defect, but worth noting operationally: in this session the `playwright` MCP server failed to connect ("Skipping connection (recent failure cached retries automatically in 15 min...)"). This doesn't affect anything committed, but whoever picks up the E2E test work (§12, `test/`) should confirm the Playwright plugin actually connects before relying on it, since it's currently unusable as configured/cached.

### A4. No `tools:` scoping on `change-reviewer`, no explicit output-permission grant
Given Review 2's entire saga was about a hook agent being denied write access, it's slightly notable that `change-reviewer.md` doesn't declare any `tools` frontmatter at all — it relies entirely on inheriting the invoking session's permissions rather than declaring its own need for `Write`/`Edit`. That's fine for a manually-invoked subagent (this review is proof it works), but if this agent is ever wired back into an automated trigger (a hook, a scheduled task), the same permission problem from Review 2 could resurface. Worth remembering if automation is revisited.

---

## B. Plan vs. reality: consistency check

### B1. Directory structure matches PLAN.md §4 only partially — most of the tree doesn't exist yet
Comparing the actual filesystem to PLAN.md §4's specified layout:

| Path | Specified in §4 | Present on disk | Notes |
|---|---|---|---|
| `frontend/` | Yes | **No** | Directory does not exist at all |
| `backend/` | Yes | Partial | Only `backend/schema/` exists, and it's empty |
| `backend/schema/` | Yes | Yes (empty) | No schema SQL, no seed logic yet |
| `planning/` | Yes | Yes | `PLAN.md` + `REVIEW.md` present |
| `scripts/` | Yes | **No** | No start/stop scripts for mac or Windows |
| `test/` | Yes | **No** | No Playwright config, no `docker-compose.test.yml` |
| `db/` | Yes | Yes | Correctly gitignored except `.gitkeep`, exactly as §4 specifies |
| `Dockerfile` | Yes | **No** | |
| `docker-compose.yml` | Yes (optional) | **No** | |
| `.env` | Yes (gitignored) | N/A | Correctly absent (gitignored) |
| `.env.example` | Implied ("committed") | **No** | See B2 — this is the one gap worth flagging explicitly |

This is expected for a scaffolding-stage repo and matches the README's own "Status" section ("Scaffolding and planning stage — `frontend/` and `backend/` are not yet implemented"), so it is not a discrepancy between plan and reality so much as reality simply not having caught up yet. Flagging it here mainly as a manifest for whoever starts implementation, so nothing is assumed to exist that doesn't.

### B2. `.env.example` is missing — the one concrete gap worth calling out
§4's directory tree lists `.env` as "(gitignored, .env.example committed)," and the README's "Running" section instructs `cp .env.example .env`. No `.env.example` exists anywhere in the repo (`find . -iname "*.env*"` returns nothing). This is a small, cheap fix but a real one: it's the only piece of onboarding scaffolding referenced by two separate documents (PLAN.md §4 and README.md) that has zero corresponding file, and a new contributor following the README literally today would hit a "file not found" on step one. Recommend adding it now, even ahead of backend implementation, with the three variables from PLAN.md §5 (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`) as commented placeholders.

### B3. `backend/schema/` exists on disk but is untracked by git — will not survive a fresh clone
`git ls-files backend` returns nothing: the `backend/schema/` directory has no `.gitkeep` or any other tracked file inside it, unlike `db/` which correctly has one. Since Git does not track empty directories, a fresh `git clone` of this repository right now would not even produce a `backend/` folder — someone starting from a clean checkout gets a smaller skeleton than someone who inherited this working copy. This is a minor but real inconsistency worth fixing alongside B2: either add a `.gitkeep` to `backend/schema/` (matching the `db/` convention) or leave it for the first backend commit to create naturally — but if it's meant to signal "this is the intended location," it should be tracked the same way `db/` is.

### B4. CLAUDE.md / PLAN.md inclusion mechanism is a single point of truth — confirmed working, no drift
`CLAUDE.md` pulls in `planning/PLAN.md` via an `@`-include, and the copy of `PLAN.md` shown in this session's context matches the file on disk read directly. No drift between the "instructions" view and the actual file — good, this is the intended single-source-of-truth setup and it's functioning correctly.

### B5. Unresolved PLAN.md ambiguities from Review 1 are all still open
None of the eleven items from Review 1 (§A1–A6, §B1–B11) have been addressed in `PLAN.md` — the document is byte-for-byte the same specification. This is fine at this stage (no implementation exists yet to have collided with the ambiguities), but it means the two highest-leverage items — the ticker-universe contradiction (A1/A2, where the only tickers with defined seed/sector are exactly the default watchlist, so no watchlist addition could ever succeed, yet §9's LLM example adds `PYPL`) and the Docker persistence mechanism (A3, named volume vs. bind mount) — will hit the very first backend and Docker implementation work respectively. Recommend resolving at least those two before backend/Docker work starts, since Review 1 already identified them as the findings most likely to produce incompatible implementations or a broken demo.

---

## C. Risks and rough edges

### C1. Low risk — line-ending churn on `.claude/settings.json` and `planning/REVIEW.md`
Git warns on every touch of these two files ("LF will be replaced by CRLF"), indicating no `.gitattributes` normalizes line endings and the repo currently has a mix (likely LF as committed, CRLF as edited on this Windows machine). Not urgent, but worth a `.gitattributes` entry (`* text=auto` or explicit LF pinning for JSON/MD) before multiple contributors on different OSes start touching the same files — otherwise diffs will periodically show whole-file rewrites that are pure line-ending noise.

### C2. Low risk — `.claude/settings.json` has no trailing newline
Cosmetic (`git diff` shows `\ No newline at end of file`), consistent with most JSON tooling, not worth fixing proactively but flagging since it's an easy accidental diff-widener if someone's editor auto-adds one later.

### C3. No risk currently, but worth a forward note — `backend/pyproject.toml` doesn't exist yet
PLAN.md §4 describes `backend/` as "a self-contained uv project with its own `pyproject.toml`," and the `litellm-stream` skill assumes `uv add litellm pydantic` will be run inside it. Since no `pyproject.toml` exists yet, this is purely a "not started" observation, not a defect — but it's the natural first step for whoever picks up backend work, before schema/seed logic (which needs the `backend/schema/` directory populated per PLAN.md §7) or LLM integration.

### C4. No risk — LICENSE, README, .gitignore are all in good shape
`LICENSE` (MIT) is present and referenced correctly from the README. `README.md` accurately reflects current project status ("Scaffolding and planning stage") rather than overclaiming functionality, which is good practice — it won't mislead a new contributor about what's actually runnable today. `.gitignore` is a comprehensive Python-project template (with `.env` correctly ignored) and needs no changes now; it will need a Node/Next.js section added once `frontend/` exists (e.g. `node_modules/`, `.next/`, `out/`), but that's future work, not a current gap.

---

## Summary

The project is exactly where its own README says it is: planning and Claude Code tooling scaffolding are in reasonably good shape, and almost no application code exists yet (`backend/schema/` is an empty directory; `frontend/`, `scripts/`, and `test/` don't exist on disk at all). The prior session's hook-based automation experiment (Review 2) has been cleanly abandoned and fully reverted rather than left half-broken — `.claude/settings.json` is back to its original three-plugin baseline, and a manually-invoked `change-reviewer` subagent now serves the same "review changes, write to REVIEW.md" purpose without the permission problems that sank the hook approach.

Two concrete, cheap actions would meaningfully de-risk the next phase of work:
1. **Add `.env.example`** (B2) — the README already instructs contributors to copy it, and it doesn't exist.
2. **Resolve the ticker-universe and Docker-volume ambiguities in PLAN.md** (B5, carried over from Review 1's A1/A2/A3) before backend and Docker implementation begin, since those are the two findings most likely to produce a broken demo or incompatible agent-built components if left for implementers to guess independently.

Everything else found here (B3's untracked empty directory, C1's line-ending warnings, A2's overlapping review entry points) is minor housekeeping rather than a blocker. There is no evidence of scope creep, no orphaned or contradictory configuration left over from the hook experiment, and the one piece of implementation code that does exist (the `litellm-stream` skill's example snippets) is internally consistent with PLAN.md §9's non-streaming-to-client requirement — the skill's `stream=True` is an internal detail of accumulating the LLM's structured-output JSON before it is parsed and returned as one complete response, not a contradiction of the "single complete response" contract.
