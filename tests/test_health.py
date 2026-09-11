from fastapi.testclient import TestClient

from agent_search.app.main import app


def test_health_reports_service_metadata() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "development",
        "version": "0.1.0",
    }
