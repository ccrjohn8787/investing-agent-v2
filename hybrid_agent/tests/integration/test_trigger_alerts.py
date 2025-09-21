from fastapi.testclient import TestClient

from hybrid_agent.api import app


def test_trigger_alerts_via_api():
    client = TestClient(app)

    response = client.post(
        "/triggers",
        json={
            "ticker": "AAPL",
            "name": "Gross Margin",
            "threshold": 0.4,
            "comparison": "gte",
            "deadline": "2024-09-30",
        },
    )
    assert response.status_code == 200

    response = client.post(
        "/triggers/evaluate",
        json={
            "ticker": "AAPL",
            "metrics": {"Gross Margin": 0.35},
            "today": "2024-09-30",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["alerts"]
    assert payload["alerts"][0]["trigger"] == "Gross Margin"
