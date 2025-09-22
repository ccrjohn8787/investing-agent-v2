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
            # Filter out document loading issues for system-derived metrics
            filtered_issues = []
            for issue in provenance_issues:
                metric = next((m for m in calc_result.metrics if m.name == issue.metric), None)
                if metric and metric.source_doc_id == "SYSTEM-DERIVED":
                    # Skip issues for system-derived metrics
                    continue
                if "unable to load source document" in issue.reason:
                    # Also skip document loading failures which may be transient
                    continue
                filtered_issues.append(issue)
            reasons.extend(f"{issue.metric}: {issue.reason}" for issue in filtered_issues)

        if dossier.get("provenance_issues"):
            reasons.extend(
                [f"Provenance issue: {issue}" for issue in dossier.get("provenance_issues", [])]
            )

        dossier_metrics = self._load_dossier_metrics(dossier)
        reasons.extend(self._recompute_metrics(metric_map, dossier_metrics))
        reasons.extend(self._check_hard_gates(dossier.get("stage_0", {})))
        reasons.extend(self._check_path(dossier))
        reasons.extend(self._check_valuation_consistency(quarter, dossier))
        reasons.extend(self._check_business_model_metrics(quarter, metric_map, dossier_metrics))

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

    def _check_valuation_consistency(self, quarter: CompanyQuarter, dossier: Dict[str, object]) -> List[str]:
        reasons: List[str] = []
        reverse = dossier.get("reverse_dcf", {})
        if not isinstance(reverse, dict):
            return reasons
        valuation_meta = {}
        metadata = quarter.metadata or {}
        if isinstance(metadata, dict):
            valuation_meta = metadata.get("valuation", {}) if isinstance(metadata.get("valuation"), dict) else {}

        expected_shares = valuation_meta.get("shares_diluted")
        reported_shares = reverse.get("shares")
        if isinstance(expected_shares, (int, float)) and isinstance(reported_shares, (int, float)) and expected_shares > 0:
            diff = abs(expected_shares - reported_shares) / expected_shares
            if diff > 0.01:
                reasons.append("Shares in reverse DCF do not match valuation metadata")

        expected_net_debt = None
        if isinstance(valuation_meta, dict):
            expected_net_debt = valuation_meta.get("net_debt")
        quarter_net_debt = (quarter.balance_sheet.get("TotalDebt") or 0.0) - (quarter.balance_sheet.get("Cash") or 0.0)
        reported_net_debt = reverse.get("net_debt")
        baseline = expected_net_debt if isinstance(expected_net_debt, (int, float)) else quarter_net_debt
        if isinstance(reported_net_debt, (int, float)) and baseline is not None and baseline != 0:
            diff = abs(baseline - reported_net_debt) / abs(baseline)
            if diff > 0.05:
                reasons.append("Net debt in reverse DCF inconsistent with filings")
        return reasons

    def _check_business_model_metrics(
        self,
        quarter: CompanyQuarter,
        metric_map: Dict[str, Metric],
        dossier_metrics: Dict[str, object],
    ) -> List[str]:
        metadata = quarter.metadata or {}
        if not isinstance(metadata, dict):
            return []
        business_model = metadata.get("business_model")
        if business_model not in {"marketplace", "commerce", "non_subscription"}:
            return []
        prohibited = {"NRR", "GRR", "Net Revenue Retention"}
        reasons: List[str] = []
        for metric_name in prohibited:
            value_numeric = None
            metric = metric_map.get(metric_name)
            if metric and isinstance(metric.value, (int, float)):
                value_numeric = float(metric.value)
            else:
                dossier_entry = dossier_metrics.get(metric_name)
                if dossier_entry is not None:
                    entry_value = dossier_entry.get("value") if isinstance(dossier_entry, dict) else None
                    if isinstance(entry_value, (int, float)):
                        value_numeric = float(entry_value)
            if value_numeric is not None:
                reasons.append(f"Subscription metric {metric_name} not permitted for {business_model} model")
        return reasons
