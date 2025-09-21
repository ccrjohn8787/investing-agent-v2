import pytest

from hybrid_agent.delta.delta_engine import DeltaEngine
from hybrid_agent.models import CompanyQuarter


def _quarter(period: str, revenue: float, cfo: float) -> CompanyQuarter:
    return CompanyQuarter(
        ticker="AAPL",
        period=period,
        income_stmt={"Revenue": revenue},
        balance_sheet={},
        cash_flow={"CFO": cfo},
        segments={},
    )


def test_delta_engine_computes_qoq_and_yoy():
    current = _quarter("2024Q2", 1000.0, 400.0)
    prior = _quarter("2024Q1", 950.0, 350.0)
    year_ago = _quarter("2023Q2", 800.0, 300.0)

    engine = DeltaEngine()
    result = engine.compute(current, prior, year_ago)

    assert result["Revenue"]["qoq"] == 50.0
    assert result["Revenue"]["yoy"] == 200.0
    assert result["CFO"]["qoq_percent"] == pytest.approx(0.142857, rel=1e-3)
