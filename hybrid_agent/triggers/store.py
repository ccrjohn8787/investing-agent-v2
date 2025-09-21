"""Persistence for trigger monitor state."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from hybrid_agent.storage.json_store import JSONKeyValueStore


class TriggerStore(JSONKeyValueStore):
    def __init__(self, path: Path | str = Path("data/runtime/triggers.json")) -> None:
        super().__init__(Path(path))

    def upsert(self, ticker: str, triggers: List[Dict[str, str]]) -> None:
        self.set(ticker.upper(), triggers)

    def list(self, ticker: str) -> List[Dict[str, str]]:
        return self.get(ticker.upper(), [])
