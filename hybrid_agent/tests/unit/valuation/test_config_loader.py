from pathlib import Path
import json

from hybrid_agent.models import CompanyQuarter
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.valuation.config_loader import ValuationConfigLoader


def test_apply_valuation_config_persists_documents(tmp_path):
    config_dir = tmp_path / "valuation"
    config_dir.mkdir(parents=True)
    config_payload = {
        "valuation": {
            "risk_free_rate": 0.04,
            "equity_risk_premium": 0.055,
            "beta": 1.1,
            "cost_of_debt": 0.05,
            "tax_rate": 0.21,
            "market_equity_value": 10_000_000_000.0,
            "market_debt_value": 2_000_000_000.0,
            "equity_adjustment_bps": 0.0,
            "share_price": 25.0,
            "shares_diluted": 400_000_000.0,
            "net_debt": 1_000_000_000.0,
            "terminal_inputs": {"inflation": 0.02, "real_gdp": 0.01},
            "hurdle": {"base": 0.15, "adjustment_bps": 0.0, "rationale": "Base policy."},
            "fcf_paths": {"Base": [500_000_000.0] * 5},
            "notes": "Sample config",
        },
        "provenance": {
            "WACC-point": {
                "source_doc_id": "MACRO-SAMPLE",
                "page_or_section": "Inputs",
                "quote": "Risk-free rate (UST10Y) sample value 4.0%.",
                "url": "https://example.com/macro",
            }
        },
        "documents": [
            {
                "id": "MACRO-SAMPLE",
                "ticker": "MACRO",
                "doc_type": "Macro",
                "title": "Sample Macro Doc",
                "date": "2024-12-31",
                "url": "https://example.com/macro",
                "content": "Risk-free rate (UST10Y) sample value 4.0%.",
            }
        ],
    }
    (config_dir / "TEST.json").write_text(json.dumps(config_payload), encoding="utf-8")

    quarter = CompanyQuarter(
        ticker="TEST",
        period="2024Q4",
        income_stmt={},
        balance_sheet={},
        cash_flow={},
        segments={},
    )

    store = DocumentStore(tmp_path / "docs")
    loader = ValuationConfigLoader(base_path=config_dir)
    config = loader.load("TEST")
    assert config is not None
    updated = loader.apply(quarter, config, store=store)

    assert "valuation" in updated.metadata
    assert updated.metadata["valuation"]["risk_free_rate"] == 0.04
    doc, content = store.load("MACRO-SAMPLE")
    assert doc.id == "MACRO-SAMPLE"
    assert "Risk-free rate" in content.decode("utf-8")
