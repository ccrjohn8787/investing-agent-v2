from hybrid_agent.agents.verifier import VerifierAgent
from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.models import CompanyQuarter


def test_verifier_blocks_missing_hard_gate():
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

    dossier = {
        "provenance": [
            {
                "metric": "FCF",
                "value": 230.0,
                "document_id": "DOC-1",
                "doc_type": "10-K",
                "url": "https://example.com",
            }
        ],
        "stage_0": [
            {"gate": "Circle of Competence", "result": "Pass"},
            {"gate": "Fraud/Controls", "result": "Pass"},
            {"gate": "Imminent Solvency", "result": "Pass"},
            # Missing Valuation gate intentionally
            {"gate": "Final Decision Gate", "result": "Pass"},
        ],
    }

    verifier = VerifierAgent(CalculationService())
    result = verifier.verify(quarter=quarter, dossier=dossier)

    assert result.status == "BLOCKER"
    assert "valuation" in " ".join(result.reasons).lower()
