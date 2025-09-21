from hybrid_agent.models import CompanyQuarter
from hybrid_agent.parse.normalize import Normalizer


def _quarter(period: str, revenue: float, ebit: float, cfo: float, fcf: float) -> CompanyQuarter:
    return CompanyQuarter(
        ticker="TEST",
        period=period,
        income_stmt={"Revenue": revenue, "EBIT": ebit},
        balance_sheet={
            "AccountsReceivable": revenue * 0.1,
            "Inventory": revenue * 0.05,
            "TotalAssets": revenue * 0.8,
            "Cash": revenue * 0.2,
            "TotalEquity": revenue * 0.4,
        },
        cash_flow={"CFO": cfo, "FCF": fcf},
        segments={"Consolidated": {"Revenue": revenue}},
        metadata={"unit_scale": 1000, "currency": "USD"},
    )


def test_normalizer_scales_and_rolls_ttm():
    normalizer = Normalizer()
    history = [
        _quarter("2024Q1", 450, 45, 40, 35),
        _quarter("2023Q4", 430, 40, 38, 32),
        _quarter("2023Q3", 410, 38, 36, 30),
    ]
    current = _quarter("2024Q2", 500, 50, 42, 37)

    normalized = normalizer.normalize_quarter(current, history)

    # unit scaling applied
    assert normalized.income_stmt["Revenue"] == 500_000.0
    assert normalized.cash_flow["FCF"] == 37_000.0
    assert normalized.segments["Consolidated"]["Revenue"] == 500_000.0

    metadata = normalized.metadata
    assert metadata["original_unit_scale"] == 1000
    assert metadata["unit_scale"] == 1.0
    assert metadata["currency"] == "USD"

    # TTM revenue = sum of current + three prior quarters
    expected_ttm_revenue = sum(q.income_stmt["Revenue"] * 1000 for q in [current] + history[:3])
    assert metadata["ttm"]["Revenue"] == expected_ttm_revenue
    assert metadata["ttm"]["FCF"] == sum(q.cash_flow["FCF"] * 1000 for q in [current] + history[:3])
    assert metadata["ttm"]["AccountsReceivable"] == normalized.balance_sheet["AccountsReceivable"]
    assert metadata["ttm_period"].startswith("TTM-2024")
