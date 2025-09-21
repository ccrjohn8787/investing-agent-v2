"""Retriever for evidence snippets."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .index import InMemoryDocumentIndex, IndexedChunk


def _score(query_terms: List[str], chunk: IndexedChunk) -> float:
    chunk_terms = chunk.text.lower().split()
    counts = Counter(chunk_terms)
    return float(sum(counts[term] for term in query_terms))


class Retriever:
    def __init__(self, index: InMemoryDocumentIndex) -> None:
        self._index = index

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, str]]:
        terms = query.lower().split()
        scored = []
        for chunk in self._index.iter_chunks():
            score = _score(terms, chunk)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for _, chunk in scored[:top_k]:
            results.append(
                {
                    "document_id": chunk.document_id,
                    "ticker": chunk.ticker,
                    "document_type": chunk.document_type,
                    "url": chunk.url,
                    "excerpt": chunk.text,
                }
            )
        return results
