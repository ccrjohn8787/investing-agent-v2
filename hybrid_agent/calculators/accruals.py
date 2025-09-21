"""Accrual quality metrics."""
from __future__ import annotations

from typing import Optional

from .utils import safe_div


def accruals_ratio(
    net_income: float,
    cash_flow_from_operations: float,
    average_total_assets: float,
) -> Optional[float]:
    """Compute Sloan accruals ratio = (NI - CFO) / Avg Total Assets."""

    if net_income is None or cash_flow_from_operations is None:
        return None
    numerator = net_income - cash_flow_from_operations
    return safe_div(numerator, average_total_assets)


def balance_sheet_accruals(
    delta_current_assets: float,
    delta_cash: float,
    delta_current_liabilities: float,
    delta_short_term_debt: float,
    average_total_assets: float,
) -> Optional[float]:
    """Compute balance-sheet based accruals ratio per Sloan (1996)."""

    if None in (
        delta_current_assets,
        delta_cash,
        delta_current_liabilities,
        delta_short_term_debt,
    ):
        return None
    numerator = (
        (delta_current_assets - delta_cash)
        - (delta_current_liabilities - delta_short_term_debt)
    )
    return safe_div(numerator, average_total_assets)
