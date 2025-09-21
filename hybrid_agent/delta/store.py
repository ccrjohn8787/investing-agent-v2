"""Persistence layer for delta computations."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from hybrid_agent.storage.json_store import JSONKeyValueStore


class DeltaStore(JSONKeyValueStore):
    def __init__(self, path: Path | str = Path("data/runtime/deltas.json")) -> None:
        super().__init__(Path(path))

    def save(self, ticker: str, deltas: Dict[str, Dict[str, float]]) -> None:
        self.set(ticker.upper(), deltas)

    def fetch(self, ticker: str) -> Dict[str, Dict[str, float]]:
        return self.get(ticker.upper(), {})
