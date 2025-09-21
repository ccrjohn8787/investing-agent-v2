"""Trigger monitor tracks KPI thresholds and deadlines."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple


@dataclass
class Trigger:
    ticker: str
    name: str
    threshold: float
    comparison: str
    deadline: date


class TriggerMonitor:
    def __init__(self) -> None:
        self._triggers: Dict[Tuple[str, str], Trigger] = {}

    def upsert(self, ticker: str, name: str, threshold: float, comparison: str, deadline: date) -> None:
        self._triggers[(ticker, name)] = Trigger(ticker, name, threshold, comparison, deadline)

    def remove(self, ticker: str, name: str) -> None:
        self._triggers.pop((ticker, name), None)

    def evaluate(self, ticker: str, metrics: Dict[str, float], today: date) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        for (key_ticker, name), trigger in self._triggers.items():
            if key_ticker != ticker:
                continue
            value = metrics.get(name)
            if value is None:
                continue
            if today > trigger.deadline:
                alerts.append(
                    {
                        "trigger": name,
                        "message": f"Deadline passed without update for {name}",
                    }
                )
                continue
            if self._breach(trigger.comparison, value, trigger.threshold):
                alerts.append(
                    {
                        "trigger": name,
                        "message": f"Breach detected for {name}: value {value}",
                    }
                )
        return alerts

    @staticmethod
    def _breach(comparison: str, value: float, threshold: float) -> bool:
        if comparison == "gte":
            return value < threshold
        if comparison == "lte":
            return value > threshold
        if comparison == "gt":
            return value <= threshold
        if comparison == "lt":
            return value >= threshold
        return False
