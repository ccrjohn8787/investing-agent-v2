"""Return on invested capital helpers."""
from __future__ import annotations

from typing import Optional

from .utils import safe_div


def nopat(ebit: float, tax_rate: float) -> Optional[float]:
    """Net operating profit after tax."""

    if ebit is None or tax_rate is None:
        return None
    return ebit * (1.0 - tax_rate)


def invested_capital(
    total_equity: float,
    total_debt: float,
    cash_and_equivalents: float,
    non_operating_assets: float = 0.0,
) -> Optional[float]:
    """Compute invested capital = equity + debt - cash - non-operating assets."""

    if None in (total_equity, total_debt, cash_and_equivalents, non_operating_assets):
        return None
    return total_equity + total_debt - cash_and_equivalents - non_operating_assets


def roic(nopat_value: float, invested_capital_value: float) -> Optional[float]:
    """ROIC = NOPAT / invested capital."""

    return safe_div(nopat_value, invested_capital_value)


def incremental_roic(
    nopat_current: float,
    nopat_prior: float,
    invested_capital_current: float,
    invested_capital_prior: float,
) -> Optional[float]:
    """Incremental ROIC = ΔNOPAT / ΔInvested Capital."""

    if None in (
        nopat_current,
        nopat_prior,
        invested_capital_current,
        invested_capital_prior,
    ):
        return None
    delta_nopat = nopat_current - nopat_prior
    delta_capital = invested_capital_current - invested_capital_prior
    return safe_div(delta_nopat, delta_capital)
