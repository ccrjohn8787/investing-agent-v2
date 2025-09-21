"""Deterministic WACC calculation utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class WACCInputs:
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    cost_of_debt: float
    tax_rate: float
    market_equity_value: float
    market_debt_value: float
    equity_adjustment_bps: float = 0.0  # qualitative adjustment (+/- basis points)


@dataclass
class WACCResult:
    point: float
    lower: float
    upper: float
    cost_of_equity: float
    cost_of_debt_after_tax: float
    weights: Dict[str, float]
    inputs: Dict[str, float]


class WACCCalculator:
    """Computes WACC and returns a provenance-aware bundle."""

    def derive(self, params: WACCInputs) -> WACCResult:
        cost_of_equity = self._cost_of_equity(
            params.risk_free_rate,
            params.beta,
            params.equity_risk_premium,
            params.equity_adjustment_bps,
        )
        cost_of_debt_after_tax = params.cost_of_debt * (1 - params.tax_rate)

        equity_weight, debt_weight = self._weights(
            params.market_equity_value,
            params.market_debt_value,
        )

        wacc_point = cost_of_equity * equity_weight + cost_of_debt_after_tax * debt_weight
        wacc_lower = max(wacc_point - 0.01, 0.0)
        wacc_upper = wacc_point + 0.01

        return WACCResult(
            point=wacc_point,
            lower=wacc_lower,
            upper=wacc_upper,
            cost_of_equity=cost_of_equity,
            cost_of_debt_after_tax=cost_of_debt_after_tax,
            weights={"equity": equity_weight, "debt": debt_weight},
            inputs={
                "rf": params.risk_free_rate,
                "erp": params.equity_risk_premium,
                "beta": params.beta,
                "rd": params.cost_of_debt,
                "tax": params.tax_rate,
                "weights_equity": equity_weight,
                "weights_debt": debt_weight,
                "equity_adjustment_bps": params.equity_adjustment_bps,
            },
        )

    def _cost_of_equity(
        self,
        rf: float,
        beta: float,
        erp: float,
        adjustment_bps: float,
    ) -> float:
        adjustment = adjustment_bps / 10_000.0
        return rf + beta * erp + adjustment

    def _weights(self, equity_value: float, debt_value: float) -> tuple[float, float]:
        equity = max(equity_value, 0.0)
        debt = max(debt_value, 0.0)
        total = equity + debt
        if total == 0:
            return 1.0, 0.0
        return equity / total, debt / total
