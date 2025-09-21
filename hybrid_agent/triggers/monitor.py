"""Trigger monitor tracks KPI thresholds and deadlines."""
from __future__ import annotations


from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple

from .store import TriggerStore


class TriggerMonitor:
    def __init__(self, store: TriggerStore | None = None) -> None:
        self._store = store or TriggerStore()
        self._triggers: Dict[Tuple[str, str], Trigger] = {}

    def upsert(self, ticker: str, name: str, threshold: float, comparison: str, deadline: date) -> None:
        self._triggers[(ticker, name)] = Trigger(ticker, name, threshold, comparison, deadline)
        serialized = [
            {
                "name": trig.name,
                "threshold": trig.threshold,
                "comparison": trig.comparison,
                "deadline": trig.deadline.isoformat(),
            }
            for trig in self._triggers.values()
            if trig.ticker == ticker
        ]
        self._store.upsert(ticker, serialized)

    def remove(self, ticker: str, name: str) -> None:
        self._triggers.pop((ticker, name), None)
        serialized = [
            {
                "name": trig.name,
                "threshold": trig.threshold,
                "comparison": trig.comparison,
                "deadline": trig.deadline.isoformat(),
            }
            for key, trig in self._triggers.items()
            if key[0] == ticker
        ]
        self._store.upsert(ticker, serialized)

    def evaluate(self, ticker: str, metrics: Dict[str, float], today: date) -> List[Dict[str, str]]:
        alerts: List[Dict[str, str]] = []
        if not any(key[0] == ticker for key in self._triggers.keys()):
            self._load_from_store(ticker)
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

    def _load_from_store(self, ticker: str) -> None:
        stored = self._store.list(ticker)
        for record in stored:
            try:
                deadline = date.fromisoformat(record["deadline"])
            except Exception:
                continue
            self._triggers[(ticker, record["name"])] = Trigger(
                ticker=ticker,
                name=record["name"],
                threshold=float(record["threshold"]),
                comparison=record["comparison"],
                deadline=deadline,
            )
@dataclass
class Trigger:
    ticker: str
    name: str
    threshold: float
    comparison: str
    deadline: date
