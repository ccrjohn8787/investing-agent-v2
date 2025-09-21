import pytest

from hybrid_agent.calculators import roic


def test_nopat():
    assert roic.nopat(200, 0.21) == pytest.approx(158.0)


def test_invested_capital():
    assert roic.invested_capital(800, 400, 150, 20) == pytest.approx(1_030)


def test_invested_capital_missing_returns_none():
    assert roic.invested_capital(800, 400, None, 0) is None


def test_roic_basic():
    assert roic.roic(150, 600) == pytest.approx(0.25)


def test_incremental_roic():
    result = roic.incremental_roic(210, 180, 950, 900)
    assert result == pytest.approx((210 - 180) / (950 - 900))


def test_incremental_roic_missing_returns_none():
    assert roic.incremental_roic(None, 180, 950, 900) is None
