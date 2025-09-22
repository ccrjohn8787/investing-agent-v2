"""Calculation service that aggregates deterministic metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from hybrid_agent.calculators.metric_builder import MetricBuilder
from hybrid_agent.models import CompanyQuarter, Metric
from hybrid_agent.parse.normalize import Normalizer
from hybrid_agent.valuation import ValuationBuilder, ValuationBundle


@dataclass
class CalculationResult:
    ticker: str
    period: str
    metrics: List[Metric]
    quarter: CompanyQuarter
    history: List[CompanyQuarter]
    valuation: Optional[ValuationBundle]


class CalculationService:
    def __init__(
        self,
        normalizer: Optional[Normalizer] = None,
        builder: Optional[MetricBuilder] = None,
        valuation_builder: Optional[ValuationBuilder] = None,
    ) -> None:
        self._normalizer = normalizer or Normalizer()
        self._builder = builder or MetricBuilder()
        self._valuation_builder = valuation_builder or ValuationBuilder()

    def calculate(self, quarter: CompanyQuarter, history: Optional[List[CompanyQuarter]] = None) -> CalculationResult:
        history = history or []
        normalized_history = [
            self._normalizer.normalize_quarter(past, []) for past in history
        ]
        normalized = self._normalizer.normalize_quarter(quarter, normalized_history)
        metrics = self._builder.build(normalized)
        valuation = self._valuation_builder.build(normalized)
        if valuation:
            metrics.extend(self._build_valuation_metrics(normalized, valuation))
        return CalculationResult(
            ticker=normalized.ticker,
            period=normalized.period,
            metrics=metrics,
            quarter=normalized,
            history=normalized_history,
            valuation=valuation,
        )

    def _build_valuation_metrics(
        self,
        quarter: CompanyQuarter,
        valuation: ValuationBundle,
    ) -> List[Metric]:
        metrics: List[Metric] = []
        metrics.append(
            self._builder.metric_from_value(
                "WACC-point",
                valuation.wacc.point,
                unit="ratio",
                quarter=quarter,
                inputs=["risk_free_rate", "equity_risk_premium", "beta", "cost_of_debt"],
            )
        )
        metrics.append(
            self._builder.metric_from_value(
                "WACC-lower",
                valuation.wacc.lower,
                unit="ratio",
                quarter=quarter,
                inputs=["WACC-point"],
            )
        )
        metrics.append(
            self._builder.metric_from_value(
                "WACC-upper",
                valuation.wacc.upper,
                unit="ratio",
                quarter=quarter,
                inputs=["WACC-point"],
            )
        )
        metrics.append(
            self._builder.metric_from_value(
                "Cost of Equity",
                valuation.wacc.cost_of_equity,
                unit="ratio",
                quarter=quarter,
                inputs=["risk_free_rate", "beta", "equity_risk_premium"],
            )
        )
        metrics.append(
            self._builder.metric_from_value(
                "Cost of Debt (after tax)",
                valuation.wacc.cost_of_debt_after_tax,
                unit="ratio",
                quarter=quarter,
                inputs=["cost_of_debt", "tax_rate"],
            )
        )
        metrics.append(
            self._builder.metric_from_value(
                "Terminal Growth",
                valuation.terminal_growth,
                unit="ratio",
                quarter=quarter,
                inputs=["inflation", "real_gdp"],
            )
        )
        metrics.append(
            self._builder.metric_from_value(
                "Hurdle IRR",
                valuation.hurdle,
                unit="ratio",
                quarter=quarter,
                inputs=["policy_base", "adjustment_bps"],
            )
        )
        return metrics
