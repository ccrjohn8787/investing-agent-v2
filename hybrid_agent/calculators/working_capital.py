"""Working capital efficiency metrics."""
from __future__ import annotations

from typing import Optional

from .utils import safe_div


def days_sales_outstanding(
    accounts_receivable: float,
    revenue: float,
    *,
    days_in_period: int = 365,
) -> Optional[float]:
    """Compute DSO = AR / Revenue * days."""

    ratio = safe_div(accounts_receivable, revenue)
    if ratio is None:
        return None
    return ratio * days_in_period


def days_inventory_on_hand(
    inventory: float,
    cost_of_goods_sold: float,
    *,
    days_in_period: int = 365,
) -> Optional[float]:
    """Compute DIH = Inventory / COGS * days."""

    ratio = safe_div(inventory, cost_of_goods_sold)
    if ratio is None:
        return None
    return ratio * days_in_period


def days_payables_outstanding(
    accounts_payable: float,
    cost_of_goods_sold: float,
    *,
    days_in_period: int = 365,
) -> Optional[float]:
    """Compute DPO = AP / COGS * days."""

    ratio = safe_div(accounts_payable, cost_of_goods_sold)
    if ratio is None:
        return None
    return ratio * days_in_period


def cash_conversion_cycle(
    dso: Optional[float], dio: Optional[float], dpo: Optional[float]
) -> Optional[float]:
    """Compute Cash Conversion Cycle = DSO + DIO - DPO."""

    if dso is None or dio is None or dpo is None:
        return None
    return dso + dio - dpo


def net_working_capital(
    current_assets: float,
    current_liabilities: float,
) -> Optional[float]:
    """Net working capital = current assets - current liabilities."""

    if current_assets is None or current_liabilities is None:
        return None
    return current_assets - current_liabilities


def working_capital_turnover(
    revenue: float,
    average_net_working_capital: float,
) -> Optional[float]:
    """Compute how many times revenue covers net working capital."""

    return safe_div(revenue, average_net_working_capital)
