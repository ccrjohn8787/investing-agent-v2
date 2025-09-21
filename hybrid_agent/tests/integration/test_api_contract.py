from fastapi.testclient import TestClient

from hybrid_agent.api import app


def _quarter(period: str, revenue: float, cfo: float):
    return {
        "ticker": "AAPL",
        "period": period,
        "income_stmt": {"Revenue": revenue},
        "balance_sheet": {},
        "cash_flow": {"CFO": cfo},
        "segments": {},
    }


def test_delta_endpoint_returns_deltas():
    client = TestClient(app)

    response = client.post(
        "/delta",
        json={
            "current": _quarter("2024Q2", 1000.0, 400.0),
            "prior": _quarter("2024Q1", 950.0, 350.0),
            "year_ago": _quarter("2023Q2", 800.0, 300.0),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Revenue" in payload["deltas"]
    assert payload["deltas"]["Revenue"]["qoq"] == 50.0
