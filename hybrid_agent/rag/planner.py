"""Evidence retrieval query planner."""
from __future__ import annotations

from typing import Dict, Iterable, List

from hybrid_agent.models import CompanyQuarter


class RetrievalPlanner:
    """Generates retrieval queries for key qualitative checks."""

    def build_queries(self, quarter: CompanyQuarter, path: str) -> Dict[str, List[str]]:
        ticker = quarter.ticker
        metadata = quarter.metadata
        queries = {
            "pricing_power": [
                f"{ticker} pricing power premium segment",
                f"{ticker} price increases and elasticity",
            ],
            "kpi_definition": [
                f"{ticker} KPI definition change",
                f"{ticker} metric redefinition",
            ],
            "debt_footnote": [
                f"{ticker} debt footnote maturity schedule",
                f"{ticker} debt due 24 months",
            ],
            "auditor_opinion": [
                f"{ticker} auditor report opinion",
                f"{ticker} going concern statement",
            ],
            "segment_notes": [
                f"{ticker} segment performance commentary",
            ],
            "supplier_finance": [
                f"{ticker} supplier finance arrangements",
            ],
        }
        return queries

    def top_results(self, planner_output: Dict[str, List[str]], retriever, top_k: int = 1) -> Dict[str, List[Dict[str, str]]]:
        evidence: Dict[str, List[Dict[str, str]]] = {}
        for intent, queries in planner_output.items():
            intent_results: List[Dict[str, str]] = []
            for query in queries:
                results = retriever.search(query, top_k=top_k)
                if results:
                    intent_results.append(results[0])
            if intent_results:
                evidence[intent] = intent_results
        return evidence
