from fastapi.testclient import TestClient

from agent_search.app.main import app


def test_search_returns_ranked_grounded_evidence() -> None:
    response = TestClient(app).post(
        "/v1/search",
        json={"query": "Busan cargo terminal weather", "filters": {"region": "busan"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["ranking_version"] == "lexical-bm25-v1"
    assert payload["degraded"] is False
    assert payload["results"]
    evidence = payload["results"][0]
    assert {
        "chunk_id",
        "file_id",
        "text",
        "character_start",
        "source_title",
        "source_url",
    } <= evidence.keys()


def test_search_rejects_invalid_filter_ranges() -> None:
    response = TestClient(app).post(
        "/v1/search",
        json={
            "query": "cargo",
            "filters": {"published_from": "2026-02-01", "published_to": "2026-01-01"},
        },
    )

    assert response.status_code == 422
    assert "published_to must be on or after published_from" in response.text


def test_search_exposes_prometheus_counters() -> None:
    client = TestClient(app)
    client.post("/v1/search", json={"query": "cargo"})

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "agent_search_requests_total" in response.text
