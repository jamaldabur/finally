---
status: diagnosed
trigger: "With LLM_MOCK unset (real OpenRouter path, model = openrouter/openrouter/free), user typed 'sell 2 AAPL' into chat and the assistant's displayed message was: 'Invalid placeholder, avoid outputting non-JSON text when schema is required.' — not a real answer, not the app's own generic fallback text, but what reads like a leaked schema-enforcement instruction string."
created: 2026-09-20T21:05:00Z
updated: 2026-09-20T21:05:00Z
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-29
  status: diagnosed
---

## Current Focus

bug_class: Heisenbug/Mandelbug (non-deterministic — free auto-router picks a different backing model per call). SBFL skipped: no failing test exists, flaky spectrum would poison ranking.

hypothesis: |
  TWO independent contributing causes (AND-gate = YES):
  (A) [code] parse_llm_response()'s single except branch uses raw.strip() verbatim as the
      user-facing message for EVERY parse failure — no distinction between "valid prose"
      and "garbage/leaked instruction". Any non-JSON the model emits is rendered as the
      assistant's real reply.
  (B) [config] litellm.enable_json_schema_validation = True is DEAD on this call path
      because _call_llm_structured() passes stream=True. litellm/utils.py:1886-1907 returns
      early for streaming requests, before post_call_processing() at :1911 — the only place
      that flag is ever honored. So the documented "client-side backstop" never runs, and
      malformed output reaches parse_llm_response() un-flagged as a schema violation.
  Plus amplifier (C): routes/chat.py:166 persists the garbage as the assistant turn, so it
  survives reload AND is replayed into every subsequent prompt via build_messages().

test: differential experiment — acompletion(mock_response="not json", response_format=ChatResponseSchema) with stream=False vs stream=True; expect JSONSchemaValidationError raised only when stream=False.
expecting: stream=False raises (flag works) / stream=True returns silently (flag bypassed) -> confirms (B)
next_action: DONE — differential ran and confirmed (B). Diagnosis returned to caller. goal=find_root_cause_only, so NO fix applied.

reasoning_checkpoint:
  hypothesis: "Two contributing causes, both confirmed: (A) parse_llm_response() renders raw model text verbatim as the assistant's message for every parse failure; (B) litellm.enable_json_schema_validation=True is inert because stream=True makes litellm's async wrapper return before post_call_processing(), the only place that flag is honored."
  confirming_evidence:
    - "Direct observation: acompletion(mock_response=<the exact garbage string>, response_format=ChatResponseSchema) RAISES JSONSchemaValidationError with stream=False and returns silently with stream=True."
    - "Direct observation: get_chat_response() with _call_llm_structured returning the garbage string returns message == the garbage string verbatim, with 0 ERROR-level log records — matching the user's report exactly (200 OK, no log line)."
    - "Static read: litellm/utils.py:1886-1907 returns inside the _is_streaming_request() branch, before post_call_processing() at :1911."
  falsification_test: "If stream=False had ALSO returned silently, (B) would be false and the missing log line would need another explanation. It raised — (B) holds."
  fix_rationale: "N/A — diagnosis only. Fix direction reported to caller."
  blind_spots:
    - "Did not reproduce against the live free router (probabilistic by design; the user pre-confirmed this and it is not needed — the handling defect is deterministic and was reproduced directly)."
    - "Did not determine the ultimate PROVENANCE of the string itself. Confirmed NOT from litellm (grep of the installed package for 'avoid outputting non-JSON text'/'Invalid placeholder'/'schema is required' returns zero hits). Most likely emitted by the free router's backing model. Provenance does not change the root cause — the defect is that ANY such string is rendered verbatim."
  candidate_causes:
    - "code: parse_llm_response()'s single except branch uses raw.strip() verbatim (CONFIRMED, primary)"
    - "config: enable_json_schema_validation inert under stream=True (CONFIRMED, load-bearing — it is why the correct fallback never fired and why no log line appeared)"
    - "environment/dependency: MODEL=openrouter/openrouter/free auto-router with no FALLBACK_MODEL and no retry (CONFIRMED — grep of backend/app finds zero retry/fallback)"
    - "process/test: the existing regression test's oracle is implicit/too weak — it asserts only that message is truthy, so it PASSES while displaying '{\"message\": 42}' verbatim (CONFIRMED)"
  and_gate: "YES — this required (1) a backing model emitting non-JSON AND (2) the schema backstop being inert AND (3) the verbatim fallback. Had (2) worked, the call would have raised JSONSchemaValidationError, been caught by get_chat_response()'s except Exception, logged 'LLM call failed', and returned the CORRECT generic fallback. The right message already exists in the code; a streaming/config interaction silently disabled the path that reaches it."

## Symptoms

expected: With the real (non-mock) LLM path active, the assistant's `message` text should always be a coherent response — either a real answer, or on failure/malformed output a clear generic fallback. Never raw model output that looks like a leaked internal instruction.
actual: Displayed message was literally "Invalid placeholder, avoid outputting non-JSON text when schema is required."
errors: HTTP 200 OK. NO "LLM call failed" / ERROR-level line in uvicorn log — so get_chat_response()'s except Exception path did NOT run. acompletion() succeeded and returned content that fell through parse_llm_response()'s except branch, whose fallback uses raw.strip() verbatim as message.
reproduction: Manual UAT — Phase 3, real backend, LLM_MOCK unset, real OPENROUTER_API_KEY, sent "sell 2 AAPL" via chat UI. NOT deterministically reproducible — MODEL = "openrouter/openrouter/free" is OpenRouter's auto-router across free backing models with varying reliability.
started: 2026-09-20, right after LLM model switched from openrouter/openai/gpt-oss-120b to openrouter/openrouter/free (Plan 03-01 deviation) due to HTTP 402 insufficient credits.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-09-20T21:05:00Z
  checked: backend/app/llm/client.py parse_llm_response() lines 153-162
  found: |
    def parse_llm_response(raw: str) -> ChatResponseSchema:
        try:
            return ChatResponseSchema.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError, ValueError):
            stripped = raw.strip()
            message = stripped if stripped else "I couldn't process that — please try again."
            return ChatResponseSchema(message=message, trades=[], watchlist_changes=[])
    Single except branch catches ALL three failure modes (ValidationError, JSONDecodeError, ValueError) and treats them identically: raw.strip() becomes the user-visible message verbatim. The ONLY discriminator is empty vs. non-empty — there is no distinction between "valid prose that just isn't JSON" and "garbage / leaked instruction text".
  implication: Confirms context hypothesis Q1 and Q2 — yes, verbatim for every parse failure; no, zero distinction between garbage and plausible prose.

- timestamp: 2026-09-20T21:05:00Z
  checked: backend/app/llm/client.py line 35 and whole-file grep for fallback/retry
  found: MODEL = "openrouter/openrouter/free" is the ONLY model constant. No FALLBACK_MODEL, no retry loop, no num_retries kwarg on acompletion().
  implication: A single bad auto-router pick has no second chance — its raw output goes straight to the user.

- timestamp: 2026-09-20T21:15:00Z
  checked: "grep of installed litellm (backend/.venv/Lib/site-packages/litellm) for 'avoid outputting non-JSON text', 'Invalid placeholder', 'schema is required', 'non-JSON text'"
  found: "ZERO hits. LiteLLM's only schema-related prompt injection is default_response_schema_prompt() in litellm_core_utils/prompt_templates/factory.py:5182, whose text is 'Use this JSON schema: ```json {schema}```' — nothing resembling the reported string. LiteLLM performs no retry/repair prompt on schema failure; it just raises JSONSchemaValidationError (exceptions.py:895)."
  implication: "Answers context Q4: NO — the string is not LiteLLM's internal text leaking. It originates upstream (almost certainly the free router's backing model). Provenance is irrelevant to the root cause: the defect is that ANY such string is displayed verbatim."

- timestamp: 2026-09-20T21:18:00Z
  checked: "litellm/utils.py async client wrapper, lines 1886-1917, plus _is_streaming_request() at :2145"
  found: "_is_streaming_request() returns True whenever kwargs['stream'] is True. In that branch the wrapper RETURNS at line 1904 (wrap_streaming_result_for_cache). post_call_processing() — the ONLY function in the whole package that reads enable_json_schema_validation (confirmed by grep: utils.py:1397 is the sole consumer) — sits at line 1911, unreachable. streaming_handler.py contains no schema validation of its own."
  implication: "litellm.enable_json_schema_validation = True (client.py:33) is DEAD CODE on this project's call path, because _call_llm_structured() passes stream=True (client.py:143). The module docstring's claim that it is 'a client-side backstop ... rather than trusting the provider unconditionally' is false as written."

- timestamp: 2026-09-20T21:22:00Z
  checked: "Differential experiment (scratchpad/stream_validation_probe.py): acompletion(model=MODEL, response_format=ChatResponseSchema, mock_response=<exact reported garbage string>) with stream=False vs stream=True"
  found: |
    stream=False : RAISED JSONSchemaValidationError: litellm.JSONSchemaValidationError: model=, returned an invalid response=Invalid placeholder, avoid outputting non-JSON t...
    stream=True  : NO RAISE -> accumulated='Invalid placeholder, avoid outputting non-JSON text when schema is required.'
  implication: "EMPIRICAL SMOKING GUN. Confirms the bypass and explains the missing log line. On stream=False the flag fires -> get_chat_response()'s except Exception catches it -> logs 'LLM call failed' -> returns the CORRECT generic fallback. On the production stream=True path nothing raises, so the garbage flows straight into parse_llm_response()."

- timestamp: 2026-09-20T21:26:00Z
  checked: "End-to-end chain through the project's own code (scratchpad/e2e_chain_probe.py), real path, LLM_MOCK unset, _call_llm_structured monkeypatched to return the exact reported string"
  found: |
    parse_llm_response(GARBAGE).message              = 'Invalid placeholder, avoid outputting non-JSON text when schema is required.'
    parse_llm_response('You currently hold 5 AAPL.') = 'You currently hold 5 AAPL.'
    parse_llm_response('{"message": 42}')            = '{"message": 42}'
    get_chat_response(...).message                   = 'Invalid placeholder, avoid outputting non-JSON text when schema is required.'
    ERROR-level log records emitted: 0
  implication: "Deterministic reproduction of the HANDLING defect (the model's output is the Heisenbug; the handling is deterministic). Reproduces the user's report exactly: verbatim garbage as the message, HTTP 200, zero ERROR logs. Also shows garbage, plain prose, and valid-JSON-bad-schema are all treated identically."

- timestamp: 2026-09-20T21:30:00Z
  checked: "scratchpad/discriminator_probe.py — markdown-code-fenced but otherwise PERFECT response, and pydantic ValidationError error-type tags"
  found: |
    Input: ```json\n{"message": "Selling 2 shares of AAPL.", "trades": [{"ticker":"AAPL","side":"sell","quantity":2}], "watchlist_changes": []}\n```
    -> message = the entire raw fenced blob (fences included)
    -> trades  = []   <-- the trade is SILENTLY DROPPED, never executed
    pydantic error types: non-JSON garbage -> ['json_invalid']; plain prose -> ['json_invalid']; valid JSON bad schema -> ['string_type']
  implication: |
    TWO findings.
    (1) SEVERITY ESCALATION beyond UX: a correct, well-formed model response wrapped in a markdown code fence loses its trades entirely — the user asks "sell 2 AAPL", the model correctly requests it, and NO trade executes while raw JSON is shown. This is a correctness/agentic-loop failure, not cosmetics. The sibling agent-teams branch has _strip_code_fence()/_recover_actions_json() built specifically for this observed free-router behavior; finally-gsd has neither.
    (2) Answers context Q2: pydantic DOES expose a discriminator ('json_invalid' = not JSON at all vs 'string_type'/'missing' = JSON that failed the schema) and agent-teams uses it (_is_json_invalid_error()). finally-gsd's single except branch collapses both. BUT note the honest limit: 'json_invalid' cannot separate garbage from legitimate prose — both tag identically. So no classifier can reliably tell "leaked instruction" from "real prose answer"; the fix must be to stop showing raw text, not to try to classify it.

- timestamp: 2026-09-20T21:34:00Z
  checked: "backend/tests/llm/test_client.py::test_parse_llm_response_never_raises_and_falls_back_to_message (lines 13-21)"
  found: "Iterates ('', 'I think you should buy Apple.', '{\"message\": 42}') and asserts ONLY `assert result.message` (truthy) plus both action lists empty. It never asserts WHAT the message is. Oracle type: IMPLICIT (weakest tier — 'did not crash / is non-empty'). For the '{\"message\": 42}' case the test passes while the user-visible message is literally the string '{\"message\": 42}'. No test covers the markdown-code-fence input. No test asserts trades survive a recoverable parse."
  implication: "Answers context Q3: the scenario IS mechanically exercised but with an oracle too weak to detect the defect — the test actively encodes the buggy behavior as acceptable. This is the 'why wasn't it caught' answer: not a missing test, a missing assertion."

- timestamp: 2026-09-20T21:38:00Z
  checked: "backend/app/routes/chat.py:166 and build_messages() history replay (client.py:125-128); frontend/components/chat/ChatMessageList.tsx:105,116"
  found: "post_chat() persists the fallback message unconditionally: `await insert_message('assistant', llm_response.message, ...)`. get_messages() feeds that row back as history on the NEXT request, and build_messages() replays role/content into the prompt. Frontend renders {message.content} verbatim with no sanitization layer."
  implication: "AMPLIFIER: the garbage is not transient. It persists across reload (permanently in visible history) AND is injected into every subsequent prompt as prior assistant turn — a self-poisoning context loop that makes later turns MORE likely to also emit non-JSON. No downstream layer filters it."

- timestamp: 2026-09-20T21:40:00Z
  checked: "grep -rn 'FALLBACK_MODEL|fallbacks|num_retries|max_retries|retry' backend/app/ ; git show agent-teams:backend/app/llm/client.py"
  found: "finally-gsd: ZERO retry/fallback in the LLM path (only market/massive.py has retries). agent-teams: MODEL='openrouter/openrouter/free' PAIRED WITH FALLBACK_MODEL='openrouter/nvidia/nemotron-3-super-120b-a12b:free', _call_structured_llm() tries MODEL once then fails over once, plus a CONSTANT FALLBACK_MESSAGE='Sorry, I had trouble processing that.' (never raw model text), plus _strip_code_fence/_recover_actions_json/_is_json_invalid_error."
  implication: "Answers context Q5: confirmed no fallback exists here. The sibling branch independently hit this exact class of free-router flakiness and built four distinct mitigations for it; none were carried over when 03-01's deviation adopted the same flaky model."

## Resolution

root_cause: |
  Three confirmed contributing causes (AND-gate fired — all three were required):

  (1) [code, PRIMARY] backend/app/llm/client.py:153-162 — parse_llm_response()'s single
      except branch treats every parse failure identically and uses the model's raw text
      verbatim as the user-facing message: `message = stripped if stripped else "..."`.
      The only discriminator is empty vs. non-empty. Garbage, leaked instruction text,
      legitimate prose, and valid-JSON-that-failed-schema all render identically as the
      assistant's real reply. The generic fallback string is reachable ONLY when the model
      returns literally nothing.

  (2) [config, LOAD-BEARING] backend/app/llm/client.py:33 vs :143 — litellm.enable_json_schema_validation
      = True is inert because _call_llm_structured() passes stream=True. litellm/utils.py's
      async wrapper returns at :1904 for streaming requests, before post_call_processing()
      at :1911, which is the sole consumer of that flag. Proven empirically: identical call
      raises JSONSchemaValidationError with stream=False, returns silently with stream=True.
      This is why NO 'LLM call failed' log appeared and why the CORRECT fallback message
      ("I'm having trouble reaching the assistant right now...") — which already exists in
      get_chat_response()'s except branch — never fired. The code had the right answer; a
      streaming/config interaction silently disabled the route to it.

  (3) [environment] backend/app/llm/client.py:35 — MODEL = "openrouter/openrouter/free" is
      OpenRouter's auto-router across free backing models with no FALLBACK_MODEL and no
      retry anywhere in backend/app/. Adopted in the 03-01 deviation after the original
      model 402'd; its known flakiness was documented in 03-01-SUMMARY.md and explicitly
      judged "no new code is needed" on the assumption that parse_llm_response()'s fallback
      handled it — an assumption that is false for non-empty garbage, per (1).

  Severity is higher than the UAT report suggests: the same defect silently DROPS trades
  when a correct response arrives wrapped in a markdown code fence (verified) — an agentic
  loop failure, not just a cosmetic one. The bad message is also persisted and replayed
  into subsequent prompts.

fix: "NOT APPLIED — goal: find_root_cause_only"
verification: "N/A — diagnosis only"
files_changed: []
