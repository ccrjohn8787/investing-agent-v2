import pytest

from hybrid_agent.calculators import utils


def test_safe_division_normal():
    assert utils.safe_div(10, 2) == 5


def test_safe_division_zero_denominator_returns_none():
    assert utils.safe_div(5, 0) is None


def test_safe_division_none_inputs_returns_none():
    assert utils.safe_div(None, 2) is None
    assert utils.safe_div(2, None) is None


def test_average_filters_none_values():
    assert utils.average([1, None, 3]) == pytest.approx(2.0)


def test_average_empty_returns_none():
    assert utils.average([]) is None


def test_rolling_average_uses_window():
    assert utils.rolling_average([1, 2, 3, 4], window=2) == pytest.approx(3.5)


def test_to_basis_points():
    assert utils.to_basis_points(0.0525) == pytest.approx(525)


def test_to_basis_points_none_returns_none():
    assert utils.to_basis_points(None) is None
