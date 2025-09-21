"""TF-IDF based vector store for document retrieval."""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from hybrid_agent.models import Document


@dataclass
class VectorStoreEntry:
    document_id: str
    doc_type: str
    url: str
    ticker: str
    text: str


class TfidfVectorStore:
    """Stores document chunks and allows cosine similarity search."""

    def __init__(self, *, min_df: int = 1) -> None:
        self._entries: List[VectorStoreEntry] = []
        self._vectorizer = TfidfVectorizer(min_df=min_df)
        self._matrix = None

    def add(self, document: Document, text: str) -> None:
        self._entries.append(
            VectorStoreEntry(
                document_id=document.id,
                doc_type=document.doc_type,
                url=str(document.url),
                ticker=document.ticker,
                text=text,
            )
        )
        self._fit()

    def _fit(self) -> None:
        corpus = [entry.text for entry in self._entries]
        if corpus:
            self._matrix = self._vectorizer.fit_transform(corpus)
        else:
            self._matrix = None

    def search(self, query: str, *, top_k: int = 5) -> List[Tuple[VectorStoreEntry, float]]:
        if not query.strip() or self._matrix is None:
            return []
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        ranked_indices = scores.argsort()[::-1][:top_k]
        return [
            (self._entries[idx], float(scores[idx]))
            for idx in ranked_indices
            if scores[idx] > 0
        ]

    def persist(self, path: Path) -> None:
        payload = {
            "entries": self._entries,
            "vectorizer": self._vectorizer,
            "matrix": self._matrix,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(payload))

    @classmethod
    def load(cls, path: Path) -> "TfidfVectorStore":
        payload = pickle.loads(path.read_bytes())
        store = cls()
        store._entries = payload["entries"]
        store._vectorizer = payload["vectorizer"]
        store._matrix = payload["matrix"]
        return store

    def __len__(self) -> int:
        return len(self._entries)
