from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.models import CompanyQuarter


def _valuation_provenance():
    return {
        "source_doc_id": "MACRO-20240630",
        "page_or_section": "FRED",
        "quote": "10Y Treasury yield and ERP snapshot",
        "url": "https://example.com/macro",
    }


def test_calculation_service_appends_valuation_metrics():
    quarter = CompanyQuarter(
        ticker="TEST",
        period="2024Q2",
        income_stmt={"Revenue": 5_000_000_000.0, "NetIncome": 800_000_000.0, "EBIT": 1_000_000_000.0},
        balance_sheet={
            "TotalAssets": 20_000_000_000.0,
            "TotalEquity": 12_000_000_000.0,
            "TotalDebt": 6_000_000_000.0,
            "Cash": 1_500_000_000.0,
        },
        cash_flow={"CFO": 1_200_000_000.0, "CapEx": -300_000_000.0, "FCF": 900_000_000.0},
        segments={"Consolidated": {"Revenue": 5_000_000_000.0}},
        metadata={
            "valuation": {
                "risk_free_rate": 0.04,
                "equity_risk_premium": 0.055,
                "beta": 1.2,
                "cost_of_debt": 0.05,
                "tax_rate": 0.21,
                "market_equity_value": 40_000_000_000.0,
                "market_debt_value": 20_000_000_000.0,
                "equity_adjustment_bps": 50.0,
                "share_price": 45.0,
                "shares_diluted": 1_000_000_000.0,
                "net_debt": 4_500_000_000.0,
                "terminal_inputs": {"inflation": 0.02, "real_gdp": 0.015},
                "hurdle": {
                    "base": 0.15,
                    "adjustment_bps": -150.0,
                    "rationale": "Mature, diversified cash flows justify lower hurdle.",
                },
                "fcf_paths": {
                    "Base": [900_000_000.0] * 5,
                    "Bull": [1_050_000_000.0] * 5,
                    "Bear": [800_000_000.0] * 5,
                },
                "notes": "Deterministic projection calibrated to internal base case.",
                "provenance": {
                    "WACC-point": _valuation_provenance(),
                    "WACC-lower": _valuation_provenance(),
                    "WACC-upper": _valuation_provenance(),
                    "Terminal Growth": _valuation_provenance(),
                    "Hurdle IRR": _valuation_provenance(),
                    "Cost of Equity": _valuation_provenance(),
                    "Cost of Debt (after tax)": _valuation_provenance(),
                },
            }
        },
    )

    service = CalculationService()
    result = service.calculate(quarter)

    assert result.valuation is not None
    valuation = result.valuation
    assert 0.08 < valuation.wacc.point < 0.10
    names = {metric.name for metric in result.metrics}
    assert {"WACC-point", "Hurdle IRR", "Terminal Growth"}.issubset(names)
    assert valuation.irr_analysis.irr is not None
    assert valuation.fcf_paths["Base"] == tuple([900_000_000.0] * 5)
