# FinAlly — AI Trading Workstation

A capstone project for an agentic AI coding course: a Bloomberg-style trading terminal with live simulated market data, a virtual $10,000 portfolio, and an AI copilot that can analyze your positions and execute trades on your behalf. Built entirely by orchestrated coding agents.

Full spec: [`planning/PLAN.md`](planning/PLAN.md)

## Stack

- **Frontend**: Next.js (TypeScript), static export
- **Backend**: FastAPI (Python, managed with `uv`)
- **Database**: SQLite, lazily initialized on first run
- **Real-time data**: Server-Sent Events (`/api/stream/prices`)
- **AI**: LiteLLM → OpenRouter (`openrouter/openai/gpt-oss-120b`), structured outputs for trade execution
- **Deployment**: single Docker container, one port (8000)

## Status

Scaffolding and planning stage — `frontend/` and `backend/` are not yet implemented. See `planning/` for the design docs agents are building against.

## Running (once built)

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
