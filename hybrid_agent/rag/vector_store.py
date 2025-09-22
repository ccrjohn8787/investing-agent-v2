"""TF-IDF based vector store for document retrieval."""
from __future__ import annotations

import math
import pickle
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hybrid_agent.models import Document


@dataclass
class VectorStoreEntry:
    document_id: str
    doc_type: str
    url: str
    ticker: str
    text: str


class _SimpleTfidfVectorizer:
    """Lightweight TF-IDF vectorizer without external dependencies."""

    TOKEN_RE = re.compile(r"\b\w+\b", re.UNICODE)

    def __init__(self, *, min_df: int = 1) -> None:
        self._min_df = max(min_df, 1)
        self._idf: Dict[str, float] = {}
        self._vocab: Dict[str, int] = {}
        self._matrix: List[Dict[str, float]] = []

    def fit_transform(self, corpus: List[str]) -> List[Dict[str, float]]:
        doc_tokens = [self._tokenize(text) for text in corpus]
        doc_tf: List[Counter[str]] = []
        doc_freq: Counter[str] = Counter()
        for tokens in doc_tokens:
            counts = Counter(tokens)
            doc_tf.append(counts)
            doc_freq.update(counts.keys())

        vocab = {
            term: idx
            for idx, (term, df) in enumerate(doc_freq.items())
            if df >= self._min_df
        }
        self._vocab = vocab
        n_docs = len(corpus)
        self._idf = {
            term: math.log((1 + n_docs) / (1 + doc_freq[term])) + 1.0
            for term in vocab
        }

        vectors: List[Dict[str, float]] = []
        for counts in doc_tf:
            vector: Dict[str, float] = {}
            total = sum(counts.values()) or 1.0
            for term, count in counts.items():
                if term not in vocab:
                    continue
                tf = count / total
                weight = tf * self._idf[term]
                vector[term] = weight
            vectors.append(self._normalize(vector))

        self._matrix = vectors
        return vectors

    def transform(self, corpus: List[str]) -> List[Dict[str, float]]:
        vectors: List[Dict[str, float]] = []
        for text in corpus:
            counts = Counter(self._tokenize(text))
            total = sum(counts.values()) or 1.0
            vector: Dict[str, float] = {}
            for term, count in counts.items():
                if term not in self._vocab:
                    continue
                tf = count / total
                weight = tf * self._idf.get(term, 0.0)
                if weight > 0:
                    vector[term] = weight
            vectors.append(self._normalize(vector))
        return vectors

    def _normalize(self, vector: Dict[str, float]) -> Dict[str, float]:
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        return {term: value / norm for term, value in vector.items()}

    def _tokenize(self, text: str) -> List[str]:
        return [match.group(0).lower() for match in self.TOKEN_RE.finditer(text)]


class TfidfVectorStore:
    """Stores document chunks and allows cosine similarity search."""

    def __init__(self, *, min_df: int = 1) -> None:
        self._entries: List[VectorStoreEntry] = []
        self._vectorizer = _SimpleTfidfVectorizer(min_df=min_df)
        self._matrix: List[Dict[str, float]] = []

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
            self._matrix = []

    def search(self, query: str, *, top_k: int = 5) -> List[Tuple[VectorStoreEntry, float]]:
        if not query.strip() or not self._matrix:
            return []
        query_vec = self._vectorizer.transform([query])[0]
        if not query_vec:
            return []
        scores: List[float] = []
        for vector in self._matrix:
            score = self._cosine(query_vec, vector)
            scores.append(score)
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:top_k]
        return [
            (self._entries[idx], float(scores[idx]))
            for idx in ranked_indices
            if scores[idx] > 0
        ]

    def _cosine(self, query_vec: Dict[str, float], doc_vec: Dict[str, float]) -> float:
        if not doc_vec:
            return 0.0
        return sum(query_vec.get(term, 0.0) * weight for term, weight in doc_vec.items())

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
