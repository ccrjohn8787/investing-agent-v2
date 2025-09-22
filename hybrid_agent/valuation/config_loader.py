"""Helpers for applying valuation configuration metadata."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import CompanyQuarter, Document


class ValuationConfigLoader:
    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = base_path or Path(__file__).resolve().parents[1] / "configs" / "valuation"

    def load(self, ticker: str) -> Optional[Dict[str, Any]]:
        path = self._base_path / f"{ticker.upper()}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def apply(
        self,
        quarter: CompanyQuarter,
        config: Dict[str, Any],
        store: Optional[DocumentStore] = None,
    ) -> CompanyQuarter:
        updated = quarter.model_copy(deep=True)
        metadata = dict(updated.metadata)
        valuation_meta = dict(config.get("valuation", {}))
        provenance = config.get("provenance")
        if provenance:
            valuation_meta["provenance"] = provenance
        metadata["valuation"] = valuation_meta
        updated.metadata = metadata
        documents = config.get("documents", [])
        if store and documents:
            for doc_payload in documents:
                self._persist_document(store, doc_payload)
        return updated

    def _persist_document(self, store: DocumentStore, payload: Dict[str, Any]) -> None:
        if "content" not in payload:
            return
        content_text = str(payload["content"])
        content_bytes = content_text.encode("utf-8")
        doc_fields = {key: value for key, value in payload.items() if key != "content"}
        if "pit_hash" not in doc_fields:
            doc_fields["pit_hash"] = hashlib.sha256(content_bytes).hexdigest()
        document = Document(**doc_fields)
        try:
            store.load(document.id)
        except FileNotFoundError:
            store.save(document, content_bytes)


def apply_valuation_config(
    quarter: CompanyQuarter,
    ticker: str,
    store: Optional[DocumentStore] = None,
    base_path: Optional[Path] = None,
) -> CompanyQuarter:
    loader = ValuationConfigLoader(base_path=base_path)
    config = loader.load(ticker)
    if not config:
        return quarter
    return loader.apply(quarter, config, store=store)
