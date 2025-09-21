"""EDGAR and IR document fetcher with provenance hashing."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import requests

from hybrid_agent.models import Document


class FetchError(RuntimeError):
    """Raised when a document cannot be fetched after retries."""


def _default_http_get(url: str) -> bytes:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "HybridAgent/1.0 (contact: research@hybridagent.local)",
            "Accept": "text/html,application/json",
        }
    )
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.content


@dataclass
class FetchMetadata:
    ticker: str
    doc_type: str
    title: str
    date: str
    url: str


class EDGARClient:
    """Minimal HTTP client for fetching primary-source documents."""

    def __init__(
        self,
        http_get: Optional[Callable[[str], bytes]] = None,
        *,
        max_retries: int = 3,
        retry_backoff: float = 0.25,
    ) -> None:
        self._http_get = http_get or _default_http_get
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff

    def fetch_document(self, **kwargs: str) -> Tuple[Document, bytes]:
        metadata = FetchMetadata(**kwargs)
        raw_bytes = self._fetch_with_retries(metadata.url)
        pit_hash = hashlib.sha256(raw_bytes).hexdigest()
        document_id = self._build_document_id(metadata.ticker, metadata.date, pit_hash)
        document = Document(
            id=document_id,
            ticker=metadata.ticker,
            doc_type=metadata.doc_type,  # type: ignore[arg-type]
            title=metadata.title,
            date=metadata.date,
            url=metadata.url,
            pit_hash=pit_hash,
            pdf_pages=None,
        )
        return document, raw_bytes

    def _fetch_with_retries(self, url: str) -> bytes:
        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                payload = self._http_get(url)
                if isinstance(payload, bytes):
                    return payload
                return bytes(payload)
            except Exception as exc:  # pragma: no cover - exception path tested indirectly
                last_error = exc
                if attempt >= self._max_retries:
                    raise FetchError(f"Failed to fetch document from {url}") from exc
                time.sleep(self._retry_backoff)
        if last_error is not None:
            raise FetchError(f"Failed to fetch document from {url}") from last_error
        raise FetchError(f"Failed to fetch document from {url}")

    @staticmethod
    def _build_document_id(ticker: str, date: str, pit_hash: str) -> str:
        clean_date = date.replace("-", "")
        return f"{ticker}-{clean_date}-{pit_hash[:12]}"
