"""Normalization helpers for structured financial statements."""
from __future__ import annotations

from dataclasses import replace

from hybrid_agent.models import CompanyQuarter


class Normalizer:
    """Normalizes parsed financial statements."""

    def normalize_quarter(self, quarter: CompanyQuarter) -> CompanyQuarter:
        # Placeholder for currency/unit adjustments; currently pass-through.
        return replace(quarter)
