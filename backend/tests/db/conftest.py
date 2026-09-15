import pytest

from app.db import connection


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Every db test gets its own throwaway SQLite file — never touch the
    real db/finally.db. Patching connection.DB_PATH (rather than each
    module's own copy) is enough: every app/db/* module calls
    connection.connect(), which reads DB_PATH from this module at call time."""
    monkeypatch.setattr(connection, "DB_PATH", tmp_path / "finally.db")
