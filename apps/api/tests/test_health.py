from fastapi.testclient import TestClient

from app.main import app


def test_healthz():
    r = TestClient(app).get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_health_alias():
    """Alias for GFE environments where /healthz is intercepted before Cloud Run."""
    r = TestClient(app).get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
