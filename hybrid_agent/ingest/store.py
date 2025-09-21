"""Local point-in-time document store."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from hybrid_agent.models import Document


class DocumentStore:
    """Persists immutable documents keyed by ticker and PIT hash."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save(self, document: Document, content: bytes) -> Document:
        ticker_dir = self._base_path / document.ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = ticker_dir / f"{document.id}.json"
        binary_path = ticker_dir / f"{document.id}.bin"

        if not metadata_path.exists():
            metadata_path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        if not binary_path.exists():
            binary_path.write_bytes(content)
        return document

    def load(self, document_id: str) -> Tuple[Document, bytes]:
        ticker = document_id.split("-", 1)[0]
        ticker_dir = self._base_path / ticker
        metadata_path = ticker_dir / f"{document_id}.json"
        binary_path = ticker_dir / f"{document_id}.bin"
        if not metadata_path.exists() or not binary_path.exists():
            raise FileNotFoundError(document_id)
        document = Document.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        content = binary_path.read_bytes()
        return document, content

    def list_documents(self) -> Iterable[Document]:
        for metadata_path in self._base_path.glob("*/*.json"):
            yield Document.model_validate_json(metadata_path.read_text(encoding="utf-8"))
