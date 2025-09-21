import pytest

from hybrid_agent.calculators import unit_econ as ue


def test_take_rate():
    assert ue.take_rate(200, 4000) == pytest.approx(0.05)


def test_net_revenue_retention():
    result = ue.net_revenue_retention(100, 30, 10, 5)
    assert result == pytest.approx((100 + 30 - 10 - 5) / 100)


def test_net_revenue_retention_missing_returns_none():
    assert ue.net_revenue_retention(None, 30, 10, 5) is None


def test_gross_revenue_retention():
    assert ue.gross_revenue_retention(100, 8) == pytest.approx(0.92)


def test_customer_acquisition_cost():
    assert ue.customer_acquisition_cost(200, 20) == pytest.approx(10.0)


def test_contribution_margin():
    assert ue.contribution_margin(500, 300) == pytest.approx(0.4)


def test_contribution_margin_missing_returns_none():
    assert ue.contribution_margin(None, 300) is None


def test_payback_period_months():
    assert ue.payback_period_months(120, 30, periods_per_year=4) == pytest.approx(12.0)


def test_ltv_to_cac():
    assert ue.ltv_to_cac(900, 300) == pytest.approx(3.0)
