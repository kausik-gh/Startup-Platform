from fastapi.testclient import TestClient
from platform_api.main import app
from typing import Any


def test_liveness_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "Liveness check passed"}


def test_readiness_check_unconfigured(monkeypatch: Any) -> None:
    # Ensure DATABASE_URL is not set
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {
            "status": "error",
            "database": "not_configured",
            "message": "Database is not configured",
        }
