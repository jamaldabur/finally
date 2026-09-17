---
phase: "02"
slug: "core-trading-ui"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-17"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser → FastAPI (`/api/*`) | User-controlled ticker and quantity strings cross into the backend here; also cross-origin during local dev (`:3000` → `:8000`) | Trade requests, ticker symbols, quantities |
| FastAPI → Browser (`detail`, tick payloads, portfolio/watchlist responses) | Backend-generated strings (rejection reasons, ticker symbols) and monetary values cross back and are rendered into the DOM | Rejection text, prices, cash/position figures |
| Browser internal (price store → header total) | The one place in the phase where a displayed monetary figure is computed client-side rather than read from the API | Live total value (display-only recompute) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-SC | Tampering | `npm install` of the nine frontend packages | high | mitigate | Blocking-human package-legitimacy checkpoint (Plan 02-01 Task 0); user reviewed and approved all six `[SUS]`-flagged packages on npmjs.com before install; versions pinned exactly, `package-lock.json` committed | closed |
| T-02-01 | Elevation of Privilege | `backend/app/main.py` `CORSMiddleware` | medium | mitigate | `allow_origins` is the single literal `http://localhost:3000`, never a wildcard; credentials not enabled; confirmed via code review as the only change in that file this phase | closed |
| T-02-02 | Tampering | `TradeBar.tsx` rendering the 400 `detail` and the user's ticker text | low | mitigate | Rendered as JSX text children (React-escaped); zero `dangerouslySetInnerHTML` repo-wide, confirmed by code review and phase verification | closed |
| T-02-03 | Tampering | `POST /api/portfolio/trade` request body | low | mitigate | Body is exactly `{ticker, side, quantity}` per `TradeRequest`; no client-derived monetary value ever placed in a request; confirmed by phase verification | closed |
| T-02-04 | Information Disclosure | `frontend/.env.example` / `.env.development.local` | low | accept | `NEXT_PUBLIC_API_BASE_URL` is a public origin, not a secret; `NEXT_PUBLIC_*` values are inlined into the client bundle by design | closed |
| T-02-05 | Tampering | `WatchlistRow.tsx` rendering backend-supplied ticker symbols | low | mitigate | Rendered as JSX text children; repository-wide zero-`dangerouslySetInnerHTML` check confirmed | closed |
| T-02-06 | Denial of Service | `usePriceStore()` consumers | low | mitigate | Single shared `EventSource`; `new EventSource` confirmed to appear only in `frontend/lib/priceStore.tsx` — N watchlist/position rows can never become N backend connections | closed |
| T-02-07 | Tampering | `JSON.parse` of the SSE `data` payload in the shared store | low | accept | Payload originates from the same-origin FastAPI backend in production and an explicitly allow-listed local origin in dev; not user-supplied, no `eval`-class parsing | closed |
| T-02-08 | Spoofing | Simulated prices presented as market data | low | mitigate | Watchlist change-percent column labelled session-relative; header's unconditional "Simulated" marker (Plan 02-03) confirmed present, both verified live in UAT test 8 | closed |
| T-02-09 | Tampering | `Header.tsx` `useLiveTotalValue` | medium | mitigate | Client-recomputed total is display-only, never placed in a request body; scope fixed to `cash_balance + Σ qty × price`, confirmed by phase verification | closed |
| T-02-10 | Spoofing | Header presenting a dollar balance beside live-looking prices | medium | mitigate | Visible "Simulated" marker beside the portfolio total, confirmed present and human-verified (UAT test 7/8) | closed |
| T-02-11 | Repudiation | Connection dot showing green while the stream is dead | low | mitigate | Status derived from real `onopen`/`onerror` transitions plus a `readyState !== EventSource.OPEN` grace-timer check; live stop/restart lifecycle human-verified (UAT test 7) | closed |
| T-02-12 | Tampering | `PositionsRow.tsx` rendering backend monetary strings and ticker symbols | low | mitigate | All rendered as JSX text children; zero `dangerouslySetInnerHTML` repo-wide | closed |
| T-02-13 | Denial of Service | 5-second `GET /api/portfolio` interval in `portfolioStore.tsx` | low | accept | Single-user, same-host, in-process SQLite read; negligible against the 0.5s SSE broadcast already sustained; in-flight refresh guarded against double-fire | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-04 | `.env.example`'s `NEXT_PUBLIC_API_BASE_URL` is a public dev-server origin, not a secret; Next.js inlines all `NEXT_PUBLIC_*` values into the client bundle by design | Plan 02-01 threat model | 2026-09-17 |
| AR-02-02 | T-02-07 | SSE payload is same-origin (prod) or explicitly allow-listed (dev), never user-supplied; `JSON.parse` with no `eval`-class parsing | Plan 02-02 threat model | 2026-09-17 |
| AR-02-03 | T-02-13 | Single-user, same-host, in-process SQLite read once every 5s; negligible relative to the 0.5s SSE broadcast the same backend already sustains | Plan 02-03 threat model | 2026-09-17 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-17 | 14 | 14 | 0 | gsd-secure-phase (ASVS L1, plan-time register, ORCHESTRATOR classification against code-review + phase-verification + live UAT evidence — auditor spawn short-circuited per ASVS L1 rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-17
