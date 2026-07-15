from fastapi.testclient import TestClient

from lineageguard.api import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_event_endpoint() -> None:
    response = TestClient(app).post(
        "/api/v1/events",
        json={
            "event_id": "api-test",
            "asset_urn": (
                "urn:li:dataset:(urn:li:dataPlatform:duckdb,main.stg_customers,PROD)"
            ),
            "change_type": "column_renamed",
            "previous_field": "customer_age",
            "field": "age_years",
        },
    )
    assert response.status_code == 200
    assert response.json()["report"]["severity"] == "critical"
