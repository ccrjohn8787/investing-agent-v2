"""Retriever for evidence snippets."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .index import InMemoryDocumentIndex, IndexedChunk
from .vector_store import TfidfVectorStore


def _score(query_terms: List[str], chunk: IndexedChunk) -> float:
    chunk_terms = chunk.text.lower().split()
    counts = Counter(chunk_terms)
    return float(sum(counts[term] for term in query_terms))


class Retriever:
    def __init__(self, index: InMemoryDocumentIndex, vector_store: TfidfVectorStore | None = None) -> None:
        self._index = index
        self._vector_store = vector_store

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        terms = query.lower().split()
        scored = []

        if self._vector_store is not None:
            for entry, vector_score in self._vector_store.search(query, top_k=top_k):
                scored.append((vector_score, entry))

        for chunk in self._index.iter_chunks():
            score = _score(terms, chunk)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for _, chunk in scored[:top_k]:
            if isinstance(chunk, IndexedChunk):
                results.append(
                    {
                        "document_id": chunk.document_id,
                        "ticker": chunk.ticker,
                        "document_type": chunk.document_type,
                        "url": str(chunk.url),
                        "excerpt": chunk.text,
                    }
                )
            else:
                results.append(
                    {
                        "document_id": chunk.document_id,
                        "ticker": chunk.ticker,
                        "document_type": chunk.doc_type,
                        "url": chunk.url,
                        "excerpt": chunk.text,
                    }
                )
        return results
