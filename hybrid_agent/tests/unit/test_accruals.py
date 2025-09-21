import pytest

from hybrid_agent.calculators import accruals


def test_accruals_ratio_basic():
    result = accruals.accruals_ratio(100, 80, 400)
    assert result == pytest.approx(0.05)


def test_accruals_ratio_missing_inputs_returns_none():
    assert accruals.accruals_ratio(None, 80, 400) is None


def test_balance_sheet_accruals():
    result = accruals.balance_sheet_accruals(50, 5, 30, 2, 400)
    expected = ((50 - 5) - (30 - 2)) / 400
    assert result == pytest.approx(expected)


def test_balance_sheet_accruals_missing_inputs_returns_none():
    assert accruals.balance_sheet_accruals(None, 5, 30, 2, 400) is None
