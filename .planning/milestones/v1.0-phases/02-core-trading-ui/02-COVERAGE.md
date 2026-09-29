# API Coverage — Phase 02 Core Trading UI

No external API integration: This phase is a frontend UI consuming this project's own FastAPI
backend (`GET /api/portfolio`, `GET /api/watchlist`, `POST /api/portfolio/trade`,
SSE `/api/stream/prices`) — a first-party, same-repo REST surface documented in `planning/PLAN.md`
§8, not a third-party/external API or SDK. The `api-coverage.verify-pre` detector's "surface api"
signal fired on the phase's own plan files describing this internal contract (e.g.
`frontend/lib/api.ts`'s `fetchPortfolio`/`postTrade`/`fetchWatchlist` calling the backend built in
Phase 1), which is exactly the over-fire case this declaration exists to override. No LLM, AI
provider, or third-party service is called anywhere in this phase — that begins in Phase 3
(OpenRouter/LiteLLM chat integration), where the real coverage gate applies.
