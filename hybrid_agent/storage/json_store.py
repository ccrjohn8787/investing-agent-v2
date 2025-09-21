"""Simple JSON-backed key-value store utilities."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JSONKeyValueStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = value
        self._write(data)

    def get(self, key: str, default: Any = None) -> Any:
        data = self._load()
        return data.get(key, default)

    def all(self) -> Dict[str, Any]:
        return self._load()

    def delete(self, key: str) -> None:
        data = self._load()
        if key in data:
            del data[key]
            self._write(data)
