import pytest

from hybrid_agent.calculators import dcf


def test_enterprise_value():
    assert dcf.enterprise_value(25, 1_000, 200) == pytest.approx(25_200)


def test_capm_cost_of_equity_with_adjustment_bounds():
    result = dcf.capm_cost_of_equity(0.04, 1.2, 0.05, adjustment_bps=200)
    # adjustment capped at 150 bps
    expected = 0.04 + 1.2 * 0.05 + 0.015
    assert result == pytest.approx(expected)


def test_capm_cost_of_equity_missing_returns_none():
    assert dcf.capm_cost_of_equity(None, 1, 0.05) is None


def test_after_tax_cost_of_debt():
    assert dcf.after_tax_cost_of_debt(0.06, 0.25) == pytest.approx(0.045)


def test_capital_structure_weights():
    eq_w, debt_w = dcf.capital_structure_weights(600, 400)
    assert eq_w == pytest.approx(0.6)
    assert debt_w == pytest.approx(0.4)


def test_capital_structure_weights_zero_total_returns_none():
    assert dcf.capital_structure_weights(0, 0) is None


def test_weighted_average_cost_of_capital():
    result = dcf.weighted_average_cost_of_capital(0.09, 0.04, 600, 400)
    expected = 0.09 * 0.6 + 0.04 * 0.4
    assert result == pytest.approx(expected)


def test_terminal_value_gordon():
    result = dcf.terminal_value_gordon(200, 0.1, 0.03)
    expected = 200 * 1.03 / (0.1 - 0.03)
    assert result == pytest.approx(expected)


def test_terminal_value_gordon_invalid_when_growth_exceeds_discount():
    assert dcf.terminal_value_gordon(200, 0.04, 0.05) is None


def test_discount_cash_flows():
    result = dcf.discount_cash_flows([100, 110], 0.1)
    expected = 100 / 1.1 + 110 / 1.21
    assert result == pytest.approx(expected)


def test_reverse_dcf_enterprise_value():
    projected = [100, 110, 120]
    result = dcf.reverse_dcf_enterprise_value(projected, 0.1, 0.03)
    pv = dcf.discount_cash_flows(projected, 0.1)
    tv = dcf.terminal_value_gordon(projected[-1], 0.1, 0.03)
    expected = pv + tv / (1.1 ** 3)
    assert result == pytest.approx(expected)


def test_implied_equity_value():
    assert dcf.implied_equity_value(10_000, 500) == 9_500


def test_implied_share_price():
    assert dcf.implied_share_price(9_500, 1_000) == pytest.approx(9.5)


def test_internal_rate_of_return():
    # invest 100 today, receive 60, 60, 60
    irr = dcf.internal_rate_of_return([-100, 60, 60, 60])
    assert irr == pytest.approx(0.3631, rel=1e-3)


def test_internal_rate_of_return_non_convergence_returns_none():
    assert dcf.internal_rate_of_return([-100, 0, 0]) is None


def test_build_equity_cash_flows():
    cash_flows = dcf.build_equity_cash_flows(50, [120, 130], 1_000, 100)
    expected_terminal = 1_000 / 100
    assert cash_flows == (-50, 1.2, 1.3 + expected_terminal)


def test_build_equity_cash_flows_validates_inputs():
    assert dcf.build_equity_cash_flows(50, [], 1_000, 100) is None
    assert dcf.build_equity_cash_flows(50, [120], 1_000, 0) is None


def test_valuation_sensitivity():
    assert dcf.valuation_sensitivity(0.08, [-0.01, 0, 0.01]) == (0.07, 0.08, 0.09)


def test_irr_monotonicity_and_sensitivity():
    base = dcf.run_irr_analysis(
        price=100,
        shares=1,
        net_debt=0,
        wacc=0.10,
        terminal_g=0.03,
        fcf_path=[100, 110, 121, 133, 146],
        scenarios={
            "Bull": [100, 120, 144, 173, 208],
            "Bear": [100, 105, 110, 115, 120],
        },
    )

    better = dcf.run_irr_analysis(
        price=100,
        shares=1,
        net_debt=0,
        wacc=0.09,
        terminal_g=0.035,
        fcf_path=[100, 115, 132, 152, 175],
    )

    assert better.irr > base.irr
    assert set(base.sensitivity.keys()) == {"wacc+100bps", "wacc-100bps", "g+50bps", "g-50bps"}
    assert base.scenarios[0].name == "Bull"
