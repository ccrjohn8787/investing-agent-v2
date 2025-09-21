"""Normalization helpers for structured financial statements."""
from __future__ import annotations

from hybrid_agent.models import CompanyQuarter


class Normalizer:
    """Normalizes parsed financial statements."""

    def normalize_quarter(self, quarter: CompanyQuarter) -> CompanyQuarter:
        # Placeholder for currency/unit adjustments; currently a deep copy.
        return quarter.model_copy(deep=True)
