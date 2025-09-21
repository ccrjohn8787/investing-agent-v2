"""High-level ingest orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from hybrid_agent.models import Document

from .edgar import EDGARClient
from .store import DocumentStore


@dataclass
class DocumentSpec:
    doc_type: str
    title: str
    date: str
    url: str

    @classmethod
    def from_payload(cls, payload: object) -> "DocumentSpec":
        if hasattr(payload, "model_dump"):
            raw = payload.model_dump()
        elif isinstance(payload, dict):  # type: ignore[arg-type]
            raw = payload
        else:  # pragma: no cover - defensive guard
            raw = vars(payload)
        return cls(
            doc_type=raw["doc_type"],
            title=raw["title"],
            date=raw["date"],
            url=str(raw["url"]),
        )


class IngestService:
    """Coordinates fetching and persisting primary-source documents."""

    def __init__(self, client: EDGARClient, store: DocumentStore) -> None:
        self._client = client
        self._store = store

    def ingest(self, ticker: str, documents: Sequence[object]) -> List[Document]:
        stored: List[Document] = []
        for item in documents:
            spec = DocumentSpec.from_payload(item)
            document, content = self._client.fetch_document(
                ticker=ticker,
                doc_type=spec.doc_type,
                title=spec.title,
                date=spec.date,
                url=spec.url,
            )
            stored.append(self._store.save(document, content))
        return stored

    def list_documents(self) -> Iterable[Document]:
        return self._store.list_documents()
