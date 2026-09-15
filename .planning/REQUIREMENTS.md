# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-09-15
**Core Value:** A user can watch live prices, trade a simulated portfolio, and have an AI copilot execute trades on their behalf — the full agentic trading loop must work end-to-end.

## v1 Requirements

Requirements for the current milestone (the full remainder of `planning/PLAN.md` beyond the already-built market data layer). Each maps to roadmap phases.

### Database (DATA)

- [ ] **DATA-01**: System persists user profile (cash balance, default $10,000) in a `users_profile` SQLite table
- [ ] **DATA-02**: System persists positions (ticker, quantity, avg_cost) in a `positions` SQLite table
- [ ] **DATA-03**: System persists an append-only trade history in a `trades` SQLite table
- [ ] **DATA-04**: System records portfolio value snapshots every 30 seconds and immediately after each trade, in a `portfolio_snapshots` table
- [ ] **DATA-05**: System persists chat conversation history (role, content, actions) in a `chat_messages` table
- [ ] **DATA-06**: Watchlist add/remove operations are persisted (extends the existing read-only `watchlist` table with write paths)

### Portfolio & Trading (PORT)

- [ ] **PORT-01**: User can execute a market buy order — instant fill at current price, no fees, no confirmation dialog
- [ ] **PORT-02**: User can execute a market sell order — instant fill at current price, no fees, no confirmation dialog
- [ ] **PORT-03**: A buy order is rejected with a clear error if cash balance is insufficient
- [ ] **PORT-04**: A sell order is rejected with a clear error if the user doesn't own enough shares
- [ ] **PORT-05**: User can view current portfolio (positions, cash balance, total value, unrealized P&L) via `GET /api/portfolio`
- [ ] **PORT-06**: User can view portfolio value history over time via `GET /api/portfolio/history`

### Watchlist (WLST)

- [ ] **WLST-01**: User can add a ticker to the watchlist via `POST /api/watchlist`; unrecognized tickers are rejected with a 400
- [ ] **WLST-02**: User can remove a ticker from the watchlist via `DELETE /api/watchlist/{ticker}`
- [ ] **WLST-03**: User can view the current watchlist with latest prices via `GET /api/watchlist`

### AI Chat (CHAT)

- [ ] **CHAT-01**: User can send a chat message and receive a complete structured JSON response (message + actions) via `POST /api/chat`
- [ ] **CHAT-02**: LLM responses are requested and parsed as structured output (`message`, `trades[]`, `watchlist_changes[]`) via LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b`)
- [ ] **CHAT-03**: Trades/watchlist changes the LLM specifies auto-execute through the same validation path as manual trade-bar/watchlist actions — no confirmation dialog
- [ ] **CHAT-04**: Each LLM-requested action is annotated with an `executed`/`error` outcome and returned to the frontend separately from the chat message text
- [ ] **CHAT-05**: User's recent conversation history hydrates on page load via `GET /api/chat`
- [ ] **CHAT-06**: System supports `LLM_MOCK=true` for deterministic mock chat responses (dev/testing without an API key)

### Frontend (UI)

- [ ] **UI-01**: Watchlist panel shows live-updating prices via SSE, flashing green/red on price change
- [ ] **UI-02**: Each watchlist ticker shows a sparkline mini-chart accumulated from the SSE stream since page load
- [ ] **UI-03**: Clicking a ticker in the watchlist shows a larger detailed chart for it in the main chart area
- [ ] **UI-04**: Portfolio heatmap (treemap) sizes rectangles by position weight and colors/saturates by unrealized P&L%, capped at ±10%
- [ ] **UI-05**: P&L line chart shows total portfolio value over time, sourced from `portfolio_snapshots`
- [ ] **UI-06**: Positions table shows ticker, quantity, avg cost, current price, unrealized P&L, % change
- [ ] **UI-07**: Trade bar lets the user submit buy/sell market orders (ticker, quantity, buy button, sell button)
- [ ] **UI-08**: AI chat panel (collapsible) hydrates history on mount and shows inline trade/watchlist confirmation badges labeled success or error
- [ ] **UI-09**: Header shows live portfolio total value, a connection status indicator (green/yellow/red dot), and cash balance
- [ ] **UI-10**: UI follows the dark trading-terminal visual design (color scheme, price flash animation) specified in PLAN.md §2

### Deployment (DEPLOY)

- [ ] **DEPLOY-01**: App builds as a multi-stage Docker image (Node build stage → Python runtime stage), serving frontend + API on a single port (8000)
- [ ] **DEPLOY-02**: SQLite database persists via a Docker volume mount at `db/`
- [ ] **DEPLOY-03**: Idempotent start/stop scripts exist for macOS/Linux (bash) and Windows (PowerShell)
- [ ] **DEPLOY-04**: `.env.example` is committed, documenting `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`

### Testing (TEST)

- [ ] **TEST-01**: Backend unit tests cover trade execution logic, P&L calculations, and edge cases (insufficient cash/shares)
- [ ] **TEST-02**: Backend unit tests cover LLM structured-output parsing, including malformed responses
- [ ] **TEST-03**: Backend unit tests cover API route status codes and response shapes for portfolio/watchlist/chat endpoints
- [ ] **TEST-04**: Frontend unit tests cover price flash animation triggering, watchlist CRUD, portfolio display calculations, and chat rendering/loading state
- [ ] **TEST-05**: Playwright E2E suite (in `test/`, own `docker-compose.test.yml`, `LLM_MOCK=true`) covers fresh start, watchlist add/remove, buy, sell, visualization rendering, mocked chat trade execution, and SSE reconnection

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Deployment

- **DEPLOY2-01**: Terraform configuration for AWS App Runner (or similar) cloud deployment

### Platform

- **PLAT2-01**: Multi-user support with authentication (schema already reserves `user_id` for this)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user auth / login | Single hardcoded `user_id="default"` is sufficient for a self-contained demo; no auth = no multi-user complexity |
| Limit orders, partial fills, order book | Market orders only — keeps portfolio math and execution logic dramatically simpler |
| Trade confirmation dialogs | Deliberate zero-friction design; simulated money, zero real stakes, fluid demo experience |
| Postgres / external DB server | SQLite is sufficient for a single-user, self-contained, zero-config deployment |
| WebSockets | SSE (one-way push) is simpler and sufficient for the price-streaming use case |
| Cloud deployment (Terraform/App Runner) | Stretch goal per PLAN.md §11, not core to the v1 course capstone deliverable |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 0
- Unmapped: 34 ⚠️ (pending roadmap creation)

---
*Requirements defined: 2026-09-15*
*Last updated: 2026-09-15 after initial definition*
