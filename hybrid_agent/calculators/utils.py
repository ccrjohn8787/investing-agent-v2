"""Shared numerical utilities for calculator modules."""
from __future__ import annotations

from typing import Iterable, Optional, Sequence


def safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Return numerator / denominator guarding against division by zero.

    Returns None when the denominator is missing or zero.
    """

    if denominator is None:
        return None
    if abs(denominator) < 1e-12:
        return None
    if numerator is None:
        return None
    return numerator / denominator


def average(values: Sequence[float]) -> Optional[float]:
    """Compute the arithmetic mean of a non-empty sequence."""

    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def rolling_average(values: Iterable[float], window: int) -> Optional[float]:
    """Compute the average of the most recent `window` observations."""

    subset = list(values)[-window:]
    return average(subset)


def to_basis_points(value: float) -> Optional[float]:
    """Convert a decimal rate to basis points."""

    if value is None:
        return None
    return value * 10_000
