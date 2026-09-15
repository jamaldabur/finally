import pytest

from app.db import connection


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Every test gets its own throwaway SQLite file — never touch the real
    db/finally.db. Mirrors tests/db/conftest.py."""
    monkeypatch.setattr(connection, "DB_PATH", tmp_path / "finally.db")
