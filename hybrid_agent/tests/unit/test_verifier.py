from datetime import date

from hybrid_agent.agents.verifier import VerifierAgent
from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import CompanyQuarter, Document, Metric


def _quarter(period: str, revenue: float = 500_000, fcf: float = 40_000, ebit: float = 50_000):
    return CompanyQuarter(
        ticker="TEST",
        period=period,
        income_stmt={"Revenue": revenue, "EBIT": ebit},
        balance_sheet={
            "TotalDebt": revenue * 0.1,
            "Cash": revenue * 0.05,
            "AccountsReceivable": revenue * 0.1,
        },
        cash_flow={"FCF": fcf, "CFO": fcf + 5_000},
        segments={"Consolidated": {"Revenue": revenue}},
        metadata={
            "ttm": {
                "Revenue": revenue * 4,
                "FCF": fcf * 4,
                "EBIT": ebit * 4,
            }
        },
    )


def _provenance_entry(doc: Document, quote: str):
    return {
        "quote": quote,
        "source_doc_id": doc.id,
        "page_or_section": "filing table",
        "url": str(doc.url),
        "date": doc.date,
    }


def test_verifier_passes_valid_dossier(tmp_path):
    store = DocumentStore(tmp_path)
    doc = Document(
        id="TEST-DOC-1",
        ticker="TEST",
        doc_type="10-K",
        title="Test",
        date="2024-02-01",
        url="https://example.com/10k",
        pit_hash="hash",
    )
    store.save(doc, b"Revenue grew 20 percent year over year.")

    quarter = _quarter("2024Q2")
    quarter.metadata["provenance"] = {
        "Revenue": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "FCF": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "EBIT": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "DSO": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "DIH": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "DPO": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "CCC": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "Accruals Ratio": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "Net Debt / EBITDA": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "ROIC": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
        "NRR": _provenance_entry(doc, "Revenue grew 20 percent year over year"),
    }

    history = [_quarter(f"2023Q{i}") for i in range(1, 9)]

    calc_service = CalculationService()
    verifier = VerifierAgent(calc_service, document_store=store, sample_size=3)

    calc_result = calc_service.calculate(quarter, history)
    metrics_payload = [
        {
            "metric": metric.name,
            "value": metric.value,
            "source_doc_id": metric.source_doc_id,
        }
        for metric in calc_result.metrics
        if isinstance(metric.value, (int, float))
    ]

    stage0 = {
        "hard": [
            {"gate": "Circle of Competence", "result": "Pass"},
            {"gate": "Fraud/Controls", "result": "Pass"},
            {"gate": "Imminent Solvency", "result": "Pass"},
            {"gate": "Valuation", "result": "Pass"},
            {"gate": "Final Decision Gate", "result": "Pass"},
        ],
    }

    dossier = {
        "output_0": "Mature path. Hard gates: PASS.",
        "stage_0": stage0,
        "metrics": metrics_payload,
        "path_reasons": [],
        "provenance_issues": [],
    }

    result = verifier.verify(quarter, dossier, history)
    assert result.status == "PASS"


def test_verifier_blocks_non_primary_source(tmp_path):
    store = DocumentStore(tmp_path)
    doc = Document(
        id="TEST-DOC-2",
        ticker="TEST",
        doc_type="10-K",
        title="Test",
        date="2024-02-01",
        url="https://example.com/10k",
        pit_hash="hash2",
    )
    store.save(doc, b"Revenue grew 20 percent year over year.")

    quarter = _quarter("2024Q2")
    quarter.metadata["provenance"] = {
        "Revenue": _provenance_entry(doc, "Nonexistent snippet"),
    }

    history = [_quarter(f"2023Q{i}") for i in range(1, 9)]

    calc_service = CalculationService()
    verifier = VerifierAgent(calc_service, document_store=store)

    dossier = {
        "output_0": "Emergent path. Hard gates: PASS.",
        "stage_0": {"hard": [{"gate": "Circle of Competence", "result": "Pass"}]},
        "metrics": [
            {
                "metric": "Revenue",
                "value": 500_000.0,
                "source_doc_id": doc.id,
            }
        ],
        "path_reasons": ["TTM FCF <= 0"],
        "provenance_issues": [],
    }

    result = verifier.verify(quarter, dossier, history)
    assert result.status == "BLOCKER"
    assert any("quote not found" in reason.lower() for reason in result.reasons)
