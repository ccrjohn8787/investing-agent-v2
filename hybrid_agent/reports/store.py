"""Persistence for analyst/verifier reports per ticker."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from hybrid_agent.storage.json_store import JSONKeyValueStore


class ReportStore(JSONKeyValueStore):
    def __init__(self, path: Path | str = Path("data/runtime/reports.json")) -> None:
        super().__init__(Path(path))

    def save_report(
        self,
        ticker: str,
        analyst: Dict[str, object] | None = None,
        verifier: Dict[str, object] | None = None,
        **extras: Dict[str, object],
    ) -> None:
        existing = self.get(ticker.upper(), {})
        if analyst is not None:
            existing["analyst"] = analyst
        if verifier is not None:
            existing["verifier"] = verifier
        for key, value in extras.items():
            if value is not None:
                existing[key] = value
        self.set(ticker.upper(), existing)

    def fetch(self, ticker: str) -> Dict[str, object]:
        return self.get(ticker.upper(), {})

    def all_reports(self) -> Dict[str, object]:
        return self.all()
