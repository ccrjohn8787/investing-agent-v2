from hybrid_agent.valuation.wacc import WACCCalculator, WACCInputs


def test_wacc_derivation_inputs_provenance():
    calc = WACCCalculator()
    params = WACCInputs(
        risk_free_rate=0.045,
        equity_risk_premium=0.055,
        beta=1.1,
        cost_of_debt=0.06,
        tax_rate=0.21,
        market_equity_value=80.0,
        market_debt_value=20.0,
        equity_adjustment_bps=25,
    )
    res = calc.derive(params)

    assert 0.07 <= res.point <= 0.11
    assert res.lower == res.point - 0.01
    assert res.upper == res.point + 0.01
    for key in ["rf", "erp", "beta", "rd", "tax", "weights_equity", "weights_debt"]:
        assert key in res.inputs
    assert res.cost_of_equity > params.risk_free_rate
    assert res.weights["equity"] == 0.8
    assert res.weights["debt"] == 0.2
