---
phase: "03"
slug: "ai-chat-copilot"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-21"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|----------------|
| Browser → `POST /api/chat` | Untrusted free-text user input enters the server and reaches an LLM that can trigger state changes | User message text |
| Server → OpenRouter (`openrouter.ai`) | Outbound call carrying the user's portfolio context, authenticated by `OPENROUTER_API_KEY` | Portfolio/watchlist context, conversation history, API key (transport auth only, never logged) |
| LLM response → action execution | Untrusted model output crosses into cash-balance and position mutation | Proposed trades/watchlist changes (structured, schema-validated) |
| Package registry → `backend/uv.lock` | Third-party code enters the runtime (`litellm`, `pydantic`, `python-dotenv`) | Installed package contents |
| `GET /api/chat` → Browser | Prior conversation history (including any LLM output) is replayed to the client and rendered | Chat messages, action annotations |
| Server → SQLite (`chat_messages`) | Conversation history and action outcomes persisted, plaintext, single-user local file | Chat content, action outcomes |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | `app/llm/actions.py` → `execute_trade()` | high | mitigate | Two independent layers: `_validate_trade_item()` rejects non-finite/non-positive quantity and invalid side before dispatch; `execute_trade()`'s own guard (`service.py:157-177`) is the first statement, ahead of normalization — as amended by T-03-37 (sell-only negative-quantity recovery happens in the normalizer, before this validator runs, and is itself a registered, verified threat) | closed |
| T-03-02 | Elevation of Privilege | `app/llm/actions.py` | high | mitigate | Chat actions applied only via `execute_trade()`/`add_watchlist_ticker()`/`remove_watchlist_ticker()`; negative grep for direct cash/position/trade persistence access confirms no second mutation path | closed |
| T-03-03 | Information Disclosure | `app/llm/client.py` logging | high | mitigate | Exception handler logs exception type + message only; failover logs model names + exception type/message; fence-recovery log is a bounded 200-char prefix — never full body, message list, or env var value | closed |
| T-03-04 | Spoofing | assistant `message` text | medium | mitigate | System prompt forbids asserting outcomes; outcomes travel as separate structured fields, rendered by badges independent of message text | closed |
| T-03-05 | Denial of Service | `POST /api/chat` LLM call | medium | mitigate | Every outbound-call failure mode degrades to a 200 message-only response via `parse_llm_response`'s fallback and broad exception handling | closed |
| T-03-06 | Repudiation | chat-originated trades in `trades` | low | accept | `trades` records no origin; single hardcoded `user_id="default"`, no second party to dispute against; `chat_messages.actions` provides the practical audit trail | closed (AR-03-01) |
| T-03-SC | Tampering | `uv add litellm pydantic python-dotenv` | high | mitigate | Blocking-human package-legitimacy checkpoint cleared (03-01-SUMMARY.md); versions pinned; `uv.lock` resolves all three with sha256 integrity hashes | closed |
| T-03-07 | Tampering | `routes/chat.py` `_actions_from_json()` | medium | mitigate | Parse+validate wrapped in a catch-all for JSON/validation/type/key errors, degrading to empty action lists rather than raising | closed |
| T-03-08 | Denial of Service | `POST /api/chat` prompt history | medium | mitigate | `PROMPT_HISTORY_LIMIT = 20` applied inside `build_messages()`; `get_messages(limit=50)` bounds the DB read | closed |
| T-03-09 | Tampering | prompt replay of prior messages | medium | mitigate | Replay carries only `{role, content}`; the `actions` column never enters prompt text | closed |
| T-03-10 | Information Disclosure | `chat_messages` table | low | accept | Chat content stored plaintext in `db/finally.db`; single-user local demo, same file already holds trade history | closed (AR-03-02) |
| T-03-11 | Tampering | rendering backend/LLM-supplied text in the chat panel | high | mitigate | Zero `dangerouslySetInnerHTML` repo-wide; chat content rendered via JSX children; no direct `fetch(` under `components/chat` | closed |
| T-03-12 | Spoofing | assistant bubble vs. action badges | medium | mitigate | Assistant bubble renders `message.content` only; badges are siblings driven by `action.outcome`, never parsed from message text | closed |
| T-03-13 | Denial of Service | rapid repeat chat submissions | low | mitigate | `isSendingRef` rejects re-entry before any await; input and Send button disabled while sending | closed |
| T-03-14 | Information Disclosure | dev CORS origin | low | accept | Same-origin in prod; single explicit `http://localhost:3000` CORS origin in dev; Phase 5 decides whether dev CORS ships | closed (AR-03-03) |
| T-03-15 | Spoofing | `ActionBadge.tsx` outcome rendering | high | mitigate | `executed = action.outcome === "executed"` is the sole driver of glyph/colour/`role="alert"`; nothing in the component reads `message` | closed |
| T-03-16 | Tampering | `ActionBadge.tsx` reason text | medium | mitigate | `action.reason` rendered as JSX children; no string transformation that could reinterpret content | closed |
| T-03-17 | Information Disclosure | rejection text embedding cash/share figures | low | accept | Figures are the user's own, already shown in header and positions table | closed (AR-03-04) |
| T-03-22 | Spoofing | collapsed-panel unread indicator | low | mitigate | `hasUnread` gated on a non-null baseline armed only post-hydrate; the old `collapsedAtCount` mechanism fully removed | closed |
| T-03-24 | Tampering | 03-UI-SPEC.md amendment integrity | medium | mitigate | Exactly one `## Amendments` heading, cross-referencing G-03-1/G-03-2 | closed |
| T-03-23 | Information Disclosure | collapsed rail content | low | accept | Collapsed rail renders only a static word, a glyph, and a boolean dot — no additional content exposed | closed (AR-03-05) |
| T-03-25 | Denial of Service | LLM failover retry logic | medium | mitigate | Exactly two straight-line attempts (primary + one fallback); no loop, no retry counter | closed |
| T-03-26 | Denial of Service | fenced-code-block recovery regex | medium | mitigate | Anchored, module-scope-compiled, non-greedy regex; applied once, retried only when stripping actually changed the input | closed |
| T-03-27 | Elevation of Privilege | fallback model call context | medium | mitigate | Fallback call reuses the identical `messages` object from the primary attempt; nothing derived from the failed response is constructed or injected | closed |
| T-03-28 | Spoofing | fence-recovered response validation | high | mitigate | Recovery re-runs the same Pydantic schema validator, no hand-parsing/repair/synthesis; recovered items pass through the identical execution gate | closed |
| T-03-29 | Information Disclosure | fence-recovery logging | low | mitigate | Bounded 200-char prefix logged; model names + exception type/message only | closed |
| T-03-30 | Repudiation | streaming flag / dead toggle removal | medium | mitigate | `acompletion()` passes no `stream` kwarg; `enable_json_schema_validation` fully removed; warning/error logged on every degraded path | closed |
| T-03-31 | Tampering | rail full-height spec amendment | medium | mitigate | `03-UI-SPEC.md` Dock-placement bullet explicitly states full-column height | closed |
| T-03-32 | Repudiation | 03-UI-SPEC.md G-03-4 amendment integrity | low | mitigate | One `## Amendments` heading, 3 references to G-03-4 | closed |
| T-03-33 | Spoofing | enlarged collapsed-rail click target | low | accept | Enlarged target reaches only a non-destructive, instantly reversible expand action | closed (AR-03-06) |
| T-03-34 | Information Disclosure | taller collapsed rail | low | accept | Taller rail renders no additional content beyond the existing label/glyph/dot (carries T-03-23 forward) | closed (AR-03-07) |
| T-03-35 | Tampering | `actions.py` normalize-once-and-reuse | high | mitigate | `_normalize_trade_item()`/`_normalize_watchlist_item()` each called exactly once per loop iteration; validators take the normalized values as keyword args; no second raw-value derivation exists anywhere else in the file | closed |
| T-03-36 | Elevation of Privilege | watchlist add/remove dispatch | high | mitigate | Explicit `if action == "add" / elif action == "remove" / else: error` — the destructive branch is unreachable by fallthrough and never raises | closed |
| T-03-37 | Tampering | sell-only negative-quantity sign recovery | medium | mitigate | Recovery gated on `side == "sell"` AND numeric AND finite AND `< 0`; negative buy falls through untouched and is rejected; direction never inferred from sign | closed |
| T-03-38 | Elevation of Privilege | `execute_trade()` guard (non-chat callers) | high | mitigate | Guard unmodified by 03-08, including the `isinstance(quantity, bool)` exclusion; still the first statement, ahead of normalization | closed |
| T-03-39 | Denial of Service | LLM schema field constraints | medium | mitigate | `Field(description=...)` only, no `gt=`/`ge=`/`Literal[`/etc. — a single bad item cannot discard the whole response, matching the module's documented permissiveness rationale | closed |
| T-03-40 | Repudiation | action outcome annotation | medium | mitigate | Every annotation (executed or error) is built from the same normalized locals that were validated and executed — a badge can never describe a different action than the one performed | closed |
| T-03-41 | Spoofing | new schema descriptions / prompt bullet | low | accept | Static developer-authored text; no user data or model output interpolated into schema descriptions or the system prompt | closed (AR-03-08) |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-06 | `trades` records no origin; single hardcoded `user_id="default"` with no second party to dispute against; `chat_messages.actions` provides the practical audit trail | Plan 03-01 threat model | 2026-09-17 |
| AR-03-02 | T-03-10 | Chat content stored plaintext in `db/finally.db`; single-user local demo, same file already holds trade history | Plan 03-02 threat model | 2026-09-18 |
| AR-03-03 | T-03-14 | Same-origin in production; single explicit `http://localhost:3000` CORS origin in dev; Phase 5 decides whether dev CORS ships | Plan 03-03 threat model | 2026-09-18 |
| AR-03-04 | T-03-17 | Rejection text embeds the user's own cash/share figures, already shown in the header and positions table | Plan 03-04 threat model | 2026-09-18 |
| AR-03-05 | T-03-23 | Collapsed rail renders only a static word, a glyph, and a boolean dot | Plan 03-05 threat model | 2026-09-19 |
| AR-03-06 | T-03-33 | Enlarged rail click target reaches only a non-destructive, instantly reversible expand action | Plan 03-07 threat model | 2026-09-21 |
| AR-03-07 | T-03-34 | Taller rail renders no additional content beyond the existing label/glyph/dot | Plan 03-07 threat model | 2026-09-21 |
| AR-03-08 | T-03-41 | New schema descriptions and prompt bullet are static developer-authored text, no user data or model output interpolated | Plan 03-08 threat model | 2026-09-21 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-21 | 38 | 38 | 0 | gsd-security-auditor (ASVS L1, plan-time register spanning all 8 plans including 4 gap-closure plans; verified mitigations against implementation, not merely claimed by SUMMARY — 30 mitigate/transfer threats closed by direct code evidence, 8 accept-disposition threats closed by transcription into this Accepted Risks Log) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-21
