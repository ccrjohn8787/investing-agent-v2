"""Delta engine for quarter-over-quarter and year-over-year comparisons."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from hybrid_agent.calculators.utils import safe_div
from hybrid_agent.models import CompanyQuarter
from .store import DeltaStore


class DeltaEngine:
    KEY_METRICS = {
        "Revenue": ("income_stmt", "Revenue"),
        "Gross Profit": ("income_stmt", "GrossProfit"),
        "CFO": ("cash_flow", "CFO"),
        "FCF": ("cash_flow", "FCF"),
    }

    def __init__(self, store: Optional[DeltaStore] = None) -> None:
        self._store = store or DeltaStore()

    def compute(
        self,
        current: CompanyQuarter,
        prior: CompanyQuarter,
        year_ago: CompanyQuarter,
    ) -> Dict[str, Dict[str, float]]:
        deltas: Dict[str, Dict[str, float]] = {}
        for name, (section, key) in self.KEY_METRICS.items():
            current_value = getattr(current, section).get(key)
            prior_value = getattr(prior, section).get(key)
            year_value = getattr(year_ago, section).get(key)
            if current_value is None or prior_value is None or year_value is None:
                continue
            qoq = current_value - prior_value
            yoy = current_value - year_value
            qoq_percent = safe_div(qoq, abs(prior_value))
            yoy_percent = safe_div(yoy, abs(year_value))
            deltas[name] = {
                "current": current_value,
                "qoq": qoq,
                "yoy": yoy,
                "qoq_percent": qoq_percent if qoq_percent is not None else 0.0,
                "yoy_percent": yoy_percent if yoy_percent is not None else 0.0,
            }
        ticker = current.ticker.upper()
        self._store.save(ticker, deltas)
        return deltas

    def fetch(self, ticker: str) -> Dict[str, Dict[str, float]]:
        return self._store.fetch(ticker)
