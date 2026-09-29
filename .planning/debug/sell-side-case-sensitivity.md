---
status: diagnosed
trigger: "trying to sell 2 AAPL i get \"Requesting sale of 2 AAPL shares at the current price of $221.21. Estimated proceeds: $442.42. ✕ SELL 2 AAPL — Invalid side: 'SELL'\" — the model returned side as uppercase 'SELL' and it was rejected outright instead of being normalized to lowercase"
created: 2026-09-21T19:15:00Z
updated: 2026-09-21T19:15:00Z
goal: find_root_cause_only
gap_id: G-03-8
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-29
  status: diagnosed
---

## Current Focus

hypothesis: "CONFIRMED — the code at HEAD is correct. The uvicorn server the human tested against (PID 11468, started 2026-09-20 20:49:50 +0300, no --reload) has been running since BEFORE the two fixes landed, so round-3 UAT exercised ~45-hour-old in-memory bytecode."
test: "Directly observed the live process (Win32_Process CreationDate + CommandLine + netstat owner of :8000), reproduced the exact error string from the pre-b2187b2 source, and showed HEAD cannot produce it."
expecting: "n/a — root cause confirmed"
next_action: "Return ROOT CAUSE FOUND to caller. No source change required for G-03-8; the fix direction is a runtime restart plus a workflow guard so UAT can never again run against a stale process."

reasoning_checkpoint:
  hypothesis: "The badge text came from backend source predating commit b2187b2 (2026-09-21 14:08:47), still resident in a long-lived uvicorn process started 2026-09-20 20:49:50 with no --reload. It is a stale-runtime artifact, not a normalization defect."
  confirming_evidence:
    - "Win32_Process: PID 11468 `uvicorn.exe app.main:app --port 8000` (no --reload), CreationDate 9/20/2026 8:49:50 PM; netstat shows PID 11468 owns LISTENING 127.0.0.1:8000; /api/health still returns ok — this exact process served the UAT."
    - "8 backend commits landed after that process start, including b2187b2 and a06d51d."
    - "Executing the pre-b2187b2 _validate_trade_item against LlmTradeItem(side='SELL') returns the literal \"Invalid side: 'SELL'\" — byte-identical to the badge."
    - "Executing HEAD's _normalize_trade_item + _validate_trade_item against side='SELL' returns side='sell', validate=None (accepted)."
    - "Stored chat_messages row at 2026-09-21T16:11:20Z carries side='SELL' RAW in the annotation — HEAD stores the normalized 'sell' — so the annotation itself was built by pre-a06d51d code."
  falsification_test: "If HEAD's validator had returned \"Invalid side: 'SELL'\", or if the offending DB row's created_at predated the fixes (a replayed old message), or if the :8000 listener had started after 18:39, the hypothesis would be dead."
  fix_rationale: "No source fix is warranted — the source is already correct and its regression test is green. The real corrective action is operational: restart the backend before verification, and make that a required step."
  blind_spots: "Did not re-drive a live LLM turn through the restarted server (costs a real API call and the free router is non-deterministic); the proof is that the failing string is unreachable in HEAD source rather than a live green run."
  candidate_causes:
    - "code: _normalize_trade_item fails to lower-case side (Ishikawa: code) — ELIMINATED empirically"
    - "environment: long-lived uvicorn process without --reload holding pre-fix bytecode (Ishikawa: environment) — CONFIRMED"
    - "data: an old pre-fix annotation replayed from chat history by GET /api/chat (Ishikawa: data) — ELIMINATED via row created_at"
    - "process: UAT round 3 run with no restart step after backend fixes landed (Ishikawa: method) — CONFIRMED contributing"
  and_gate: "yes — two conditions had to hold simultaneously: (1) the dev server runs without --reload, so new code is never picked up, AND (2) the verification workflow has no restart/version step between landing a backend fix and human UAT. Either alone is harmless: with --reload the fixes would have loaded; with a restart step the missing --reload would not have mattered."

## Symptoms

expected: "With LLM_MOCK unset and a real OPENROUTER_API_KEY, sending 'sell 2 AAPL' executes with a green badge, positive quantity, and fill price, or fails for an honest reason — never a badge rejecting the trade on a case/whitespace technicality."
actual: |
  Requesting sale of 2 AAPL shares at the current price of $221.21. Estimated proceeds: $442.42.
  ✕ SELL 2 AAPL — Invalid side: 'SELL'
errors: "Invalid side: 'SELL'"
reproduction: "Test 3 in .planning/phases/03-ai-chat-copilot/03-UAT.md (G-03-8) — live non-mock LLM chat, 'sell 2 AAPL'"
started: "Round-3 UAT, immediately after 03-08 (G-03-5/G-03-6 normalization work) and 03-07 landed"

## Eliminated

- hypothesis: "`_normalize_trade_item()` lower-cases `action` for watchlist items but not `side` for trades (the asymmetry suggested in the investigation hints)."
  evidence: "backend/app/llm/actions.py:102 reads `side = item.side.strip().lower()` — the exact mirror of line 120's action handling. Executed at HEAD: side='SELL' -> 'sell', validate -> None. No asymmetry exists."
  timestamp: 2026-09-21T19:22:00Z

- hypothesis: "`LlmTradeItem.side`'s Field(description=...) or SYSTEM_PROMPT says nothing about case, so the model emits 'SELL' and the backend legitimately rejects it."
  evidence: "Irrelevant to the failure — uppercase 'SELL' is ACCEPTED at HEAD regardless of what the model emits. The description already says 'buy or sell, lower case' (schema.py:36) and the prompt covers sign, not case. Prompt wording cannot be the root cause of a rejection that HEAD does not perform."
  timestamp: 2026-09-21T19:23:00Z

- hypothesis: "The uppercase reason came from `execute_trade()` (backend/app/portfolio/service.py:173) receiving a raw side from the chat path."
  evidence: "execute_llm_actions() passes the normalized `side` local (actions.py:184), not `item.side`. Even the intermediate version (b2187b2..a06d51d) passed `item.side.lower()`. Neither can hand 'SELL' to execute_trade."
  timestamp: 2026-09-21T19:24:00Z

- hypothesis: "The badge was an OLD pre-fix annotation replayed into the panel by `GET /api/chat` history hydration, not a fresh turn."
  evidence: "The chat_messages row carrying reason \"Invalid side: 'SELL'\" has created_at 2026-09-21T16:11:20Z (19:11 local) — during round-3 UAT, 32 minutes AFTER a06d51d landed at 18:39 local — and its assistant text matches the user's report verbatim ('Requesting sale of 2 AAPL shares at the current price of $221.21'). It was written live, not replayed."
  timestamp: 2026-09-21T19:26:00Z

- hypothesis: "A stale Docker image / container was serving the app."
  evidence: "`docker ps -a` and `docker images` both return nothing. The app runs locally: `next dev` (frontend) and `uvicorn app.main:app --port 8000` (backend)."
  timestamp: 2026-09-21T19:27:00Z

## Evidence

- timestamp: 2026-09-21T19:16:00Z
  checked: "grep for the literal 'Invalid side' across the repo"
  found: "Exactly two producers at HEAD: backend/app/llm/actions.py:133 (_validate_trade_item) and backend/app/portfolio/service.py:173 (execute_trade). Both interpolate {side!r}."
  implication: "The badge string must come from one of these two — or from a version of one of them that is not HEAD."

- timestamp: 2026-09-21T19:17:00Z
  checked: "backend/app/llm/actions.py at HEAD — _normalize_trade_item / _validate_trade_item / execute_llm_actions"
  found: "_normalize_trade_item() does `side = item.side.strip().lower()` (line 102) and execute_llm_actions() calls _validate_trade_item(side=...) and execute_trade(side=...) with that SAME normalized value (lines 164-186)."
  implication: "At HEAD, side='SELL' is lowercased to 'sell' BEFORE validation. The hint's suspected asymmetry (side not lowercased like action) does NOT exist at HEAD — both are normalized identically."

- timestamp: 2026-09-21T19:18:00Z
  checked: "Can either HEAD validator emit the uppercase repr 'SELL'?"
  found: "No. actions.py:133 reprs the already-lowercased `side` param, so its worst output is \"Invalid side: 'sell'\" — unreachable, since 'sell' is in the allowed tuple. service.py:173 reprs the `side` it is passed, and the only chat caller passes the lowercased value."
  implication: "The observed string is NOT producible by HEAD code. The running code was not HEAD."

- timestamp: 2026-09-21T19:19:00Z
  checked: "git show b2187b2 -- backend/app/llm/actions.py (fix(03): WR-02 normalize case before validating trade side)"
  found: "The PRE-b2187b2 line was exactly: `if item.side not in (\"buy\", \"sell\"): return f\"Invalid side: {item.side!r}\"` — raw, un-normalized item.side in both the check and the repr."
  implication: "Code predating b2187b2 produces the observed string verbatim for side='SELL'. Strong candidate: a stale running process/image."

- timestamp: 2026-09-21T19:25:00Z
  checked: "Ran HEAD's _normalize_trade_item + _validate_trade_item under backend/.venv against side values 'SELL', 'sell', ' SELL ', 'Sell', 'BUY', 'SELL '"
  found: "Every value normalizes to 'sell'/'buy' and validate returns None (accepted). LlmTradeItem(side='SELL', quantity=-2) normalizes to ('AAPL', 'sell', 2.0)."
  implication: "HEAD accepts uppercase side. The reported rejection is impossible against current source — empirically, not just by reading."

- timestamp: 2026-09-21T19:26:00Z
  checked: "sqlite3 db/finally.db — chat_messages rows with non-empty actions, and full history with timestamps"
  found: |
    2026-09-21T16:11:20Z assistant | trades=[{ticker 'AAPL', side 'SELL', quantity 2.0, price None, outcome 'error', reason \"Invalid side: 'SELL'\"}]
    2026-09-21T16:11:43Z assistant | content = raw JSON blob {"action": "BUY", "symbol": "GOOGL", ...}  <- this is G-03-7 (UAT test 2)
    2026-09-21T11:31:28Z assistant | trades=[{side 'sell', quantity -2.0, reason 'Invalid quantity: -2.0'}]  <- round-2 UAT
  implication: "Both round-3 failures came from the same server within 23 seconds. The annotation stores the RAW uppercase side, which only pre-a06d51d code does (HEAD stores the normalized value). G-03-7 and G-03-8 are one event, not two bugs."

- timestamp: 2026-09-21T19:27:00Z
  checked: "Executed the pre-b2187b2 `_validate_trade_item` (extracted via `git show b2187b2^:backend/app/llm/actions.py`) against LlmTradeItem(side='SELL')"
  found: "Returns the literal string \"Invalid side: 'SELL'\" — byte-identical to the user's badge. 'Sell' -> \"Invalid side: 'Sell'\", 'sell' -> None."
  implication: "The running code was pre-b2187b2 (before 2026-09-21 14:08:47 +0300). The intermediate version (b2187b2..a06d51d) cannot produce it either, since its check lower-cases before comparing — so the runtime is older than BOTH fixes."

- timestamp: 2026-09-21T19:28:00Z
  checked: "Win32_Process for python/node/uvicorn; netstat -ano for :8000; curl /api/health"
  found: |
    PID 29720 uvicorn.exe "app.main:app --port 8000"   CreationDate 2026-09-20 20:49:50 +0300   (NO --reload flag)
    PID 11468 uv python.exe (same start time) == LISTENING owner of 127.0.0.1:8000, /api/health -> {"status":"ok"} (still alive now)
    PID 5056/28228 next dev (frontend)                 CreationDate 2026-09-20 20:18:xx
  implication: "SMOKING GUN. The backend process serving the UAT has been running since 2026-09-20 20:49:50 with no --reload, so it holds module bytecode imported ~45 hours before round-3 UAT. Its start time is 45s before the first real-LLM chat row (2026-09-20T17:50:35Z), so it has served every chat turn since."

- timestamp: 2026-09-21T19:29:00Z
  checked: "git log --since='2026-09-20 20:49:50' -- backend/"
  found: "8 backend commits landed after the process started: db1575d, 4d0999c (03-06 G-03-3 fence/streaming fix, 09-20 22:10), b2187b2 (WR-02 case normalization, 09-21 14:08), ed74e72, 951fd95, a06d51d (03-08 normalize-once + sign recovery, 09-21 18:39), f1178e0, 8f60cb7."
  implication: "Every backend fix from 03-06 onward is absent from the running process. 4d0999c's absence explains UAT test 2 (raw JSON as message — HEAD's parse_llm_response can never assign raw model text to `message`); b2187b2's absence explains UAT test 3. One cause, two reported gaps."

- timestamp: 2026-09-21T19:30:00Z
  checked: "Why UAT test 1 (frontend G-03-4) passed while tests 2 and 3 failed; backend/.venv pytest tests/llm"
  found: "The frontend runs under `next dev`, which hot-reloads, so 03-07's frontend fix WAS live. The backend has no equivalent. All 57 tests in backend/tests/llm pass at HEAD, including test_execute_llm_actions_padded_side_executes (side=' BUY ')."
  implication: "Perfect differential: hot-reloaded layer verified correctly, non-reloaded layer reported stale behavior. Source and its regression tests are green — only the runtime was stale."

## Resolution

root_cause: |
  Stale backend runtime, not a code defect. The uvicorn process the human
  tested against (PID 11468, `uvicorn app.main:app --port 8000`, started
  2026-09-20 20:49:50 +0300 with NO --reload flag, still listening on :8000)
  has held module bytecode imported ~45 hours before round-3 UAT. It predates
  b2187b2 (2026-09-21 14:08:47), whose pre-fix line
  `if item.side not in ("buy","sell"): return f"Invalid side: {item.side!r}"`
  reproduces the badge string byte-for-byte for side='SELL'; it also predates
  a06d51d (03-08). At HEAD, `_normalize_trade_item()` lower-cases `side`
  exactly as it lower-cases watchlist `action`, and side='SELL' is accepted
  (verified by execution, and by 57 passing tests). Two conditions had to hold
  together (AND-gate): the dev server runs without --reload, AND the
  verification workflow has no "restart the backend / confirm the running
  build" step between landing a backend fix and human UAT. The same stale
  process is also the sole cause of G-03-7 (UAT test 2's raw-JSON message),
  which 4d0999c fixed 80 minutes after the process started — both gaps were
  recorded 23 seconds apart from the same process.
fix: "Not applied (goal: find_root_cause_only). Direction: (1) restart the backend and re-run UAT tests 2 and 3; (2) run the dev server with --reload, or add an explicit restart step to the verification workflow; (3) consider surfacing the running build's git SHA via /api/health so a stale runtime is self-evident during UAT."
verification: "Pending — re-run UAT tests 2 and 3 against a restarted server."
files_changed: []
