import json

from hybrid_agent.agents.analyst import AnalystAgent
from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.models import CompanyQuarter, Document
from hybrid_agent.rag.index import InMemoryDocumentIndex
from hybrid_agent.rag.retrieve import Retriever


class StubLLM:
    def __init__(self, response: dict):
        self._response = response

    def generate(self, prompt: str) -> str:
        return json.dumps(self._response)


def test_analyze_output_contains_required_sections():
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

    document = Document(
        id="DOC-1",
        ticker="AAPL",
        doc_type="10-K",
        title="Form 10-K",
        date="2024-02-01",
        url="https://example.com",
        pit_hash="hash",
    )

    index = InMemoryDocumentIndex()
    index.add(document, "Apple maintains strong pricing power across premium segments.")
    retriever = Retriever(index)
    calc_service = CalculationService()

    llm_response = {
        "output_0": "Mature path. Hard gates: PASS. Final Decision Gate: PASS. WACC=8% (7%-9%), g=3%, Hurdle IRR=12%.",
        "stage_0": [],
        "stage_1": "Company overview...",
        "provenance": [],
        "reverse_dcf": {},
        "final_gate": {},
    }

    agent = AnalystAgent(calculation_service=calc_service, retriever=retriever, llm=StubLLM(llm_response))
    result = agent.analyze(
        ticker="AAPL",
        today="2024-06-30",
        quarter=quarter,
        documents=[document],
    )

    assert "output_0" in result
    assert "stage_0" in result
    assert result["stage_0"] == []
    assert "provenance" in result
    assert any(item["document_id"] == "DOC-1" for item in result["provenance"])
