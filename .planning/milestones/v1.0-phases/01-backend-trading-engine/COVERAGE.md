# Phase 1 — External API Coverage

No external API integration: extends existing internal SQLite persistence and FastAPI routes; no new external service is called.

**Scan basis:** Phase 1's plans touch only `backend/app/db/*`, `backend/app/portfolio/*`,
`backend/app/routes/*`, `backend/app/main.py`, and `backend/tests/*`. No new package is installed
(`backend/pyproject.toml` and `backend/uv.lock` are untouched), and no new network call is added —
the Massive REST integration in `backend/app/market/massive.py` already exists from the completed
market-data work and is not modified by this phase.
