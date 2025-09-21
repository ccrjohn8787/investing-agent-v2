"""Persistence for analyst/verifier reports per ticker."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from hybrid_agent.storage.json_store import JSONKeyValueStore


class ReportStore(JSONKeyValueStore):
    def __init__(self, path: Path | str = Path("data/runtime/reports.json")) -> None:
        super().__init__(Path(path))

    def save_report(self, ticker: str, analyst: Dict[str, object], verifier: Dict[str, object]) -> None:
        payload = {"analyst": analyst, "verifier": verifier}
        self.set(ticker.upper(), payload)

    def fetch(self, ticker: str) -> Dict[str, object]:
        return self.get(ticker.upper(), {})

    def all_reports(self) -> Dict[str, object]:
        return self.all()
