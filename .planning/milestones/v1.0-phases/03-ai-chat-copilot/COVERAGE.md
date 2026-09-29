# Phase 3 — API Coverage Matrix

**External API:** OpenRouter Chat Completions API, reached through LiteLLM (`litellm.acompletion`), model `openrouter/openai/gpt-oss-120b`.
**Detector:** `api-coverage.cjs --json` → `detected: true` (signal: `(surface) api`).
**Baseline:** full coverage. Every capability below starts as `INTEGRATE`; this table is the subtraction record.

| capability | decision | reason |
|---|---|---|
| `chat/completions` — text response | INTEGRATE | |
| `response_format` structured outputs (`json_schema` from a Pydantic model) | INTEGRATE | |
| `stream=true` chunk accumulation (server-internal only) | INTEGRATE | |
| `reasoning_effort` request parameter | INTEGRATE | |
| `litellm.enable_json_schema_validation` client-side schema validation | INTEGRATE | |
| Error/exception surface (rate limit, auth failure, timeout, malformed body) | INTEGRATE | |
| Tool / function calling | OPT-OUT | not needed — PLAN.md §9 carries actions inside the structured-output payload, not through a tool-call loop |
| Streaming the LLM response through to the browser | OPT-OUT | explicitly out of scope — PLAN.md §9 step 4 requires one complete parsed JSON response before anything downstream happens |
| `GET /models` model listing | OPT-OUT | not needed — the model string is fixed by root CLAUDE.md; there is no runtime model picker |
| `GET /generation` cost and usage metadata | OPT-OUT | not needed — no cost or token surface exists in the UI this milestone |
| `GET /key`, `GET /credits` (rate limits, balance) | OPT-OUT | not needed — no quota display and no budget enforcement in scope |
| Provider routing preferences (`provider.order`, `allow_fallbacks`) | OPT-OUT | not needed yet — one fixed model string; revisit only if 03-RESEARCH.md Pitfall 1's provider-dependent schema support forces an explicit provider pin |
| Prompt caching | OPT-OUT | not needed — single-user demo; prompt cost is not a constraint at this scale |
| `transforms` (middle-out prompt compression) | OPT-OUT | not needed — prompt context is explicitly capped at the last 20 stored messages instead |
| Web-search plugin | OPT-OUT | explicitly out of scope — PLAN.md §9 restricts the assistant to the portfolio and watchlist context the backend assembles |
| Embeddings | OPT-OUT | not needed — no retrieval or semantic-search feature exists in this project |
| Multimodal image input | OPT-OUT | not needed — the chat panel is text-only per PLAN.md §10 |
| Audio input / output | OPT-OUT | not needed — no voice surface |
| PDF / file inputs | OPT-OUT | not needed — no document upload surface |
| `user` / request attribution metadata | OPT-OUT | not needed — single hardcoded `user_id="default"`, no multi-tenant attribution (PLAT2-01 is v2) |
| BYOK / per-request provider keys | OPT-OUT | not needed — one `OPENROUTER_API_KEY` per PLAN.md §5 |

**Second integration against the same need:** none. If a later phase adds a second LLM integration, it re-decides this full baseline rather than inheriting these opt-outs.
