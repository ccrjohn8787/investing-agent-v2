import json
from pathlib import Path

from hybrid_agent.parse.normalize import Normalizer
from hybrid_agent.parse.xbrl import XBRLParser


def test_parse_pipeline_produces_company_quarter(tmp_path):
    xbrl_payload = {
        "ticker": "AAPL",
        "period": "2024Q2",
        "income_statement": {"Revenue": 1000.0, "NetIncome": 250.0},
        "balance_sheet": {"TotalAssets": 5000.0, "TotalLiabilities": 2000.0},
        "cash_flow": {"CFO": 400.0, "CapEx": -120.0},
        "segments": {"Hardware": {"Revenue": 600.0}, "Services": {"Revenue": 400.0}},
    }
    xbrl_path = tmp_path / "aapl_2024q2.json"
    xbrl_path.write_text(json.dumps(xbrl_payload))

    parser = XBRLParser()
    quarter = parser.parse(xbrl_path)

    normalized = Normalizer().normalize_quarter(quarter)

    assert normalized.period == "2024Q2"
    assert normalized.income_stmt["Revenue"] == 1000.0
    assert normalized.segments["Services"]["Revenue"] == 400.0
