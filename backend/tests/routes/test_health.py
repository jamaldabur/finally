from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok(monkeypatch, tmp_path):
    monkeypatch.setattr("app.db.connection.DB_PATH", tmp_path / "finally.db")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
