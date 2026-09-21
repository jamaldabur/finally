---
status: diagnosed
trigger: "when I tell the chat sell 2 AAPL, I get '✕ sell -2 AAPL — Invalid quantity: -2.0'"
created: 2026-09-21T15:00:00Z
updated: 2026-09-21T16:20:00Z
---

## Current Focus

bug_class: Mandelbug (transient, non-deterministic — depends on which backing model the free auto-router selects for that call; deterministic once conditioned on the backing model)
hypothesis: CONFIRMED — see Resolution. Three conditions must hold simultaneously (AND-gate): (1) the router picks a backing model that encodes sell direction as a negative quantity, (2) neither the prompt nor the JSON Schema carries any signal that quantity must be positive, (3) the validator rejects rather than normalizes.
test: [complete] Local repro + live A/B probe against the real free router (27 calls)
expecting: [complete]
next_action: Return diagnosis. goal=find_root_cause_only — no fix applied.

reasoning_checkpoint:
  hypothesis: "'sell 2 AAPL' fails because the free auto-router sometimes selects a backing model that encodes sell direction as a signed (negative) quantity, and the pipeline has neither a signal that prevents it (prompt + JSON Schema are both silent on quantity sign) nor a recovery step that normalizes it (_validate_trade_item rejects quantity <= 0 outright)."
  confirming_evidence:
    - "Local repro: _validate_trade_item(LlmTradeItem('AAPL','sell',-2.0)) returns exactly 'Invalid quantity: -2.0'; execute_llm_actions() yields AnnotatedTrade(side='sell', quantity=-2.0, price=None, outcome='error') -> ActionBadge renders '✕ sell -2 AAPL' verbatim. Byte-identical to the user report."
    - "ChatResponseSchema.model_json_schema() shows quantity as {'title':'Quantity','type':'number'} — no description, no minimum/exclusiveMinimum. side is {'type':'string'} with no enum. The model receives zero semantic signal."
    - "SYSTEM_PROMPT (client.py:127-148) contains no rule about quantity sign or the side/quantity relationship."
    - "LIVE probe, 27 real calls: negative quantity reproduced 2x, both from backing model dots-studio/dots-3-note-preview:free (2/2 of its appearances under the current prompt). 8 distinct backing models observed."
    - "LIVE A/B: adding one explicit positive-quantity prompt rule flipped dots-studio/dots-3-note-preview:free from 2/2 negative to 2/2 positive."
  falsification_test: "If the live probe had produced zero negative quantities across ~25 calls AND the offending model could not be identified, the 'systemic contract gap' claim would be weakened to 'rare model fluke'. It did not — it reproduced twice, deterministically per backing model."
  fix_rationale: "Normalization at actions.py recovers the intent when the sign is REDUNDANT with the side (side='sell', quantity<0); prompt+schema descriptions reduce how often bad items are produced at all. These address different stages (recovery vs prevention), not the same one twice."
  blind_spots:
    - "N=27 live calls is a small sample of a non-stationary router; the per-call negative rate (~2/10 trade-emitting responses) is an estimate, not a stable statistic."
    - "Did not test whether a model ever emits side='buy' with a negative quantity meaning 'sell' (the ambiguous case). Blanket abs() would silently invert that into a real BUY — this is why sell-only normalization is recommended over blanket abs()."
    - "Did not measure whether the added prompt rule increases the 'no trade emitted at all' rate (arm B showed 3/6 no-trade vs arm A 1/6, but sample is too small and confounded by a ServiceUnavailableError)."
  candidate_causes:
    - "code: _validate_trade_item() rejects quantity <= 0 with no normalization/recovery step (actions.py:70-71)"
    - "code (adjacent, separate defect): validator normalizes with .strip().lower() but executor re-derives with .lower() only — confirmed intent inversion, see Evidence"
    - "data/contract: the JSON Schema emitted via response_format carries no description or constraint on quantity, and no enum on side"
    - "config: SYSTEM_PROMPT carries no positive-quantity rule"
    - "environment: MODEL='openrouter/openrouter/free' is an auto-router selecting a different backing model per call (8 distinct observed in 27 calls) — instruction adherence is non-stationary by construction"
    - "process/test: the LLM_MOCK path is structurally incapable of emitting a negative quantity (_TRADE_PATTERN matches unsigned digits only), so no automated test could ever have caught this"
  and_gate: "YES — the user-visible failure requires (model emits negative qty) AND (no preventive signal exists) AND (no recovery step exists), simultaneously. Removing any one condition removes the symptom. root_cause is therefore a SET, not a single cause."

## Symptoms

expected: Telling the AI assistant "sell 2 AAPL" (holding >= 2 shares) executes a sell and shows a green executed badge with a fill price.
actual: Red error badge "✕ sell -2 AAPL — Invalid quantity: -2.0". No crash, no 5xx, badge rendered correctly.
errors: "Invalid quantity: -2.0" (from _validate_trade_item, backend/app/llm/actions.py:71)
reproduction: Manual UAT round 2, Phase 3 AI Chat Copilot, REAL (non-mock) LLM path, MODEL = "openrouter/openrouter/free" (free auto-router — different backing model per call).
started: Discovered 2026-09-21 during round-2 UAT for phase 03-ai-chat-copilot (gap G-03-5). NEW defect, distinct from G-03-3 (fence recovery / silent drop).

## Eliminated

<!-- APPEND only -->

## Evidence

- timestamp: 2026-09-21T15:00:00Z
  checked: backend/app/llm/actions.py::_validate_trade_item (lines 60-72)
  found: Rejects quantity <= 0 with f"Invalid quantity: {item.quantity!r}". No normalization (no abs()) anywhere before it.
  implication: A negative quantity is a hard reject at the chat layer, before execute_trade() is ever called. Error string matches the report exactly.

- timestamp: 2026-09-21T15:00:00Z
  checked: backend/app/llm/schema.py::LlmTradeItem
  found: `quantity: float` — plain field, NO Field(description=...), NO Field(gt=0). Same for ticker/side/action. Module docstring documents the deliberate permissiveness (one bad item must not discard the whole response).
  implication: The JSON Schema emitted to the model via response_format=ChatResponseSchema carries only {"type": "number"} for quantity — zero semantic signal that quantity must be positive / that side alone conveys direction.

- timestamp: 2026-09-21T15:00:00Z
  checked: backend/app/llm/client.py::SYSTEM_PROMPT (lines 127-148)
  found: No mention of quantity sign, magnitude, or the side/quantity relationship. Only responsibilities + two hard constraints (no outcome assertions, no pressure framing).
  implication: No prompt-level signal either. The model has NO signal anywhere steering it away from a signed-quantity encoding.

- timestamp: 2026-09-21T15:00:00Z
  checked: backend/app/portfolio/service.py::execute_trade (lines 157-177)
  found: Independent leading guard rejects non-finite/bool/<=0 quantity with the SAME message shape f"Invalid quantity: {quantity!r}". Added in Plan 03-01 Task 3 explicitly to guard non-chat/direct callers.
  implication: Two layers produce identical error text. The one the user saw is the actions.py layer (it short-circuits first). execute_trade()'s guard is a genuine last line of defense for direct callers and should not be relaxed.

- timestamp: 2026-09-21T15:40:00Z
  checked: LOCAL REPRO — scratchpad/repro_negative_qty.py, 6 experiments, run under `uv run python` from backend/
  found: |
    E1: _validate_trade_item(LlmTradeItem('AAPL','sell',-2.0)) -> 'Invalid quantity: -2.0'  (exact match to report)
    E2: execute_llm_actions() -> AnnotatedTrade(ticker='AAPL', side='sell', quantity=-2.0, price=None,
        outcome='error', reason='Invalid quantity: -2.0'); position unchanged at 5.0, cash unchanged.
        ActionBadge.tsx renders `${glyph} ${side} ${quantity} ${ticker}` -> "✕ sell -2 AAPL" verbatim.
    E3: execute_trade(side='sell', quantity=abs(-2.0)) -> status='executed', fill_price=190.0,
        position 5.0 -> 3.0, cash 9050 -> 9430. Normalization WOULD have produced the correct trade.
    E4: execute_trade(side='sell', quantity=-2.0) -> status='error', reason='Invalid quantity: -2.0'
        (its OWN independent guard, identical string).
    E5: ChatResponseSchema.model_json_schema() -> quantity is {"title":"Quantity","type":"number"};
        side is {"title":"Side","type":"string"}. NO description, NO minimum, NO enum anywhere.
    E6: build_mock_response('sell -2 AAPL') -> trades=[] (the '-' breaks _TRADE_PATTERN's \s+\d match);
        'sell 2 AAPL' -> [('AAPL','sell',2.0)]. The mock can NEVER emit a negative quantity.
  implication: |
    Root cause confirmed byte-for-byte. abs() normalization is a valid recovery. The identical guard
    exists in execute_trade(), so normalization must happen BEFORE that call (in actions.py) —
    execute_trade()'s guard does not need to change. And LLM_MOCK=true (what every automated test and
    the entire E2E suite runs under) is structurally incapable of reproducing this, which is the
    complete answer to "why wasn't this caught".

- timestamp: 2026-09-21T15:55:00Z
  checked: LIVE A/B PROBE — scratchpad/probe_live_llm.py, real OPENROUTER_API_KEY, MODEL='openrouter/openrouter/free', user_message='sell 2 AAPL', context seeded with a 5-share AAPL position. 6 calls per arm.
  found: |
    ARM A (current SYSTEM_PROMPT verbatim), 6 calls -> 6 DIFFERENT backing models:
      nvidia/nemotron-3-ultra-550b-a55b:free           -> ('AAPL','sell', 2.0)
      cohere/north-mini-code:free                      -> []            (no trade emitted at all)
      nex-agi/nex-n2.5-mini:free                       -> ('AAPL','sell', 2.0)
      nvidia/nemotron-3-nano-omni-30b-a3b-reasoning    -> ('AAPL','sell', 2.0)
      nex-agi/nex-n2.5-mini:free                       -> ('AAPL','sell', 2.0)
      dots-studio/dots-3-note-preview:free             -> ('AAPL','sell',-2.0)   <<< BUG REPRODUCED
    ARM B (same prompt + one explicit "quantity is ALWAYS positive, side conveys direction" rule):
      0 negative quantities. dots-studio/dots-3-note-preview:free appeared TWICE and emitted
      ('AAPL','sell', 2.0) both times.
  implication: |
    The bug is NOT a user-side fluke — it reproduced on the first N=6 live probe. Instruction
    adherence is per-backing-model, and the free auto-router picks a different one per call.
    The prompt rule demonstrably corrects the one offending model (2/2 negative -> 2/2 positive).

- timestamp: 2026-09-21T16:05:00Z
  checked: LIVE PROBE ROUND 2 — scratchpad/probe_round2.py, 15 calls across 3 phrasings ("sell 2 AAPL", "sell 2 shares of AAPL", "please sell 2 AAPL for me"), current prompt only
  found: |
    8 calls succeeded (7 were RateLimitError/Timeout — free tier). Of 5 trade-emitting responses:
      4 positive, 1 NEGATIVE — again exclusively dots-studio/dots-3-note-preview:free.
    Combined across both rounds under the CURRENT prompt: 10 trade-emitting responses, 2 negative,
    both from dots-studio/dots-3-note-preview:free (2/2 of that model's appearances).
    Also observed: nex-agi/nex-n2.5-mini:free returned side='SELL' (uppercase) — already handled by
    the WR-02 case-normalization fix (commit b2187b2), which is direct precedent for this exact
    class of "model encodes the same intent in a different surface form" defect.
  implication: |
    Systemic, not a one-off. The defect is deterministic *conditioned on the backing model* and
    random only in which model the router picks. ~1 in 5 trade-emitting responses on this sample.
    Bug class is Mandelbug, not Bohrbug.

- timestamp: 2026-09-21T16:15:00Z
  checked: ADJACENT DEFECT — scratchpad/probe_strip_gap.py. _validate_trade_item()/_validate_watchlist_item() validate `item.side.strip().lower()` / `item.action.strip().lower()`, but execute_llm_actions() re-derives with `item.side.lower()` / `change.action.lower()` — NO .strip().
  found: |
    side=' buy'  -> validate returns None (PASSES), execute_trade rejects: "Invalid side: ' buy'"
    side='BUY '  -> validate PASSES, execute_trade rejects: "Invalid side: 'buy '"
    side=' SELL' -> validate PASSES, execute_trade rejects: "Invalid side: ' sell'"
    action=' add' on a watchlist that CONTAINS AAPL:
      LLM asked to ADD AAPL -> AnnotatedWatchlistChange(action=' add', outcome='executed', reason=None)
      watchlist BEFORE: [AAPL, AMZN, GOOGL, JPM, META, MSFT, NFLX, NVDA, TSLA, V]
      watchlist AFTER : [AMZN, GOOGL, JPM, META, MSFT, NFLX, NVDA, TSLA, V]   <-- AAPL DELETED
      -> ' add' != 'add', so it falls into the else/REMOVE branch and reports a GREEN "executed" badge.
  implication: |
    Same root-cause class as the reported bug (validator normalizes a value, executor uses the raw
    one), but strictly MORE severe: a requested ADD silently performs a REMOVE and reports success.
    Arguably a higher-priority finding than G-03-5 itself. Not yet filed as a gap.

## Resolution

root_cause: |
  A three-condition AND-gate (no single cause is sufficient):

  (1) ENVIRONMENT — MODEL = "openrouter/openrouter/free" is an auto-router that selects a different
      backing model per call (8 distinct models observed across 27 live calls). One of them,
      dots-studio/dots-3-note-preview:free, deterministically encodes "sell 2" as
      {"side":"sell","quantity":-2} — a redundant signed-quantity representation.

  (2) CONTRACT — nothing anywhere in the project tells the model that quantity is a positive
      magnitude and that `side` alone conveys direction. SYSTEM_PROMPT (client.py:127-148) is silent;
      LlmTradeItem (schema.py:20-23) has no Field(description=...), so the JSON Schema the provider
      actually enforces is literally {"title":"Quantity","type":"number"} with no enum on `side`
      either. There is ZERO preventive signal.

  (3) CODE — _validate_trade_item() (actions.py:70-71) rejects any quantity <= 0 outright with
      f"Invalid quantity: {item.quantity!r}". It has no normalization/recovery step, so a signed
      quantity whose sign is merely REDUNDANT with an already-correct `side` is discarded on a
      technicality rather than recovered.

  Remove any one condition and the user never sees the failure. It surfaced now because Phase 3's
  round-2 UAT is the first exercise of the REAL (non-mock) LLM path.

  Separately confirmed (same root-cause class, distinct defect, NOT yet filed):
  the validator normalizes side/action with .strip().lower() but the executor re-derives them with
  .lower() only — a whitespace-padded " add" bypasses validation and silently performs a REMOVE while
  reporting a green "executed" badge.

fix: [NOT APPLIED — goal: find_root_cause_only. Recommended direction in the returned diagnosis.]
verification: [n/a — diagnosis only]
files_changed: []
