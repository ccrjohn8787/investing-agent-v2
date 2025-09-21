import pytest

from hybrid_agent.calculators import working_capital as wc


def test_days_sales_outstanding():
    assert wc.days_sales_outstanding(120, 360) == pytest.approx(121.6666667)


def test_days_sales_outstanding_handles_missing():
    assert wc.days_sales_outstanding(None, 100) is None
    assert wc.days_sales_outstanding(100, 0) is None


def test_days_inventory_on_hand():
    assert wc.days_inventory_on_hand(90, 540) == pytest.approx(60.8333333)


def test_days_payables_outstanding():
    assert wc.days_payables_outstanding(80, 730) == pytest.approx(40.0)


def test_cash_conversion_cycle_combines_components():
    dso = 100
    dio = 80
    dpo = 60
    assert wc.cash_conversion_cycle(dso, dio, dpo) == 120


def test_cash_conversion_cycle_missing_component_returns_none():
    assert wc.cash_conversion_cycle(100, None, 50) is None


def test_net_working_capital():
    assert wc.net_working_capital(500, 300) == 200


def test_net_working_capital_missing_returns_none():
    assert wc.net_working_capital(500, None) is None


def test_working_capital_turnover():
    assert wc.working_capital_turnover(1000, 200) == pytest.approx(5.0)


def test_working_capital_turnover_missing_returns_none():
    assert wc.working_capital_turnover(1000, 0) is None
