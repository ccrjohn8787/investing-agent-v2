"""Deterministic WACC, terminal growth, and reverse-DCF helpers."""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

from .utils import safe_div


def enterprise_value(
    share_price: float,
    shares_diluted: float,
    net_debt: float,
) -> Optional[float]:
    """Compute enterprise value from equity and net debt."""

    if None in (share_price, shares_diluted, net_debt):
        return None
    return share_price * shares_diluted + net_debt


def capm_cost_of_equity(
    risk_free_rate: float,
    beta: float,
    equity_risk_premium: float,
    *,
    adjustment_bps: float = 0.0,
    max_adjustment_bps: float = 150.0,
) -> Optional[float]:
    """CAPM cost of equity with bounded qualitative adjustment."""

    if None in (risk_free_rate, beta, equity_risk_premium):
        return None
    bounded_adjustment = max(-max_adjustment_bps, min(max_adjustment_bps, adjustment_bps))
    adjustment = bounded_adjustment / 10_000.0
    return risk_free_rate + beta * equity_risk_premium + adjustment


def after_tax_cost_of_debt(
    pretax_cost_of_debt: float,
    tax_rate: float,
) -> Optional[float]:
    """Tax-effected cost of debt."""

    if None in (pretax_cost_of_debt, tax_rate):
        return None
    return pretax_cost_of_debt * (1.0 - tax_rate)


def capital_structure_weights(
    market_equity_value: float,
    market_debt_value: float,
) -> Optional[Tuple[float, float]]:
    """Return (equity_weight, debt_weight) using market values."""

    if None in (market_equity_value, market_debt_value):
        return None
    equity = max(market_equity_value, 0.0)
    debt = max(market_debt_value, 0.0)
    total = equity + debt
    if total == 0:
        return None
    return equity / total, debt / total


def weighted_average_cost_of_capital(
    cost_of_equity: float,
    cost_of_debt_after_tax: float,
    market_equity_value: float,
    market_debt_value: float,
) -> Optional[float]:
    """Market-value weighted average cost of capital."""

    weights = capital_structure_weights(market_equity_value, market_debt_value)
    if weights is None or None in (cost_of_equity, cost_of_debt_after_tax):
        return None
    equity_weight, debt_weight = weights
    return cost_of_equity * equity_weight + cost_of_debt_after_tax * debt_weight


def terminal_value_gordon(
    final_year_cash_flow: float,
    discount_rate: float,
    terminal_growth_rate: float,
) -> Optional[float]:
    """Gordon growth terminal value."""

    if None in (final_year_cash_flow, discount_rate, terminal_growth_rate):
        return None
    if discount_rate <= terminal_growth_rate:
        return None
    return final_year_cash_flow * (1 + terminal_growth_rate) / (
        discount_rate - terminal_growth_rate
    )


def discount_cash_flows(
    cash_flows: Sequence[float],
    discount_rate: float,
) -> Optional[float]:
    """Return present value of a forward cash flow sequence."""

    if cash_flows is None or discount_rate is None:
        return None
    pv = 0.0
    for period, cash_flow in enumerate(cash_flows, start=1):
        pv += cash_flow / (1 + discount_rate) ** period
    return pv


def reverse_dcf_enterprise_value(
    projected_fcf: Sequence[float],
    wacc: float,
    terminal_growth_rate: float,
) -> Optional[float]:
    """Enterprise value implied by a free cash flow projection."""

    if wacc is None or projected_fcf is None or terminal_growth_rate is None:
        return None
    if len(projected_fcf) == 0:
        return None
    pv_fcf = discount_cash_flows(projected_fcf, wacc)
    if pv_fcf is None:
        return None
    terminal = terminal_value_gordon(projected_fcf[-1], wacc, terminal_growth_rate)
    if terminal is None:
        return None
    terminal_pv = terminal / (1 + wacc) ** len(projected_fcf)
    return pv_fcf + terminal_pv


def implied_equity_value(
    enterprise_value_amount: float,
    net_debt: float,
) -> Optional[float]:
    """Convert enterprise value back to equity value."""

    if None in (enterprise_value_amount, net_debt):
        return None
    return enterprise_value_amount - net_debt


def implied_share_price(
    equity_value: float,
    shares_diluted: float,
) -> Optional[float]:
    """Implied share price = equity value / diluted shares."""

    return safe_div(equity_value, shares_diluted)


def internal_rate_of_return(
    cash_flows: Sequence[float],
    *,
    guess: float = 0.1,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> Optional[float]:
    """Compute IRR using Newton-Raphson; returns None if it fails to converge."""

    if cash_flows is None or len(cash_flows) < 2:
        return None

    rate = guess
    for _ in range(max_iter):
        npv = 0.0
        d_npv = 0.0
        for period, cf in enumerate(cash_flows):
            denom = (1 + rate) ** period
            npv += cf / denom
            if period > 0:
                d_npv -= period * cf / ((1 + rate) ** (period + 1))
        if abs(d_npv) < 1e-9:
            return None
        new_rate = rate - npv / d_npv
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
    return None


def build_equity_cash_flows(
    initial_equity_outlay: float,
    projected_fcf: Sequence[float],
    terminal_value: float,
    shares_diluted: float,
) -> Optional[Tuple[float, ...]]:
    """Return equity cash flows for IRR calculation.

    Represents buying one share at the current price and receiving per-share
    FCF plus a terminal value in the final period.
    """

    if None in (initial_equity_outlay, projected_fcf, terminal_value, shares_diluted):
        return None
    if len(projected_fcf) == 0:
        return None
    if shares_diluted <= 0:
        return None
    per_share_fcf = [fcf / shares_diluted for fcf in projected_fcf]
    terminal_per_share = terminal_value / shares_diluted
    cash_flows = [-initial_equity_outlay, *per_share_fcf[:-1], per_share_fcf[-1] + terminal_per_share]
    return tuple(cash_flows)


def valuation_sensitivity(
    base_rate: float,
    deltas: Iterable[float],
) -> Tuple[float, ...]:
    """Return a tuple of sensitivity points around a base rate."""

    return tuple(base_rate + delta for delta in deltas)
