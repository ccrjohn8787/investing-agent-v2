"""Verifier agent applying QA rules to analyst dossiers."""
from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import CompanyQuarter, QAResult, Metric
from hybrid_agent.provenance.validator import ProvenanceValidator

_ALLOWED_DOC_TYPES = {"10-K", "20-F", "10-Q", "6-K", "8-K", "Proxy", "IR-Deck", "Transcript"}
_HARD_GATES = {
    "Circle of Competence",
    "Fraud/Controls",
    "Imminent Solvency",
    "Valuation",
    "Final Decision Gate",
}


class VerifierAgent:
    def __init__(
        self,
        calculation_service: CalculationService,
        document_store: Optional[DocumentStore] = None,
        sample_size: int = 5,
        rng_seed: int = 42,
    ) -> None:
        self._calculation_service = calculation_service
        self._validator = ProvenanceValidator(document_store) if document_store else None
        self._sample_size = sample_size
        self._rng = random.Random(rng_seed)

    def verify(
        self,
        quarter: CompanyQuarter,
        dossier: Dict[str, object],
        history: Optional[List[CompanyQuarter]] = None,
    ) -> QAResult:
        reasons: List[str] = []
        calc_result = self._calculation_service.calculate(quarter, history or [])
        metric_map = {metric.name: metric for metric in calc_result.metrics}

        if self._validator:
            provenance_issues = self._validator.validate_metrics(calc_result.metrics)
            reasons.extend(f"{issue.metric}: {issue.reason}" for issue in provenance_issues)

        if dossier.get("provenance_issues"):
            reasons.extend(
                [f"Provenance issue: {issue}" for issue in dossier.get("provenance_issues", [])]
            )

        dossier_metrics = self._load_dossier_metrics(dossier)
        reasons.extend(self._recompute_metrics(metric_map, dossier_metrics))
        reasons.extend(self._check_hard_gates(dossier.get("stage_0", {})))
        reasons.extend(self._check_path(dossier))

        if reasons:
            return QAResult(status="BLOCKER", reasons=reasons)
        return QAResult(status="PASS", reasons=[])

    def _load_dossier_metrics(self, dossier: Dict[str, object]) -> Dict[str, object]:
        entries = dossier.get("metrics") or dossier.get("provenance", [])
        mapping: Dict[str, object] = {}
        for entry in entries:
            name = entry.get("metric") or entry.get("name")
            if name:
                mapping[name] = entry
        return mapping

    def _recompute_metrics(
        self,
        metric_map: Dict[str, Metric],
        dossier_metrics: Dict[str, object],
    ) -> List[str]:
        numeric_metrics = [m for m in metric_map.values() if isinstance(m.value, (int, float))]
        sample = numeric_metrics[: self._sample_size]
        reasons: List[str] = []
        for metric in sample:
            entry = dossier_metrics.get(metric.name)
            if not entry:
                reasons.append(f"Metric {metric.name} missing from dossier")
                continue
            value = entry.get("value")
            if not isinstance(value, (int, float)):
                reasons.append(f"Metric {metric.name} value not numeric in dossier")
                continue
            expected = float(metric.value)
            diff = abs(expected - value)
            if expected == 0:
                ratio = diff
            else:
                ratio = diff / abs(expected)
            if ratio > 0.01:
                reasons.append(f"Metric mismatch for {metric.name}")
        return reasons

    def _check_hard_gates(self, stage0: Dict[str, List[Dict[str, object]]]) -> List[str]:
        rows = stage0.get("hard", []) if isinstance(stage0, dict) else stage0
        seen = {row.get("gate"): row.get("result") for row in rows if isinstance(row, dict)}
        reasons = []
        for gate in _HARD_GATES:
            result = seen.get(gate)
            if result is None:
                reasons.append(f"Missing hard gate: {gate}")
            elif result not in {"Pass", "PASS"}:
                reasons.append(f"Hard gate failed: {gate}")
        return reasons

    def _check_path(self, dossier: Dict[str, object]) -> List[str]:
        reasons: List[str] = []
        path_reasons = dossier.get("path_reasons", [])
        output = dossier.get("output_0", "")
        if "Mature" in output and path_reasons:
            reasons.append("Path marked Mature but reasons list not empty")
        return reasons
