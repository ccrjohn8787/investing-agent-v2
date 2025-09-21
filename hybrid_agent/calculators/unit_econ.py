"""Unit economics calculators covering marketplace and subscription metrics."""
from __future__ import annotations

from typing import Optional

from .utils import safe_div


def take_rate(revenue: float, gross_bookings: float) -> Optional[float]:
    """Platform take rate = revenue / gross bookings (GMV)."""

    return safe_div(revenue, gross_bookings)


def net_revenue_retention(
    starting_arr: float,
    expansions: float,
    contractions: float,
    churn: float,
) -> Optional[float]:
    """NRR = (Start + Expansions - Contractions - Churn) / Start."""

    if None in (starting_arr, expansions, contractions, churn):
        return None
    ending = starting_arr + expansions - contractions - churn
    return safe_div(ending, starting_arr)


def gross_revenue_retention(starting_arr: float, churn: float) -> Optional[float]:
    """GRR = (Start - Churn) / Start."""

    if None in (starting_arr, churn):
        return None
    retained = starting_arr - churn
    return safe_div(retained, starting_arr)


def customer_acquisition_cost(
    sales_and_marketing_spend: float,
    net_new_customers: float,
) -> Optional[float]:
    """CAC = S&M spend / net new customers."""

    return safe_div(sales_and_marketing_spend, net_new_customers)


def contribution_margin(revenue: float, variable_costs: float) -> Optional[float]:
    """Contribution margin percentage."""

    if revenue is None or variable_costs is None:
        return None
    gross_profit = revenue - variable_costs
    return safe_div(gross_profit, revenue)


def payback_period_months(
    cac: float,
    gross_profit_per_customer_per_period: float,
    periods_per_year: int = 12,
) -> Optional[float]:
    """Compute CAC payback in months given gross profit per period."""

    payback_periods = safe_div(cac, gross_profit_per_customer_per_period)
    if payback_periods is None:
        return None
    months_per_period = 12 / periods_per_year
    return payback_periods * months_per_period


def ltv_to_cac(
    lifetime_value: float,
    customer_acquisition_cost_value: float,
) -> Optional[float]:
    """Return the LTV/CAC ratio."""

    return safe_div(lifetime_value, customer_acquisition_cost_value)
