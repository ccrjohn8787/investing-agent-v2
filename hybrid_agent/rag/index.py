"""Simple in-memory document index for RAG."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from hybrid_agent.models import Document


@dataclass
class IndexedChunk:
    document_id: str
    ticker: str
    document_type: str
    url: str
    text: str


class InMemoryDocumentIndex:
    def __init__(self, chunk_size: int = 120) -> None:
        self._chunk_size = chunk_size
        self._chunks: List[IndexedChunk] = []

    def add(self, document: Document, text: str) -> None:
        words = text.split()
        if not words:
            return
        step = max(self._chunk_size // 2, 1)
        for start in range(0, len(words), step):
            window = words[start : start + self._chunk_size]
            chunk_text = " ".join(window)
            if not chunk_text:
                continue
            self._chunks.append(
                IndexedChunk(
                    document_id=document.id,
                    ticker=document.ticker,
                    document_type=document.doc_type,
                    url=document.url,
                    text=chunk_text,
                )
            )

    def iter_chunks(self) -> Iterable[IndexedChunk]:
        return iter(self._chunks)
