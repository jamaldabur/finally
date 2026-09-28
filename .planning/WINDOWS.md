---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-09-28T19:14:16.909Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 06 | deviation | test/specs/06-sse-reconnect.spec.ts | 23 | Live-drop SSE reconnection test (context.setOffline) cannot observe a status change away from Connected in this Chromium/CDP environment - the emulation blocks new connections but doesn't interrupt an already-open, continuously-streaming SSE connection; verified deterministic over 30s isolated diagnostic and across 2 full E2E runs. The unreachable-at-load reconnect test (page.route abort) independently proves the same retry/reconnect capability and passes reliably. | open |  | 2026-09-28T19:14:16.909Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "06",
    "file": "test/specs/06-sse-reconnect.spec.ts",
    "line": 23,
    "description": "Live-drop SSE reconnection test (context.setOffline) cannot observe a status change away from Connected in this Chromium/CDP environment - the emulation blocks new connections but doesn't interrupt an already-open, continuously-streaming SSE connection; verified deterministic over 30s isolated diagnostic and across 2 full E2E runs. The unreachable-at-load reconnect test (page.route abort) independently proves the same retry/reconnect capability and passes reliably.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-28T19:14:16.909Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
