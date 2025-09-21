import math

import pytest

from hybrid_agent.calculators import balance_sheet as bs


def test_net_debt():
    assert bs.net_debt(500, 120) == 380


def test_net_leverage_ratio():
    assert bs.net_leverage_ratio(500, 200, 150) == pytest.approx(2.0)


def test_net_leverage_missing_inputs_returns_none():
    assert bs.net_leverage_ratio(500, None, 150) is None


def test_interest_coverage_uses_absolute_interest():
    assert bs.interest_coverage(120, -30) == pytest.approx(4.0)


def test_fcf_interest_coverage_handles_none():
    assert bs.fcf_interest_coverage(100, None) is None


def test_twenty_four_month_coverage():
    result = bs.twenty_four_month_coverage(200, 100, 50, 150)
    assert result == pytest.approx(2.3333333)


def test_twenty_four_month_coverage_missing_returns_none():
    assert bs.twenty_four_month_coverage(200, None, 50, 150) is None


def test_runway_months_positive_burn():
    assert bs.runway_months(200, 50, 20, -120) == pytest.approx((200 + 50 - 20) / (120 / 12))


def test_runway_months_zero_burn_returns_inf():
    assert math.isinf(bs.runway_months(200, 0, 10, 120))


def test_runway_months_no_liquidity_returns_zero():
    assert bs.runway_months(10, 0, 20, -120) == 0.0
