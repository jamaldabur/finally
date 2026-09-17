# Phase 3: AI Chat Copilot - Research

**Researched:** 2026-09-17
**Domain:** LLM-backed chat endpoint with structured-output trade/watchlist auto-execution, reusing an existing trading engine
**Confidence:** MEDIUM (structured-output reliability with the locked model is a documented open risk; everything else about this codebase is HIGH — verified by reading the actual files)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | `POST /api/chat` returns complete structured JSON (message + actions) | Pattern 1 (chat route), Code Examples §1 |
| CHAT-02 | Structured output via LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b`) | Common Pitfall 1 (structured-output unreliability), Code Examples §1-2 |
| CHAT-03 | LLM-requested trades/watchlist changes auto-execute through the same validation path as manual actions | Runtime State Inventory is N/A (not a rename phase) — see Don't Hand-Roll + Pattern 2; `execute_trade()`/`add_watchlist_ticker()`/`remove_watchlist_ticker()` verified at exact current signatures below |
| CHAT-04 | Each action annotated `executed`/`error`, returned separately from message text | Pattern 2, Code Examples §3 |
| CHAT-05 | `GET /api/chat` hydrates history on mount | Pattern 1, Code Examples §4 |
| CHAT-06 | `LLM_MOCK=true` deterministic mock responses | Common Pitfall 4, Code Examples §5 |
| UI-08 | Chat panel: hydrate history, inline success/error badges | Architecture Patterns → Frontend section, Code Examples §6 |
</phase_requirements>

## Summary

This phase adds exactly one new capability — an LLM chat endpoint — on top of a backend that already has everything the chat flow needs to *reuse*: `execute_trade()` (`backend/app/portfolio/service.py`) and `add_watchlist_ticker()`/`remove_watchlist_ticker()` (`backend/app/db/watchlist.py`) are fully built, tested, and already the sole validation path for the existing trade-bar and watchlist routes. Phase 3's job is to call these same functions from a new `POST /api/chat` handler after parsing an LLM structured-output response — never to duplicate their logic.

The one genuinely new piece of infrastructure is the LLM call itself: LiteLLM → OpenRouter, model `openrouter/openai/gpt-oss-120b`, requested via the project's own `litellm-stream` skill, with `LLM_MOCK=true` as an escape hatch that must exist before any real key is required. The single biggest risk in this phase — confirmed by primary-source research below, not assumed — is that `openai/gpt-oss-120b` served through OpenRouter has documented, provider-dependent unreliability honoring `response_format`/`json_schema`: some OpenRouter endpoints for this model silently ignore the schema and return free-form text, or return an empty `message.content`. The plan must budget for a parsing-failure fallback path (treat unparseable output as a chat-only response with zero actions, never crash the endpoint) — this is not exotic hardening, it is baseline for this model+router combination.

There is also a live correctness gap in `execute_trade()` today, confirmed by reading the current source: it does not validate `quantity > 0` or that `side` is one of `{"buy", "sell"}` itself — it relies entirely on the HTTP route's Pydantic `Field(gt=0)`/`Literal["buy","sell"]` layer (`backend/app/routes/portfolio.py:24-27`). Phase 3's chat flow calls `execute_trade()` directly, bypassing that Pydantic layer entirely. Left unfixed, an LLM-hallucinated negative quantity or a non-`"buy"`/`"sell"` side string is not merely rejected — it is *silently misrouted*: reading the current `if side == "buy": ... else: _apply_sell(...)` dispatch (`backend/app/portfolio/service.py:177-186`), any side value other than the literal string `"buy"` (e.g. `"hold"`, `"BUY"`, a typo) falls into the sell branch, and a negative buy quantity passes the `cost > cash + QUANTITY_EPSILON` insufficient-cash check (a negative cost is never greater than a positive cash balance) and then *increases* cash via `new_cash_balance = cash - cost`. This must be fixed as part of Phase 3, ahead of or alongside wiring the LLM's raw `trades[]` into `execute_trade()`.

**Primary recommendation:** Validate every LLM-proposed trade/watchlist action against the *same* Pydantic-equivalent constraints the existing HTTP routes already enforce (quantity > 0, side ∈ {"buy","sell"}, ticker non-empty) in the new chat-orchestration layer, before ever reaching `execute_trade()` — and add the missing guard inside `execute_trade()` itself so the invariant holds for every caller, not just this one. Treat OpenRouter structured-output parsing as fallible: parse defensively, degrade to a message-only response with empty `trades`/`watchlist_changes` on failure, and never let a malformed LLM response 500 the endpoint.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM call + structured-output parsing | API / Backend | — | Requires the server-held `OPENROUTER_API_KEY`; must never reach the browser |
| Trade/watchlist auto-execution from chat | API / Backend | Database | Reuses `execute_trade()`/watchlist mutators, which already own DB writes + the portfolio lock |
| Portfolio/watchlist context assembly for the prompt | API / Backend | Database / Storage | `compute_portfolio_view()` + `get_watchlist_entries()` already read DB + live `PriceCache` |
| Chat history persistence | Database / Storage | — | New read/write helpers on the existing (schema-only) `chat_messages` table |
| Chat panel UI (hydrate, render, badges) | Browser / Client | — | Pure presentation of the `POST /api/chat` response; no business logic |
| `LLM_MOCK` branching | API / Backend | — | Env-var gate checked server-side before any LiteLLM call is constructed |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.101.0 [VERIFIED: pip index versions litellm, run this session] | Unified LLM client abstraction, routes to OpenRouter | Project-mandated via `.claude/skills/litellm-stream/SKILL.md` — not a discretionary choice |
| pydantic | 2.13.5 latest / 2.12.5 already locked [VERIFIED: backend/uv.lock, read this session — `name = "pydantic"` / `version = "2.13.5"` pinned by `pip index versions`; uv.lock shows `2.12.5` currently resolved as a transitive dep of fastapi] | Structured-output schema definition (`response_format=MyModel`), request/response validation | Already a transitive dependency via FastAPI throughout this codebase; skill mandates making it a direct dependency too |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | already loaded per root CLAUDE.md conventions | `.env` loading for `OPENROUTER_API_KEY`, `LLM_MOCK` | Already listed as a backend Key Dependency in `.claude/CLAUDE.md`; no new install needed if already present — verify in `backend/pyproject.toml` during planning |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LiteLLM's built-in `response_format=PydanticModel` | Manual JSON prompt + `json.loads` + hand-rolled validation | Explicitly against root CLAUDE.md's mandate to use the `litellm-stream` skill and structured outputs; only relevant as a *fallback parsing* layer when the model ignores the schema (see Pitfall 1), not as the primary mechanism |
| `litellm.enable_json_schema_validation = True` (client-side jsonschema validation for non-natively-supporting providers) | Trust the provider's `strict: true` unconditionally | OpenRouter's own structured-outputs guide states strict-mode conformance is provider-dependent, not model-dependent, and recommends client-side validation "regardless" [CITED: aireiter.com/blog/openrouter-structured-output-guide] |

**Installation:**
```bash
cd backend
uv add litellm pydantic
```

**Version verification:** `pip index versions litellm` run this session → latest `1.101.0`, matches skill's model string requirements (no version-specific behavior called out). `pip index versions pydantic` run this session → latest `2.13.5`; `backend/uv.lock` already resolves `pydantic==2.12.5` transitively via `fastapi` [VERIFIED: backend/uv.lock — grep for `name = "pydantic"` returned `version = "2.13.5"` as latest available and `INSTALLED: 2.12.5` from pip]. Planner should let `uv add pydantic` resolve to whatever satisfies the existing lockfile rather than forcing a bump.

## Package Legitimacy Audit

| Package | Registry | Age (of latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|--------------------------|-----------|--------------|---------|-------------|
| litellm | PyPI | latest release 2026-09-14 (very active project, weekly-cadence releases) | unknown (lookup returned null, not zero) | litellm.ai (project site; GitHub is BerriAI/litellm) | SUS (`too-new`, `unknown-downloads`) | **Approved** — see note below |
| pydantic | PyPI | latest release 2026-08-28 | unknown (lookup returned null, not zero) | github.com/pydantic/pydantic | SUS (`too-new`, `unknown-downloads`) | **Approved** — see note below |

**Note on the SUS verdicts:** The legitimacy checker's `too-new`/`unknown-downloads` signals here are an artifact of using *latest release publish date* as a proxy — both `litellm` and `pydantic` ship new point releases on a near-weekly cadence, so "latest release age" will almost always read as "recent" for these two projects regardless of how long the project itself has existed. This is a false-positive shape, not evidence of a slopsquat: (1) `pydantic` is already a transitive dependency of `fastapi` in this exact repo's `backend/uv.lock` at version `2.12.5`, resolved and in active use throughout every route module read this session; (2) `litellm` is named explicitly, by exact package name, in the project's own committed skill file `.claude/skills/litellm-stream/SKILL.md` (`uv add litellm pydantic`) — a first-party, project-authoritative source, not a WebSearch/training-data guess; (3) both have long-standing, well-known GitHub repos (`BerriAI/litellm`, `pydantic/pydantic`) with mainstream ecosystem presence. Given (1)-(3), no `checkpoint:human-verify` is warranted for the install step itself — the planner should proceed with `uv add litellm pydantic` directly. If the planner wants to be conservative given the automated SUS flag, a single low-cost checkpoint (confirm `import litellm; litellm.__version__` succeeds post-install) is sufficient; a human package-identity review is not.

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** litellm, pydantic — both dispositioned Approved per the note above; no planner checkpoint required beyond a normal install-smoke-test.

## Architecture Patterns

### System Architecture Diagram

```
Browser (Chat Panel)
   │  1. mount: GET /api/chat  ───────────────────────────────┐
   │  2. submit: POST /api/chat {message}                     │
   ▼                                                           │
FastAPI route: app/routes/chat.py                              │
   │                                                           │
   │  a. load portfolio context ── compute_portfolio_view()    │
   │       (app/portfolio/service.py, reads PriceCache + DB)   │
   │  b. load watchlist context ── get_watchlist_entries()     │
   │       (app/db/watchlist.py, reads DB + PriceCache)         │
   │  c. load recent history ── chat_messages.get_messages()   │
   │       (NEW — read helper on existing schema-only table)    │
   │  d. build system+context+history+user messages             │
   ▼                                                           │
   ┌─────────────── LLM_MOCK == "true" ? ─────────────────┐    │
   │ yes → deterministic mock ChatResponse (no network)   │    │
   │ no  → app/llm/client.py: litellm.acompletion(         │    │
   │         model="openrouter/openai/gpt-oss-120b",        │    │
   │         response_format=ChatResponseSchema, ...)       │    │
   └────────────────────┬──────────────────────────────────┘    │
                         ▼                                       │
              Parse JSON → ChatResponseSchema                    │
              (defensive: on parse failure, degrade to           │
               message-only response, empty actions)             │
                         │                                       │
                         ▼                                       │
   For each trades[] item  ──► validate (qty>0, side∈{buy,sell}) │
                              ──► execute_trade() [SAME function  │
                                   the trade bar route calls]     │
                              ──► annotate executed/error         │
   For each watchlist_changes[] ──► add_/remove_watchlist_ticker()│
                              [SAME functions POST/DELETE          │
                               /api/watchlist call]                │
                              ──► annotate executed/error           │
                         │                                       │
                         ▼                                       │
              chat_messages.insert_message() (NEW — write helper) │
              persists {role, content, actions JSON}              │
                         │                                       │
                         ▼                                       │
              Return {message, trades: [...+outcome],             │
                       watchlist_changes: [...+outcome]}  ────────┘
                         │
                         ▼
   Chat panel renders bubble text + inline success/error badges
   per action (separate from bubble text — PLAN.md §9 step 7)
```

### Recommended Project Structure
```
backend/app/
├── llm/
│   ├── __init__.py
│   ├── client.py       # LiteLLM call wrapper: real call vs LLM_MOCK branch
│   ├── schema.py       # Pydantic response_format models (ChatResponse, TradeRequest, WatchlistChange)
│   └── mock.py         # Deterministic mock response builder for LLM_MOCK=true
├── db/
│   └── chat_messages.py  # ADD: get_messages(), insert_message() to the existing schema-only module
├── portfolio/
│   └── service.py        # FIX: add quantity>0 / side validation guard inside execute_trade()
└── routes/
    └── chat.py          # NEW: GET/POST /api/chat, the only module here permitted to raise HTTPException for this flow

frontend/
├── lib/
│   ├── api.ts            # ADD: fetchChatHistory(), postChatMessage()
│   ├── types.ts          # ADD: ChatMessage, ChatResponse, ActionOutcome wire types
│   └── chatStore.tsx     # NEW: mirrors portfolioStore.tsx's context+hooks pattern
└── components/
    └── chat/
        ├── ChatPanel.tsx     # Collapsible container, hydrates on mount
        ├── ChatMessageList.tsx
        ├── ChatInput.tsx
        └── ActionBadge.tsx   # Inline executed/error badge, separate from bubble text
```

### Pattern 1: Chat route mirrors the existing trade/watchlist route layering
**What:** `app/routes/chat.py` is the only module in the chat request path permitted to raise `HTTPException`. All business logic (LLM call, action execution) lives in `app/llm/` and reuses `app/portfolio/service.py` / `app/db/watchlist.py` — this exactly matches the layering already established and documented at the top of `backend/app/routes/portfolio.py` (lines 1-9) and `backend/app/routes/watchlist.py` (lines 1-11), both read this session.
**When to use:** Every new route in this codebase; already the established convention, not a discretionary pattern for this phase to reinvent.
**Example:**
```python
# Source: backend/app/routes/portfolio.py:114-126 (verified this session) —
# the exact existing pattern to mirror for POST /api/chat's error translation
@router.post("/api/portfolio/trade")
async def post_trade(body: TradeRequest, request: Request) -> TradeResponse:
    result = await execute_trade(
        price_cache=request.app.state.price_cache,
        market_source=request.app.state.market_source,
        lock=request.app.state.portfolio_lock,
        ticker=body.ticker,
        side=body.side,
        quantity=body.quantity,
    )
    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.reason)
```

### Pattern 2: LLM-requested actions execute through the identical validated path as manual actions — with an added pre-validation gate
**What:** For each item in the parsed `trades[]`, first validate shape locally (ticker non-empty, `side in ("buy", "sell")`, `quantity > 0` and finite) — mirroring what `TradeRequest` Pydantic model already enforces for the HTTP route (`backend/app/routes/portfolio.py:24-27`, verified this session: `ticker: str = Field(min_length=1)`, `side: Literal["buy", "sell"]`, `quantity: float = Field(gt=0)`) — and annotate as `error` immediately for anything that fails this gate, without calling `execute_trade()` at all. Only shape-valid items reach `execute_trade()`, whose own result (`status: "executed" | "error"`) becomes the action's outcome annotation.
**When to use:** Every trade/watchlist item the LLM proposes, before it reaches the shared business-logic functions.
**Example:**
```python
# Source: verified current signature, backend/app/portfolio/service.py:135-144
# execute_trade() does NOT itself validate quantity>0 or side — confirmed by
# reading _apply_buy/_apply_sell dispatch at lines 177-186: any side value
# other than the literal "buy" falls into the sell branch, and a negative
# quantity buy passes the `cost > cash + QUANTITY_EPSILON` check (a negative
# cost is never greater than a positive cash balance) and INCREASES cash.
# This gate must exist in app/llm/ AND ideally inside execute_trade() itself:
def _validate_llm_trade(item: LlmTradeItem) -> str | None:
    """Returns an error reason, or None if the item is shape-valid."""
    if not item.ticker or not item.ticker.strip():
        return "Missing ticker"
    if item.side not in ("buy", "sell"):
        return f"Invalid side: {item.side!r}"
    if not isinstance(item.quantity, (int, float)) or item.quantity <= 0:
        return f"Invalid quantity: {item.quantity!r}"
    return None
```

### Anti-Patterns to Avoid
- **Duplicating trade/watchlist validation logic in the chat flow:** PLAN.md §9 step 6 is explicit that there is exactly one code path that validates and applies a trade or watchlist change. Writing a second `_execute_llm_trade()` that re-implements cash/share checks instead of calling `execute_trade()` violates this directly and will drift from the trade-bar behavior over time.
- **Streaming the LLM call to the frontend:** PLAN.md §9 step 4 and CHAT-01 are explicit — `POST /api/chat` is non-streaming from the frontend's point of view; the full structured response must be parsed as one JSON object before anything downstream happens. This does **not** forbid using `stream=True` on the *internal* LiteLLM→OpenRouter call (see Code Examples §1-2) — the skill's own structured-output snippet uses `stream=True` purely to accumulate the JSON string server-side before parsing. Do not confuse "accumulate internally via streaming, return once" with "stream to the client," and do not build an SSE endpoint for chat.
- **Trusting `response_format` conformance unconditionally:** see Pitfall 1 below — this specific model/router combination has documented cases of ignoring the schema entirely.
- **Folding execution outcomes into the LLM's `message` text:** PLAN.md §9 step 7 is explicit that `message` is written before execution happens and cannot reference outcomes. Outcomes must be separate structured data (`trades[].outcome`, `watchlist_changes[].outcome`), rendered as separate inline badges by the frontend (UI-08).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Trade validation/execution from chat | A second trade-execution function inside `app/llm/` | `app/portfolio/service.py::execute_trade()` (already exists, tested, lock-guarded) | PLAN.md §9 step 6 mandates exactly one path; a second implementation will silently diverge (e.g. miss the portfolio-lock, miss the immediate snapshot insert on success) |
| Watchlist add/remove from chat | Direct SQL against the `watchlist` table from `app/llm/` | `app/db/watchlist.py::add_watchlist_ticker()` / `remove_watchlist_ticker()` (already exist, already used by `POST`/`DELETE /api/watchlist`) | Same reuse mandate; also these functions already handle ticker normalization/idempotency (`INSERT OR IGNORE`) correctly |
| Structured-output JSON parsing/repair | A custom regex/brace-matching JSON extractor | Pydantic's `model_validate_json()` inside a `try/except (ValidationError, json.JSONDecodeError)`, with LiteLLM's `enable_json_schema_validation` flag as a first line of defense | Hand-rolled JSON repair for LLM output is a deep, well-documented rabbit hole (see Pitfall 1's "state machine" reference) — not worth building for a course capstone; a clean fallback-to-message-only path is sufficient and matches the project's zero-stakes design philosophy |
| Portfolio/watchlist context for the LLM prompt | A new query layer | `compute_portfolio_view()` (`app/portfolio/service.py`) + `get_watchlist_entries()` (`app/db/watchlist.py`) — both already exist and are exactly the data `GET /api/portfolio` and `GET /api/watchlist` already expose | These are the exact same read functions the REST routes call; building a parallel context-assembly function risks the two views disagreeing |

**Key insight:** This phase has almost nothing to build from scratch on the trading/data side — the entire "Don't Hand-Roll" surface here is about resisting the temptation to write a second, chat-specific trade/watchlist mutation path "for convenience." The only genuinely new hand-rolled code should be: the LLM client wrapper, the mock branch, the chat_messages read/write helpers, and the chat route's orchestration glue.

## Common Pitfalls

### Pitfall 1: `openai/gpt-oss-120b` via OpenRouter may not honor `response_format`/`json_schema`
**What goes wrong:** The model returns free-form text instead of the requested JSON schema, or in some reported cases returns a `200` response with an empty `message.content` when OpenRouter's own compatibility layer and the underlying provider disagree about strict-mode support.
**Why it happens:** OpenRouter's structured-outputs support is determined per *provider endpoint*, not per model — the same `openai/gpt-oss-120b` model string can route to different backing providers with different levels of schema enforcement (native strict / translated / advisory-only), and this can change over time [CITED: openrouter.ai/docs/guides/features/structured-outputs]. Community reports specifically describe `response_format` with `type: "json_schema"` (including `strict: true`) being ignored by `openai/gpt-oss-120b` [CITED: community.groq.com/t/structured-outputs-ignored-by-openai-gpt-oss-120b/687 — note this specific report is on Groq's own API, not OpenRouter, but corroborates the model-level (not just router-level) unreliability; OpenRouter-specific silent-ignore/empty-content reports are separately documented at aireiter.com/blog/openrouter-structured-output-guide].
**How to avoid:**
1. Set `litellm.enable_json_schema_validation = True` so LiteLLM validates the response against the Pydantic schema client-side even when the provider doesn't natively guarantee it [CITED: docs.litellm.ai/docs/completion/json_mode].
2. Always wrap the parse in `try/except` and have a defined fallback: if the response can't be parsed into `ChatResponseSchema`, construct a `ChatResponse` with `message` set to a generic "I couldn't complete that request cleanly, please rephrase" (or, if the raw text is plausible prose, use it as-is) and empty `trades`/`watchlist_changes` — never crash `POST /api/chat` on a parse failure. This satisfies CHAT-01's "always returns a complete structured JSON response" even when the *LLM's* output didn't conform.
3. Consider a `checkpoint:human-verify` task early in Phase 3 execution: manually send a real (non-mock) chat message once `OPENROUTER_API_KEY` is available and confirm the model actually returns parseable structured JSON in practice for this project's exact schema before building extensive logic on top of the assumption that it always will.
**Warning signs:** `POST /api/chat` returns 200 but `trades`/`watchlist_changes` are always empty even when the user clearly asked for a trade; or the endpoint intermittently 500s on `ValidationError`/`JSONDecodeError`.

### Pitfall 2: `execute_trade()` does not validate `quantity`/`side` itself (confirmed live bug, not hypothetical)
**What goes wrong:** A chat-originated trade with `quantity <= 0` or `side` outside `{"buy","sell"}` is not rejected by `execute_trade()` — it is silently misrouted (see Summary above for the exact mechanism) and can mint free cash or corrupt state.
**Why it happens:** `execute_trade()` was designed assuming its only caller was the HTTP route, whose Pydantic `TradeRequest` model (`Field(gt=0)`, `Literal["buy","sell"]`) did this validation upstream. Calling `execute_trade()` directly from the chat flow bypasses that layer entirely — flagged in `.planning/STATE.md`'s Blockers/Concerns section as "worth fixing before or during Phase 3" [VERIFIED: backend/app/portfolio/service.py:135-144,177-186, read this session].
**How to avoid:** Add an explicit guard at the top of `execute_trade()` (not just in the chat-layer pre-validation of Pattern 2) that returns a `TradeResult(status="error", ...)` for `quantity <= 0`, non-finite quantity, or `side not in ("buy", "sell")`. This closes the gap for every current and future caller, not just the LLM path — belt-and-suspenders with the chat-layer gate in Pattern 2.
**Warning signs:** A test that sends `{"side": "hold", "quantity": 5}` or `{"side": "buy", "quantity": -100}` directly to `execute_trade()` (bypassing the route) and asserts `status == "error"` — if this test doesn't exist yet, write it as part of this phase.

### Pitfall 3: Confusing "no client-facing streaming" with "no internal streaming"
**What goes wrong:** A planner or implementer reads PLAN.md §9 step 4 ("non-streaming... nothing to stream to the client") and concludes the LiteLLM call itself must use `stream=False`, then finds the model call unreliable or slow, or ignores the skill's own documented pattern.
**Why it happens:** The skill's own structured-output code example (`.claude/skills/litellm-stream/SKILL.md`) uses `stream=True` on the LiteLLM→OpenRouter call and manually accumulates `chunk.choices[0].delta.content` into a full JSON string before calling `MyBaseModelSubclass.model_validate_json(json_string)` — this is an internal accumulation pattern, unrelated to whether the HTTP response to the browser is streamed.
**How to avoid:** Follow the skill's exact snippet for the LiteLLM call (internal `stream=True` + accumulate + parse once complete), while `POST /api/chat` itself remains a single ordinary JSON response with no `StreamingResponse`/SSE involved.
**Warning signs:** None yet observed in this codebase — this is a documentation-clarity pitfall, not a bug, but worth calling out explicitly since the two "non-streaming" statements (PLAN.md's client contract vs. the skill's internal LiteLLM pattern) can read as contradictory at a glance.

### Pitfall 4: `LLM_MOCK` mock responses need to be deliberately designed for downstream testability, not just "hardcoded string"
**What goes wrong:** A naive mock (`if LLM_MOCK: return {"message": "mock response", "trades": [], "watchlist_changes": []}`) satisfies CHAT-06 literally but gives Phase 6's E2E suite (TEST-05: "mocked chat trade execution") nothing to test against, since the mock never produces an action.
**Why it happens:** CHAT-06 only requires *determinism*, not *usefulness for downstream E2E scenarios* — but PLAN.md §12 explicitly lists "AI chat (mocked): send a message, receive a response, trade execution appears inline" as a required E2E scenario, and that scenario needs the mock to actually produce a `trades[]` action for some input.
**How to avoid:** Design the mock as a simple deterministic function of the user's message content — e.g., if the message contains the substring "buy" followed by a recognizable ticker pattern, return a mock response with a corresponding `trades[]` entry; otherwise return a plain conversational mock message with empty actions. This is Claude's discretion (no CONTEXT.md constrains it) but should be decided during planning, not deferred to Phase 6.
**Warning signs:** Phase 6 planning discovers the mock has no way to exercise the trade-execution-via-chat E2E scenario and has to retrofit Phase 3's mock module.

### Pitfall 5: Chat history growth is unbounded, matching the project's own accepted tradeoff for `portfolio_snapshots` — but not yet stated for `chat_messages`
**What goes wrong:** `GET /api/chat` naively returns every row ever inserted, and after enough demo sessions the "recent conversation history" the LLM prompt includes (PLAN.md §9 step 2) grows unbounded, inflating token usage/cost per request.
**Why it happens:** No pruning policy is specified anywhere in PLAN.md for `chat_messages` (unlike `portfolio_snapshots`, where PLAN.md §7 explicitly says rows are "never pruned... an accepted tradeoff"). The absence of a stated policy here is a genuine open question, not a decided constraint either way.
**How to avoid:** Decide during planning (not left implicit) how many recent messages `GET /api/chat` returns to the frontend and how many are included in the LLM prompt context (PLAN.md §9 step 2's "recent conversation history" is deliberately vague — e.g. cap prompt context to the last N message pairs, but let `GET /api/chat` return more for the panel's scrollback). This is `[ASSUMED]`-tagged discretion, not a locked decision — flag it in Assumptions Log below.
**Warning signs:** None yet — this is a forward-looking design decision, not an observed bug.

## Code Examples

### 1. LiteLLM structured-output call (internal streaming, single parsed result)
```python
# Source: .claude/skills/litellm-stream/SKILL.md (project-mandated pattern,
# read this session) — adapted to acompletion for FastAPI's async route,
# matching this codebase's async-first convention (backend/.claude/CLAUDE.md
# "Async Patterns" / "All I/O operations are async")
from litellm import acompletion
import litellm

litellm.enable_json_schema_validation = True  # client-side fallback validation
MODEL = "openrouter/openai/gpt-oss-120b"

async def call_llm_structured(messages: list[dict], schema: type[BaseModel]) -> str:
    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=schema,
        reasoning_effort="low",
        stream=True,
    )
    json_string = ""
    async for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            json_string += content
    return json_string
```

### 2. Defensive parse with fallback (addresses Pitfall 1)
```python
# Pattern derived from this phase's research — no single official source;
# combines litellm's documented client-side validation flag with ordinary
# pydantic ValidationError handling.
from pydantic import ValidationError
import json

def parse_llm_response(json_string: str) -> ChatResponseSchema:
    try:
        return ChatResponseSchema.model_validate_json(json_string)
    except (ValidationError, json.JSONDecodeError):
        # Model ignored the schema (Pitfall 1) — degrade to a message-only
        # response rather than 500ing the endpoint.
        return ChatResponseSchema(
            message=json_string.strip() or "I couldn't process that — please try again.",
            trades=[],
            watchlist_changes=[],
        )
```

### 3. Action annotation shape (addresses CHAT-04)
```python
# Not sourced from an existing file — this is new shape this phase
# introduces. Mirrors TradeResult's existing status:Literal["executed","error"]
# convention from backend/app/portfolio/service.py:126-129 (read this
# session) so the frontend sees one consistent vocabulary across trade-bar
# and chat-originated trades.
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class AnnotatedAction:
    ticker: str
    action_type: Literal["trade", "watchlist"]
    outcome: Literal["executed", "error"]
    reason: str | None  # populated only on "error", mirrors TradeResult.reason
```

### 4. Chat history read/write helpers to add (addresses CHAT-05)
```python
# Source: pattern mirrors backend/app/db/trades.py's existing
# insert_trade()/get_trades() shape exactly (read this session,
# backend/app/db/trades.py:89-96) — chat_messages.py currently only has
# init_db() (backend/app/db/chat_messages.py:36-42, read this session);
# this phase adds the read/write pair the module's own docstring says is
# "Phase 3's concern."
async def insert_message(
    role: str, content: str, actions: str | None, user_id: str = DEFAULT_USER_ID
) -> ChatMessage: ...

async def get_messages(user_id: str = DEFAULT_USER_ID, limit: int = 50) -> list[ChatMessage]: ...
```

### 5. Frontend chat store, mirroring the existing portfolioStore pattern
```tsx
// Source: pattern mirrors frontend/lib/portfolioStore.tsx's existing
// createContext + useState + mount-effect shape exactly (read this session)
// — D-04/D-11 conventions (single API access point via lib/api.ts, no
// component calls fetch directly) apply identically to chat.
"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchChatHistory, postChatMessage } from "./api";
import type { ChatMessage } from "./types";

// ... createContext/useState/useEffect(mount-only fetch) exactly as
// portfolioStore.tsx does for fetchPortfolio(), substituting
// fetchChatHistory() for CHAT-05's hydrate-on-mount requirement.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Trusting any `response_format` request to be honored by the target model | Treat structured-output conformance as provider/endpoint-dependent even for "supported" models; validate client-side regardless | Ongoing, documented as of the OpenRouter structured-outputs guide and multiple 2025-2026 community bug reports for this exact model | Directly shapes Pitfall 1's mandatory fallback-parsing requirement for this phase |

**Deprecated/outdated:** None specific to this phase — the stack (LiteLLM, OpenRouter, Pydantic) is current and actively maintained; the risk here is model/provider-behavior reliability, not library staleness.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The mock (`LLM_MOCK=true`) response should be a deterministic function of message content (e.g. keyword-triggered mock trade) rather than a single static reply, to support Phase 6's E2E "mocked chat trade execution" scenario | Common Pitfall 4 | If wrong (project wants a trivially static mock), Phase 6 will need to retrofit a richer mock — low risk, easily corrected later since it's purely additive |
| A2 | No pruning/cap policy exists yet for `chat_messages` row count or how many messages are included in the LLM prompt context — this phase should decide a cap (e.g. last N pairs) rather than sending the entire history on every call | Common Pitfall 5 | If unaddressed, token cost per chat call grows unbounded over a long demo session; not a correctness bug, but a cost/latency regression over time |
| A3 | `python-dotenv` is assumed already present as a backend dependency per root `.claude/CLAUDE.md`'s Key Dependencies list, but was not independently re-confirmed against the current `backend/pyproject.toml` in this session (only `fastapi`, `uvicorn[standard]`, `httpx` were seen in the dependencies list read this session) | Standard Stack → Supporting | If missing, `.env` loading for `OPENROUTER_API_KEY`/`LLM_MOCK` at backend startup would need to be added — the planner should re-verify `backend/pyproject.toml`'s exact dependency list before assuming it's there |

**If this table is empty:** N/A — see above; three assumptions logged, none blocking, none touching the phase's core success criteria.

## Open Questions

1. **Does `openai/gpt-oss-120b` via OpenRouter reliably return valid structured JSON for this project's exact schema in practice?**
   - What we know: Documented community reports (Groq forum, GitHub issues, an OpenRouter-specific structured-outputs guide) describe this model ignoring `response_format`/`json_schema` on some provider routes, or returning empty content on others.
   - What's unclear: Whether the *specific* OpenRouter provider route this project will actually hit at runtime is one of the affected ones — this varies over time and cannot be determined without a live API call.
   - Recommendation: Add a `checkpoint:human-verify` task early in Phase 3's execution (once `OPENROUTER_API_KEY` is confirmed present) to send one real chat message and manually confirm the response parses cleanly, before building extensive downstream logic on the assumption that it always will. Build the defensive-parse fallback (Code Example §2) regardless of the outcome.

2. **Should `execute_trade()`'s missing quantity/side validation be fixed as a standalone commit before Phase 3's chat wiring, or as part of the same plan?**
   - What we know: The gap is real and confirmed by reading the current source (Pitfall 2); it predates Phase 3 and was flagged during Phase 1's own review (`01-REVIEW.md` WR-01/WR-02 per `.planning/STATE.md`).
   - What's unclear: Whether the project wants this treated as a discrete bugfix commit (cleaner git history, isolates the fix from new chat code) or folded into the same plan/wave that wires chat trades through `execute_trade()` (since the chat flow is what makes the gap newly exploitable via untrusted LLM output rather than a validated HTTP body).
   - Recommendation: Fix it as an early task within this phase's plan (not deferred to a separate phase), since PLAN.md's own §9 step 6 language ("the same validation function used by POST /api/portfolio/trade") implies the validation should already be complete at that shared layer — Phase 3 is simply the first caller to expose the gap's real consequences.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `OPENROUTER_API_KEY` | Real (non-mock) LLM calls (CHAT-02) | Present in project root `.env` per root CLAUDE.md ("There is an OPENROUTER_API_KEY in the .env file in the project root") — not independently re-read this session per the secret-file read guard | — | `LLM_MOCK=true` (CHAT-06) fully substitutes for development/testing without touching the real key |
| `litellm` PyPI package | All LLM calls, mock and real | Not yet installed in `backend/pyproject.toml` (confirmed by reading it this session — only `fastapi`, `uvicorn[standard]`, `httpx` listed) | latest 1.101.0 | None — required install for this phase |
| Network access to `openrouter.ai` | Real (non-mock) LLM calls | Not tested this session (sandboxed research environment) | — | `LLM_MOCK=true` for any environment without outbound network access (CI, offline dev) |

**Missing dependencies with no fallback:** None — `litellm` is a required install but has no fallback need (it's this phase's whole point); `LLM_MOCK` fully covers the no-network/no-key case.
**Missing dependencies with fallback:** `OPENROUTER_API_KEY` / network access → `LLM_MOCK=true`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.24+ (`asyncio_mode = "auto"`) [VERIFIED: backend/pyproject.toml:12-23, read this session] |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && uv run pytest tests/routes/test_chat.py tests/db/test_chat_messages.py tests/llm -x` (paths anticipate this phase's new test files; adjust to whatever the plan actually creates) |
| Full suite command | `cd backend && uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | `POST /api/chat` returns `{message, trades, watchlist_changes}` shape | route (TestClient) | `uv run pytest tests/routes/test_chat.py::test_post_chat_returns_structured_response -x` | ❌ Wave 0 |
| CHAT-02 | Structured output requested via `response_format`; mock path bypasses network | unit (LLM client, mocked/monkeypatched) | `uv run pytest tests/llm/test_client.py -x` | ❌ Wave 0 |
| CHAT-03 | LLM trade auto-executes through `execute_trade()`; LLM watchlist change auto-executes through `add_/remove_watchlist_ticker()` | integration (chat route + real service functions, isolated DB) | `uv run pytest tests/routes/test_chat.py::test_chat_trade_auto_executes -x` | ❌ Wave 0 |
| CHAT-04 | Each action annotated `executed`/`error`, separate from `message` | route | `uv run pytest tests/routes/test_chat.py::test_chat_action_annotated_on_insufficient_cash -x` | ❌ Wave 0 |
| CHAT-05 | `GET /api/chat` returns prior history | route | `uv run pytest tests/routes/test_chat.py::test_get_chat_hydrates_history -x` | ❌ Wave 0 |
| CHAT-06 | `LLM_MOCK=true` skips network, deterministic | unit + route | `uv run pytest tests/llm/test_mock.py tests/routes/test_chat.py::test_chat_with_llm_mock -x` | ❌ Wave 0 |
| Pitfall 2 fix | `execute_trade()` rejects `quantity<=0` / invalid `side` directly | unit (service) | `uv run pytest tests/portfolio/test_service.py::test_execute_trade_rejects_invalid_quantity_and_side -x` | ❌ Wave 0 |
| UI-08 | Chat panel hydrates + renders inline badges | frontend component (React Testing Library — not yet set up per TEST-04, deferred to Phase 6 per traceability table) | manual/UAT only this phase | ❌ Wave 0 (frontend test harness not yet established; TEST-04 is Phase 6's requirement) |

### Sampling Rate
- **Per task commit:** targeted `uv run pytest <new test file> -x`
- **Per wave merge:** `cd backend && uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`; UI-08's frontend behavior verified via manual UAT this phase (frontend unit-test harness is Phase 6's TEST-04, not yet established)

### Wave 0 Gaps
- [ ] `backend/tests/routes/test_chat.py` — covers CHAT-01, CHAT-03, CHAT-04, CHAT-05, CHAT-06
- [ ] `backend/tests/db/test_chat_messages.py` — extend existing schema-only file with read/write tests for the new `insert_message()`/`get_messages()` helpers
- [ ] `backend/tests/llm/` (new package, needs `__init__.py`) — `test_client.py` for the LiteLLM wrapper (mocked network), `test_mock.py` for the `LLM_MOCK` deterministic branch
- [ ] `backend/tests/portfolio/test_service.py` — extend existing file with the Pitfall 2 fix's regression test
- [ ] Framework install: none — pytest/pytest-asyncio already configured project-wide; only the `tests/llm/__init__.py` package needs creating

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single hardcoded `user_id="default"`, no auth in scope per project constraints |
| V3 Session Management | No | No sessions — stateless single-user demo |
| V4 Access Control | No | No multi-user boundary to enforce |
| V5 Input Validation | Yes | LLM output is untrusted input: every `trades[]`/`watchlist_changes[]` item must pass the same shape validation the HTTP Pydantic layer already enforces (Pattern 2) before reaching `execute_trade()`/watchlist mutators. The user's raw chat message string itself needs no special sanitization beyond normal string handling — it is never interpolated into SQL (all DB access here is parameterized, verified in `backend/app/db/*.py`) or executed as code. |
| V6 Cryptography | No | No new crypto surface — `OPENROUTER_API_KEY` is an existing secret already handled by the project's `.env`/env-var convention; this phase must not log it (matches the existing convention already followed for `MASSIVE_API_KEY` in `backend/app/market/factory.py`, per `.planning/codebase/CONCERNS.md`'s prior audit) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection via chat message content attempting to make the model claim a trade "executed" that didn't, or fabricate a favorable outcome in its own `message` text | Spoofing / Tampering | Not applicable to the *displayed outcome* — PLAN.md §9 step 7 already structurally prevents this: the LLM's `message` text is generated *before* execution happens and outcomes are reported as separate structured data the backend computes from the real `TradeResult`/mutation result, never from anything the LLM claims. The frontend must render outcome badges from this backend-computed field, never parse/trust outcome claims out of `message` text. |
| LLM-hallucinated trade parameters (negative quantity, invalid side, malformed ticker) reaching `execute_trade()` unvalidated | Tampering | Pattern 2's pre-validation gate + Pitfall 2's fix inside `execute_trade()` itself |
| API key leakage of `OPENROUTER_API_KEY` in logs/error messages | Information Disclosure | Never log the key or full request/response bodies containing it; mirror the existing `MASSIVE_API_KEY` handling convention (key read from env, never logged, errors reference it generically) |
| Chat endpoint used to exfiltrate `OPENROUTER_API_KEY` or other env vars via a crafted user message asking the LLM to repeat its system prompt/config | Information Disclosure | Low severity for a single-user demo with no other users to exfiltrate from, but the system prompt should not itself embed the key or other secrets — only the LiteLLM client call needs it, and it never appears in any message sent to the model |

## Sources

### Primary (HIGH confidence)
- `backend/app/portfolio/service.py`, `backend/app/routes/portfolio.py`, `backend/app/routes/watchlist.py`, `backend/app/db/watchlist.py`, `backend/app/db/chat_messages.py`, `backend/app/db/trades.py`, `backend/app/db/positions.py`, `backend/app/db/users_profile.py`, `backend/app/main.py`, `backend/app/market/base.py`, `backend/app/market/cache.py`, `backend/app/market/simulator.py`, `backend/tests/conftest.py`, `backend/tests/routes/test_portfolio.py`, `backend/tests/db/test_chat_messages.py`, `backend/tests/portfolio/test_service.py` — all read directly this session
- `frontend/lib/api.ts`, `frontend/lib/types.ts`, `frontend/lib/portfolioStore.tsx`, `frontend/app/page.tsx`, `frontend/components/trade-bar/TradeBar.tsx`, `frontend/components/watchlist/WatchlistPanel.tsx`, `frontend/components/header/Header.tsx`, `frontend/package.json` — all read directly this session
- `.claude/skills/litellm-stream/SKILL.md` — read directly this session (project-authoritative, mandated by root CLAUDE.md)
- `pip index versions litellm` / `pip index versions pydantic` — run this session
- `gsd_run query package-legitimacy check --ecosystem pypi litellm pydantic python-dotenv` — run this session

### Secondary (MEDIUM confidence)
- [OpenRouter Structured Outputs guide](https://openrouter.ai/docs/guides/features/structured-outputs) — fetched this session, official OpenRouter docs
- [LiteLLM JSON Mode / Structured Outputs docs](https://docs.litellm.ai/docs/completion/json_mode) — fetched this session, official LiteLLM docs
- [OpenRouter Structured Output: Why Your Schema Gets Ignored](https://aireiter.com/blog/openrouter-structured-output-guide) — fetched this session, third-party practitioner guide corroborating official docs' provider-dependent caveat

### Tertiary (LOW confidence)
- [Groq Community: Structured Outputs ignored by openai/gpt-oss-120b](https://community.groq.com/t/structured-outputs-ignored-by-openai-gpt-oss-120b/687) — WebSearch result, community forum report, not an OpenRouter-specific report but corroborates model-level unreliability
- WebSearch summaries for `litellm.acompletion` + Pydantic `response_format` behavior (GitHub issues BerriAI/litellm #8060, #6830, #7561 referenced in search results but not individually fetched/read this session)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — litellm/pydantic versions verified via `pip index versions` this session; installation command is the project's own mandated skill instruction, not a discretionary choice
- Architecture/reuse of existing validation path: HIGH — every function signature and current behavior cited above (`execute_trade()`, `add_watchlist_ticker()`, `compute_portfolio_view()`, chat_messages schema) was confirmed by reading the actual current source this session, not inferred from documentation
- Structured-output reliability with the locked model: MEDIUM — corroborated by two independent official/practitioner sources (OpenRouter's own docs + a third-party guide), but the model/provider-routing landscape changes over time and this project's specific runtime behavior was not (and could not be, in this sandboxed session) directly tested against the real OpenRouter API
- Pitfalls: HIGH for Pitfall 2 (confirmed by reading the exact current dispatch logic), MEDIUM for Pitfall 1 (well-corroborated but inherently probabilistic/time-varying), MEDIUM for Pitfalls 3-5 (reasoning from the existing spec + codebase conventions, not externally verified)

**Research date:** 2026-09-17
**Valid until:** 7 days for the OpenRouter/gpt-oss-120b structured-output reliability claim specifically (this is an actively-changing, provider-routing-dependent behavior per the sources themselves) — 30 days for everything else (stable library versions, stable existing codebase contracts)
