"""Provenance validation utilities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import Metric
from .cache import DocumentCache


@dataclass
class ProvenanceIssue:
    metric: str
    reason: str


class ProvenanceValidator:
    def __init__(self, store: DocumentStore | None) -> None:
        self._cache = DocumentCache(store) if store else None

    def validate_metrics(self, metrics: Iterable[Metric]) -> List[ProvenanceIssue]:
        if self._cache is None:
            return []
        issues: List[ProvenanceIssue] = []
        for metric in metrics:
            issues.extend(self._validate_metric(metric))
        return issues

    def _validate_metric(self, metric: Metric) -> List[ProvenanceIssue]:
        problems: List[ProvenanceIssue] = []
        if not metric.source_doc_id:
            problems.append(ProvenanceIssue(metric.name, "missing source_doc_id"))
        if not metric.page_or_section:
            problems.append(ProvenanceIssue(metric.name, "missing page_or_section"))
        if not metric.quote:
            problems.append(ProvenanceIssue(metric.name, "missing quote"))
        else:
            if len(metric.quote.split()) > 30:
                problems.append(ProvenanceIssue(metric.name, "quote exceeds 30 words"))
        if not metric.url:
            problems.append(ProvenanceIssue(metric.name, "missing url"))

        if problems:
            return problems

        if self._cache is None:
            return []
        try:
            text = self._cache.fetch_text(metric.source_doc_id)
        except Exception:
            return [ProvenanceIssue(metric.name, "unable to load source document")]

        quote = metric.quote.strip()
        if quote and quote not in text:
            normalized_text = self._normalize_text(text)
            normalized_quote = self._normalize_text(quote)
            if normalized_quote not in normalized_text:
                problems.append(ProvenanceIssue(metric.name, "quote not found in source document"))
        return problems

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value.lower())
