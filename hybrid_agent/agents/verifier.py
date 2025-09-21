"""Verifier agent applying QA rules to analyst dossiers."""
from __future__ import annotations

from typing import Dict, Iterable, List

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.models import CompanyQuarter, QAResult

_ALLOWED_DOC_TYPES = {"10-K", "20-F", "10-Q", "6-K", "8-K", "Proxy", "IR-Deck", "Transcript"}
_HARD_GATES = {
    "Circle of Competence",
    "Fraud/Controls",
    "Imminent Solvency",
    "Valuation",
    "Final Decision Gate",
}


class VerifierAgent:
    def __init__(self, calculation_service: CalculationService) -> None:
        self._calculation_service = calculation_service

    def verify(self, quarter: CompanyQuarter, dossier: Dict[str, object]) -> QAResult:
        reasons: List[str] = []
        calc_result = self._calculation_service.calculate(quarter)
        metric_map = {metric.name: metric for metric in calc_result.metrics}

        provenance_entries = dossier.get("provenance", [])
        reasons.extend(self._check_sources(provenance_entries))
        reasons.extend(self._check_metric_consistency(provenance_entries, metric_map))
        reasons.extend(self._check_hard_gates(dossier.get("stage_0", [])))

        if reasons:
            return QAResult(status="BLOCKER", reasons=reasons)
        return QAResult(status="PASS", reasons=[])

    def _check_sources(self, provenance_entries: Iterable[Dict[str, object]]) -> List[str]:
        reasons: List[str] = []
        for entry in provenance_entries:
            doc_type = str(entry.get("doc_type", ""))
            if doc_type not in _ALLOWED_DOC_TYPES:
                reasons.append(f"Non-primary source detected: {doc_type}")
        return reasons

    def _check_metric_consistency(
        self,
        provenance_entries: Iterable[Dict[str, object]],
        metric_map: Dict[str, object],
    ) -> List[str]:
        reasons: List[str] = []
        for entry in provenance_entries:
            name = entry.get("metric")
            value = entry.get("value")
            if name not in metric_map:
                continue
            expected = metric_map[name].value
            if not isinstance(expected, (int, float)):
                continue
            if not isinstance(value, (int, float)):
                reasons.append(f"Metric {name} missing numeric value")
                continue
            if expected == 0:
                diff_ratio = abs(value - expected)
            else:
                diff_ratio = abs(value - expected) / abs(expected)
            if diff_ratio > 0.01:
                reasons.append(f"Metric mismatch for {name}")
        return reasons

    def _check_hard_gates(self, gate_rows: Iterable[Dict[str, object]]) -> List[str]:
        seen = {row.get("gate"): row.get("result") for row in gate_rows if isinstance(row, dict)}
        reasons = []
        for gate in _HARD_GATES:
            result = seen.get(gate)
            if result is None:
                reasons.append(f"Missing hard gate: {gate}")
            elif result not in {"Pass", "PASS"}:
                reasons.append(f"Hard gate failed: {gate}")
        return reasons
