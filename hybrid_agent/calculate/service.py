"""Calculation service that aggregates deterministic metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from hybrid_agent.calculators.metric_builder import MetricBuilder
from hybrid_agent.models import CompanyQuarter, Metric
from hybrid_agent.parse.normalize import Normalizer


@dataclass
class CalculationResult:
    ticker: str
    period: str
    metrics: List[Metric]
    quarter: CompanyQuarter
    history: List[CompanyQuarter]


class CalculationService:
    def __init__(self, normalizer: Optional[Normalizer] = None, builder: Optional[MetricBuilder] = None) -> None:
        self._normalizer = normalizer or Normalizer()
        self._builder = builder or MetricBuilder()

    def calculate(self, quarter: CompanyQuarter, history: Optional[List[CompanyQuarter]] = None) -> CalculationResult:
        history = history or []
        normalized_history = [
            self._normalizer.normalize_quarter(past, []) for past in history
        ]
        normalized = self._normalizer.normalize_quarter(quarter, normalized_history)
        metrics = self._builder.build(normalized)
        return CalculationResult(
            ticker=normalized.ticker,
            period=normalized.period,
            metrics=metrics,
            quarter=normalized,
            history=normalized_history,
        )
