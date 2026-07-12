from fastapi.testclient import TestClient
from platform_api.main import app

client = TestClient(app)


def test_liveness_check() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Liveness check passed"}


def test_readiness_check() -> None:
    response = client.get("/health/ready")
    # During bootstrap, it should return 200 since DATABASE_URL is not set by default
    assert response.status_code in (200, 503)
    assert "status" in response.json()
