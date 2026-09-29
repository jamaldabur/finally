import pytest

from app.db import watchlist as watchlist_module


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Every test gets its own throwaway SQLite file — never touch the real
    db/finally.db during tests. Because every new app/db/*.py module in this
    phase imports `_connect` from `app.db.watchlist` by function reference
    (Python late-binds the module global at call time), patching this one
    attribute isolates all six tables at once (see 01-RESEARCH.md Pitfall 1)."""
    monkeypatch.setattr(watchlist_module, "DB_PATH", tmp_path / "finally.db")
