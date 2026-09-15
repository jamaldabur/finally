from app.db import connection


def test_connect_creates_parent_directory_and_opens(tmp_path):
    nested = tmp_path / "nested" / "dir" / "finally.db"
    connection.DB_PATH = nested  # not using monkeypatch: local, throwaway path

    with connection.connect() as conn:
        conn.execute("CREATE TABLE t (id INTEGER)")

    assert nested.exists()


def test_connect_enables_wal_journal_mode(tmp_path):
    connection.DB_PATH = tmp_path / "finally.db"

    with connection.connect() as conn:
        (mode,) = conn.execute("PRAGMA journal_mode").fetchone()

    assert mode.lower() == "wal"


def test_connect_commits_on_clean_exit(tmp_path):
    connection.DB_PATH = tmp_path / "finally.db"

    with connection.connect() as conn:
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t (id) VALUES (1)")

    with connection.connect() as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM t").fetchone()
    assert count == 1


def test_connect_rolls_back_on_exception(tmp_path):
    connection.DB_PATH = tmp_path / "finally.db"

    with connection.connect() as conn:
        conn.execute("CREATE TABLE t (id INTEGER)")

    try:
        with connection.connect() as conn:
            conn.execute("INSERT INTO t (id) VALUES (1)")
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    with connection.connect() as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM t").fetchone()
    assert count == 0
