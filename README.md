# FinAlly — AI Trading Workstation

A capstone project for an agentic AI coding course: a Bloomberg-style trading terminal with live simulated market data, a virtual $10,000 portfolio, and an AI copilot that can analyze your positions and execute trades on your behalf. Built entirely by orchestrated coding agents.

Full spec: [`planning/PLAN.md`](planning/PLAN.md)

## Stack

- **Frontend**: Next.js (TypeScript), static export
- **Backend**: FastAPI (Python, managed with `uv`)
- **Database**: SQLite, lazily initialized on first run
- **Real-time data**: Server-Sent Events (`/api/stream/prices`)
- **AI**: LiteLLM → OpenRouter (`openrouter/openrouter/free`), structured outputs for trade execution
- **Deployment**: single Docker container, one port (8000)

## Status

**v1.0 shipped.** The full agentic trading loop works end-to-end — watch live prices, place trades (manually or via the AI chat copilot), see the result reflected across the watchlist, positions table, heatmap, and P&L chart, all served from one Docker container.

That said, this is a student/capstone project built by orchestrated AI agents, and it has **not been used in production or by real users** — it's demo-scale software, not hardened. It almost certainly still has bugs, rough edges, and untested combinations of inputs. A few known, non-blocking issues are tracked in `.planning/PROJECT.md`'s "Next Milestone Goals" section (e.g. chat can break under a non-localhost HTTP origin due to a `crypto.randomUUID()` secure-context requirement). If something looks broken, it probably is — please open an issue rather than assume it's you.

## Running

```bash
cp .env.example .env   # add your OPENROUTER_API_KEY
./scripts/start_mac.sh # or scripts/start_windows.ps1 on Windows
```

Opens at `http://localhost:8000` — no login required.

## Project Layout

```
frontend/    Next.js app (static export, served by the backend)
backend/     FastAPI app, owns DB schema, API routes, SSE, LLM integration
planning/    Shared spec and docs agents build against
test/        Playwright E2E tests
scripts/     Docker start/stop scripts
db/          SQLite volume mount (runtime data, gitignored)
```

## License

MIT — see [LICENSE](LICENSE).
