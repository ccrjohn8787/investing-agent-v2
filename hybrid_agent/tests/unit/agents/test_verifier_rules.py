from hybrid_agent.agents.verifier import VerifierAgent
from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.models import CompanyQuarter, Document


def _quarter():
    return CompanyQuarter(
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


def test_verifier_passes_valid_dossier():
    quarter = _quarter()
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
            {"gate": "Valuation", "result": "Pass"},
            {"gate": "Final Decision Gate", "result": "Pass"},
        ],
    }
    verifier = VerifierAgent(CalculationService())
    result = verifier.verify(quarter=quarter, dossier=dossier)

    assert result.status == "PASS"


def test_verifier_blocks_non_primary_source():
    quarter = _quarter()
    dossier = {
        "provenance": [
            {
                "metric": "Revenue",
                "value": 1000.0,
                "document_id": "BLOG-1",
                "doc_type": "Blog",
                "url": "https://blog.example.com",
            }
        ],
        "stage_0": [
            {"gate": "Circle of Competence", "result": "Pass"},
            {"gate": "Fraud/Controls", "result": "Pass"},
            {"gate": "Imminent Solvency", "result": "Pass"},
            {"gate": "Valuation", "result": "Pass"},
            {"gate": "Final Decision Gate", "result": "Pass"},
        ],
    }
    verifier = VerifierAgent(CalculationService())
    result = verifier.verify(quarter=quarter, dossier=dossier)

    assert result.status == "BLOCKER"
    assert "non-primary" in result.reasons[0].lower()
