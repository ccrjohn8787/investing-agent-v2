from fastapi.testclient import TestClient

from hybrid_agent.api import app
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import Document
from hybrid_agent.reports.store import ReportStore


def _store_document(store: DocumentStore, doc_id: str, doc_type: str, content: str) -> None:
    document = Document(
        id=doc_id,
        ticker=doc_id.split('-')[0],
        doc_type=doc_type,
        title=f"{doc_id} source",
        date="2024-12-31",
        url="https://example.com",
        pit_hash="hash",
    )
    store.save(document, content.encode("utf-8"))


def test_full_pipeline_passes_qa(tmp_path):
    client = TestClient(app)
    store = DocumentStore(tmp_path)
    app.state.document_store = store
    app.state.report_store = ReportStore(tmp_path / "reports.json")

    _store_document(
        store,
        "UBER-TESTDOC",
        "10-K",
        (
            "Revenue for Q4 2024 totaled 37,000,000,000 USD.\n"
            "Net income for the quarter was 1,400,000,000 USD.\n"
            "EBIT reported at 2,100,000,000 USD.\n"
            "Operating cash flow reached 5,800,000,000 USD.\n"
            "Capital expenditures were (700,000,000) USD.\n"
            "Total assets closed at 50,000,000,000 USD.\n"
            "Total equity ended at 15,000,000,000 USD."
        ),
    )

    _store_document(
        store,
        "MACRO-UBER-VALUATION-2024",
        "Macro",
        (
            "Risk-free rate (UST10Y) 31-Dec-2024: 3.00%. Damodaran implied ERP Jan-2025: 4.00%."
            " Levered beta (2Y weekly vs SPX): 0.90. Pretax cost of debt (interest / avg debt): 4.00%."
            " Cash tax rate assumption: 21%. Base hurdle: 15%. Hurdle policy adjustment: -150 bps for mature marketplace."
            " Equity adjustment applied: -25 bps for scale network. Inflation anchor: 2.2%. Real GDP anchor: 1.5%."
            " Base FCF (USD millions): 5,051; 5,556; 6,112; 6,723; 7,395."
        ),
    )

    quarter = {
        "ticker": "UBER",
        "period": "2024Q4",
        "income_stmt": {
            "Revenue": 37_000_000_000.0,
            "NetIncome": 1_400_000_000.0,
            "EBIT": 2_100_000_000.0,
        },
        "balance_sheet": {
            "TotalAssets": 50_000_000_000.0,
            "TotalEquity": 15_000_000_000.0,
            "TotalDebt": 11_000_000_000.0,
            "Cash": 12_000_000_000.0,
        },
        "cash_flow": {
            "CFO": 5_800_000_000.0,
            "CapEx": -700_000_000.0,
            "FCF": 5_100_000_000.0,
        },
        "segments": {
            "Mobility": {"Revenue": 21_000_000_000.0},
            "Delivery": {"Revenue": 14_000_000_000.0},
        },
        "metadata": {
            "provenance": {
                "Revenue": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "Revenue for Q4 2024 totaled 37,000,000,000 USD.",
                    "url": "https://example.com",
                },
                "NetIncome": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "Net income for the quarter was 1,400,000,000 USD.",
                    "url": "https://example.com",
                },
                "EBIT": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "EBIT reported at 2,100,000,000 USD.",
                    "url": "https://example.com",
                },
                "CFO": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "Operating cash flow reached 5,800,000,000 USD.",
                    "url": "https://example.com",
                },
                "CapEx": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "Capital expenditures were (700,000,000) USD.",
                    "url": "https://example.com",
                },
                "TotalAssets": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "Total assets closed at 50,000,000,000 USD.",
                    "url": "https://example.com",
                },
                "TotalEquity": {
                    "source_doc_id": "UBER-TESTDOC",
                    "page_or_section": "p1",
                    "quote": "Total equity ended at 15,000,000,000 USD.",
                    "url": "https://example.com",
                },
            },
                "valuation": {
                    "risk_free_rate": 0.03,
                    "equity_risk_premium": 0.04,
                    "beta": 0.9,
                    "cost_of_debt": 0.04,
                    "tax_rate": 0.21,
                    "market_equity_value": 144_900_000_000.0,
                    "market_debt_value": 6_000_000_000.0,
                    "equity_adjustment_bps": -25.0,
                    "share_price": 69.0,
                    "shares_diluted": 2_100_000_000.0,
                    "net_debt": -1_000_000_000.0,
                    "terminal_inputs": {"inflation": 0.022, "real_gdp": 0.015},
                    "hurdle": {
                        "base": 0.15,
                        "adjustment_bps": -150.0,
                        "rationale": "Scale marketplace merits 150 bps reduction.",
                    },
                    "fcf_paths": {
                        "Base": [5_051_000_000.0, 5_556_000_000.0, 6_112_000_000.0, 6_723_000_000.0, 7_395_000_000.0],
                        "Bull": [5_051_000_000.0, 5_809_000_000.0, 6_680_000_000.0, 7_682_000_000.0, 8_834_000_000.0],
                        "Bear": [5_051_000_000.0, 5_303_000_000.0, 5_568_000_000.0, 5_846_000_000.0, 6_138_000_000.0],
                    },
                    "notes": "Deterministic valuation inputs for integration testing.",
                    "provenance": {
                        "WACC-point": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Risk-free rate (UST10Y) 31-Dec-2024: 3.00%. Damodaran implied ERP Jan-2025: 4.00%.",
                            "url": "https://example.com",
                        },
                        "WACC-lower": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Risk-free rate (UST10Y) 31-Dec-2024: 3.00%. Damodaran implied ERP Jan-2025: 4.00%.",
                            "url": "https://example.com",
                        },
                        "WACC-upper": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Risk-free rate (UST10Y) 31-Dec-2024: 3.00%. Damodaran implied ERP Jan-2025: 4.00%.",
                            "url": "https://example.com",
                        },
                        "Cost of Equity": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Levered beta (2Y weekly vs SPX): 0.90.",
                            "url": "https://example.com",
                        },
                        "Cost of Debt (after tax)": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Pretax cost of debt (interest / avg debt): 4.00%. Cash tax rate assumption: 21%.",
                            "url": "https://example.com",
                        },
                        "Terminal Growth": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Inflation anchor: 2.2%. Real GDP anchor: 1.5%.",
                            "url": "https://example.com",
                        },
                        "Hurdle IRR": {
                            "source_doc_id": "MACRO-UBER-VALUATION-2024",
                            "page_or_section": "Valuation Inputs",
                            "quote": "Base hurdle: 15%. Hurdle policy adjustment: -150 bps for mature marketplace.",
                            "url": "https://example.com",
                        },
                    },
                },
        },
    }

    history = [
        {
            "ticker": "UBER",
            "period": f"2023Q{i}",
            "income_stmt": {
                "Revenue": 30_000_000_000.0,
                "NetIncome": 1_000_000_000.0,
                "EBIT": 1_600_000_000.0,
            },
            "balance_sheet": {
                "TotalAssets": 48_000_000_000.0,
                "TotalEquity": 14_000_000_000.0,
                "TotalDebt": 10_000_000_000.0,
                "Cash": 6_500_000_000.0,
            },
            "cash_flow": {
                "CFO": 5_000_000_000.0,
                "CapEx": -600_000_000.0,
                "FCF": 4_400_000_000.0,
            },
            "segments": {
                "Mobility": {"Revenue": 18_000_000_000.0},
                "Delivery": {"Revenue": 12_000_000_000.0},
            },
            "metadata": {
                "provenance": {
                    "Revenue": {
                        "source_doc_id": "UBER-TESTDOC",
                        "page_or_section": "p1",
                        "quote": "Revenue for Q4 2024 totaled 37,000,000,000 USD.",
                        "url": "https://example.com",
                    }
                }
            },
        }
        for i in range(1, 9)
    ]

    analyze_payload = {
        "ticker": "UBER",
        "today": "2025-01-31",
        "quarter": quarter,
        "history": history,
        "documents": [
            {
                "id": "UBER-TESTDOC",
                "ticker": "UBER",
                "doc_type": "10-K",
                    "title": "Uber 2024 10-K",
                    "date": "2024-12-31",
                    "url": "https://example.com",
                    "pit_hash": "hash",
                    "content": "Uber demonstrates pricing power with improving take rates.",
                }
            ],
        }

    analyze_response = client.post("/analyze", json=analyze_payload)
    assert analyze_response.status_code == 200
    analyst_payload = analyze_response.json()
    hard_gates = analyst_payload["stage_0"].get("hard", [])
    assert any(row["gate"] == "Valuation" for row in hard_gates)
    assert analyst_payload["reverse_dcf"]["wacc"]["point"]
    assert "delta" in analyst_payload
    assert "trigger_alerts" in analyst_payload

    verify_payload = {
        "quarter": quarter,
        "dossier": analyst_payload,
    }
    verify_response = client.post("/verify", json=verify_payload)
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "PASS"

    # cleanup to avoid cross-test state leak
    if hasattr(app.state, "document_store"):
        del app.state.document_store
    if hasattr(app.state, "report_store"):
        del app.state.report_store
