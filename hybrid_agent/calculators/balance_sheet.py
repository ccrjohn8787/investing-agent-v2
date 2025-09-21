"""Balance-sheet resilience and solvency metrics."""
from __future__ import annotations

from typing import Optional

from .utils import safe_div


def net_debt(total_debt: float, cash_and_equivalents: float) -> Optional[float]:
    """Compute net debt = total debt - cash."""

    if total_debt is None or cash_and_equivalents is None:
        return None
    return total_debt - cash_and_equivalents


def net_leverage_ratio(
    total_debt: float,
    cash_and_equivalents: float,
    ebitda: float,
) -> Optional[float]:
    """Compute Net Debt / EBITDA."""

    leverage = net_debt(total_debt, cash_and_equivalents)
    if leverage is None:
        return None
    return safe_div(leverage, ebitda)


def interest_coverage(ebit: float, interest_expense: float) -> Optional[float]:
    """Compute EBIT / interest expense."""

    interest = abs(interest_expense) if interest_expense is not None else None
    return safe_div(ebit, interest)


def fcf_interest_coverage(
    free_cash_flow: float,
    interest_expense: float,
) -> Optional[float]:
    """Compute FCF / interest expense."""

    interest = abs(interest_expense) if interest_expense is not None else None
    return safe_div(free_cash_flow, interest)


def twenty_four_month_coverage(
    cash: float,
    expected_fcf_next_8q: float,
    undrawn_revolver: float,
    debt_due_24m: float,
) -> Optional[float]:
    """Coverage ratio for debt maturing within 24 months."""

    if None in (cash, expected_fcf_next_8q, undrawn_revolver, debt_due_24m):
        return None
    numerator = cash + expected_fcf_next_8q + undrawn_revolver
    return safe_div(numerator, debt_due_24m)


def runway_months(
    cash: float,
    undrawn_revolver: float,
    minimum_cash: float,
    ttm_free_cash_flow: float,
) -> Optional[float]:
    """Compute cash runway in months per specification."""

    if None in (cash, undrawn_revolver, minimum_cash, ttm_free_cash_flow):
        return None
    available_liquidity = cash + undrawn_revolver - minimum_cash
    monthly_burn = max(0.0, -ttm_free_cash_flow / 12.0)
    if monthly_burn == 0:
        return float("inf")
    if available_liquidity <= 0:
        return 0.0
    return available_liquidity / monthly_burn
