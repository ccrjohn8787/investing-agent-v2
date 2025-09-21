"""Offline smoke test for the hybrid investment agent pipeline."""
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hybrid_agent.calculate import CalculationService
from hybrid_agent.agents import AnalystAgent, VerifierAgent
from hybrid_agent.models import CompanyQuarter, Document
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever


def main() -> None:
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

    primary_doc = Document(
        id="DOC-1",
        ticker="AAPL",
        doc_type="10-K",
        title="Apple Inc. 2024 10-K",
        date="2024-02-01",
        url="https://example.com/aapl-10k",
        pit_hash="hash",
    )

    index = InMemoryDocumentIndex()
    index.add(primary_doc, "Apple maintains strong pricing power across premium product lines.")
    retriever = Retriever(index)

    calc_service = CalculationService()
    analyst = AnalystAgent(calculation_service=calc_service, retriever=retriever)
    analyst_result = analyst.analyze("AAPL", "2024-06-30", quarter, [primary_doc])

    verifier = VerifierAgent(calc_service)
    qa_result = verifier.verify(
        quarter,
        {
            "provenance": [
                {
                    "metric": "FCF",
                    "value": 230.0,
                    "document_id": "DOC-1",
                    "doc_type": "10-K",
                    "url": "https://example.com/aapl-10k",
                }
            ],
            "stage_0": [
                {"gate": "Circle of Competence", "result": "Pass"},
                {"gate": "Fraud/Controls", "result": "Pass"},
                {"gate": "Imminent Solvency", "result": "Pass"},
                {"gate": "Valuation", "result": "Pass"},
                {"gate": "Final Decision Gate", "result": "Pass"},
            ],
        },
    )

    print(analyst_result["output_0"])
    print("Stage-0 rows:", len(analyst_result["stage_0"]))
    print("Provenance entries:", analyst_result["provenance"])
    print("QA Result:", qa_result.status, qa_result.reasons)


if __name__ == "__main__":
    main()
