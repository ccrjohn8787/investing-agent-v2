import json
from pathlib import Path

from hybrid_agent.parse.xbrl import XBRLParser


def test_xbrl_parser_creates_company_quarter(tmp_path):
    sample_data = {
        "ticker": "AAPL",
        "period": "2024Q2",
        "income_statement": {"Revenue": 1000.0, "NetIncome": 250.0},
        "balance_sheet": {"TotalAssets": 5000.0, "TotalLiabilities": 2000.0},
        "cash_flow": {"CFO": 400.0, "CapEx": -120.0},
        "segments": {"Hardware": {"Revenue": 600.0}, "Services": {"Revenue": 400.0}},
    }
    xbrl_path = tmp_path / "aapl_2024q2.json"
    xbrl_path.write_text(json.dumps(sample_data))

    parser = XBRLParser()
    quarter = parser.parse(xbrl_path)

    assert quarter.ticker == "AAPL"
    assert quarter.period == "2024Q2"
    assert quarter.income_stmt["Revenue"] == 1000.0
    assert quarter.cash_flow["CapEx"] == -120.0
    assert "Hardware" in quarter.segments
