import json

from fastapi.testclient import TestClient

from hybrid_agent.api import app
from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.models import CompanyQuarter
from hybrid_agent.parse.normalize import Normalizer


def test_calculate_endpoint_returns_metrics(tmp_path):
    quarter = CompanyQuarter(
        ticker="AAPL",
        period="2024Q2",
        income_stmt={"Revenue": 1000.0, "NetIncome": 220.0, "EBIT": 260.0},
        balance_sheet={
            "AccountsReceivable": 150.0,
            "Inventory": 120.0,
            "AccountsPayable": 80.0,
            "CurrentAssets": 700.0,
            "CurrentLiabilities": 400.0,
            "TotalAssets": 2000.0,
            "TotalDebt": 500.0,
            "Cash": 300.0,
            "TotalEquity": 1200.0,
        },
        cash_flow={"CFO": 350.0, "CapEx": -120.0, "FCF": 230.0},
        segments={"Hardware": {"Revenue": 600.0}, "Services": {"Revenue": 400.0}},
    )

    normalize = Normalizer()
    service = CalculationService(normalizer=normalize)
    app.state.calc_service = service

    client = TestClient(app)
    response = client.post(
        "/calculate",
        json=json.loads(quarter.json()),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert any(metric["name"] == "FCF" for metric in payload["metrics"])
    assert any(metric["value"] == "ABSTAIN" for metric in payload["metrics"] if metric["name"] == "NRR")

    del app.state.calc_service
