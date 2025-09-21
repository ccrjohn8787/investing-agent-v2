"""Normalization helpers for structured financial statements."""
from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from hybrid_agent.models import CompanyQuarter


class Normalizer:
    """Normalizes parsed financial statements.

    Responsibilities:
    - Apply unit scaling (thousands/millions/billions) to base currency units.
    - Ensure income statement, balance sheet, and cash flow values are floats.
    - Produce trailing-twelve-month (TTM) aggregates for key flow metrics.
    - Attach normalized metadata including original scale and TTM period labels.
    """

    FLOW_METRICS: List[Tuple[str, str]] = [
        ("income_stmt", "Revenue"),
        ("income_stmt", "GrossProfit"),
        ("income_stmt", "EBIT"),
        ("cash_flow", "CFO"),
        ("cash_flow", "FCF"),
    ]

    STOCK_METRICS: List[Tuple[str, str]] = [
        ("balance_sheet", "AccountsReceivable"),
        ("balance_sheet", "Inventory"),
        ("balance_sheet", "TotalAssets"),
        ("balance_sheet", "Cash"),
        ("balance_sheet", "TotalEquity"),
    ]

    def normalize_quarter(
        self,
        quarter: CompanyQuarter,
        history: Sequence[CompanyQuarter] | None = None,
        *,
        compute_ttm: bool = True,
    ) -> CompanyQuarter:
        history = history or []
        normalized = quarter.model_copy(deep=True)

        scale = self._resolve_unit_scale(quarter)
        currency = quarter.metadata.get("currency", "USD")

        normalized.income_stmt = self._apply_scale_dict(quarter.income_stmt, scale)
        normalized.balance_sheet = self._apply_scale_dict(quarter.balance_sheet, scale)
        normalized.cash_flow = self._apply_scale_dict(quarter.cash_flow, scale)
        normalized.segments = {
            name: self._apply_scale_dict(values, scale) for name, values in quarter.segments.items()
        }

        metadata = dict(quarter.metadata)
        metadata["currency"] = currency
        metadata["original_unit_scale"] = scale
        metadata["unit_scale"] = 1.0
        if "unit_text" not in metadata and quarter.metadata.get("unit_text"):
            metadata["unit_text"] = quarter.metadata["unit_text"]

        if compute_ttm:
            ttm = self._compute_ttm(normalized, history)
            metadata["ttm"] = ttm
            metadata["ttm_period"] = self._ttm_label(normalized.period, metadata)

        normalized.metadata = metadata
        return normalized

    def _apply_scale_dict(self, data: Dict[str, float], scale: float) -> Dict[str, float]:
        scaled = {}
        for key, value in data.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            scaled[key] = numeric * scale
        return scaled

    def _resolve_unit_scale(self, quarter: CompanyQuarter) -> float:
        scale = quarter.metadata.get("unit_scale")
        if isinstance(scale, (int, float)) and scale > 0:
            return float(scale)
        unit_text = str(quarter.metadata.get("unit_text", ""))
        text = unit_text.lower()
        if "billion" in text:
            return 1_000_000_000.0
        if "million" in text:
            return 1_000_000.0
        if "thousand" in text:
            return 1_000.0
        return 1.0

    def _compute_ttm(self, current: CompanyQuarter, history: Sequence[CompanyQuarter]) -> Dict[str, float]:
        # Normalize history quarters individually (without recursive TTM)
        normalized_history: List[CompanyQuarter] = []
        for past in history[-3:]:  # only need last three quarters
            normalized_history.append(self.normalize_quarter(past, history=None, compute_ttm=False))

        ttm: Dict[str, float] = {}
        for section, field in self.FLOW_METRICS:
            current_value = self._get_metric(current, section, field)
            if current_value is None:
                continue
            total = current_value
            for past in normalized_history:
                value = self._get_metric(past, section, field)
                if value is not None:
                    total += value
            ttm[field] = total

        for section, field in self.STOCK_METRICS:
            value = self._get_metric(current, section, field)
            if value is not None:
                ttm[field] = value

        return ttm

    def _get_metric(self, quarter: CompanyQuarter, section: str, field: str) -> Optional[float]:
        container = getattr(quarter, section, {})
        value = container.get(field)
        if value is None:
            # try alternate keys with different casing
            for key, numeric in container.items():
                if key.lower() == field.lower():
                    value = numeric
                    break
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _ttm_label(self, period: str, metadata: Dict[str, object]) -> str:
        pattern = re.compile(r"(\d{4})(?:[-]?Q?(\d))", re.I)
        match = pattern.search(period or "")
        if match:
            year, quarter = match.groups()
            quarter = quarter or ""
            if quarter:
                return f"TTM-{year}Q{quarter}"
        label = metadata.get("period_label") or metadata.get("fiscal_period") or period
        return f"TTM-{label}" if label else "TTM"
