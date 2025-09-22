"""Helpers for caching PIT documents in memory during validation."""
from __future__ import annotations

from functools import lru_cache
from hybrid_agent.models import Document
from hybrid_agent.ingest.store import DocumentStore


class DocumentCache:
    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    @lru_cache(maxsize=128)
    def fetch_text(self, doc_id: str) -> str:
        document, raw_bytes = self._store.load(doc_id)
        return raw_bytes.decode("latin-1", errors="ignore")

    @lru_cache(maxsize=128)
    def fetch_document(self, doc_id: str) -> Document:
        document, _ = self._store.load(doc_id)
        return document
