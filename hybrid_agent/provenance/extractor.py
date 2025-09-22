"""Map metrics to provenance spans within PIT documents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from hybrid_agent.models import Metric
from hybrid_agent.provenance.validator import ProvenanceValidator


@dataclass
class ProvenanceSpec:
    metric_names: List[str]
    default_quote: str


class ProvenanceMapper:
    """Attaches provenance metadata to metrics using a simple spec map."""

    def __init__(self, validator: ProvenanceValidator, spec: Dict[str, ProvenanceSpec]) -> None:
        self._validator = validator
        self._spec = spec

    def enrich(self, metrics: Iterable[Metric]) -> List[Metric]:
        enriched: List[Metric] = []
        metric_list = list(metrics)
        for metric in metric_list:
            if metric.source_doc_id == "SYSTEM-DERIVED":
                mapped = self._map_metric(metric)
                enriched.append(mapped)
            else:
                enriched.append(metric)
        issues = self._validator.validate_metrics(enriched)
        if issues:
            missing = ", ".join(f"{issue.metric}: {issue.reason}" for issue in issues)
            raise ValueError(f"provenance validation failed: {missing}")
        return enriched

    def _map_metric(self, metric: Metric) -> Metric:
        spec = self._spec.get(metric.name)
        if not spec:
            return metric
        metadata = dict(metric.metadata)
        metadata.setdefault("provenance", spec.default_quote)
        return metric.model_copy(
            update={
                "source_doc_id": metadata.get("source_doc_id", "UNKNOWN"),
                "page_or_section": metadata.get("page_or_section", "n/a"),
                "quote": metadata.get("quote", spec.default_quote),
                "url": metadata.get("url", "https://example.com"),
                "metadata": metadata,
            }
        )
