"""Analyst agent orchestrating deterministic metrics and evidence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.gates import StageZeroBuilder, determine_path
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import CompanyQuarter, Document, Metric, GateRow
from hybrid_agent.provenance.validator import ProvenanceValidator
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever
from hybrid_agent.rag.planner import RetrievalPlanner
from hybrid_agent.valuation import ValuationBundle
from .llm import LLMClient, DummyLLMClient


class _LegacyLLMAdapter(LLMClient):
    def __init__(self, legacy_llm: object) -> None:
        if not hasattr(legacy_llm, "generate"):
            raise TypeError("legacy llm must implement generate(prompt: str) -> str")
        self._llm = legacy_llm

    def generate(self, prompt: str) -> str:
        return self._llm.generate(prompt)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "analyst_prompt.txt"


class AnalystAgent:
    def __init__(
        self,
        calculation_service: Optional[CalculationService] = None,
        retriever: Optional[Retriever] = None,
        llm: Optional[object] = None,
        llm_client: Optional[LLMClient] = None,
        document_store: Optional[DocumentStore] = None,
    ) -> None:
        self._calc_service = calculation_service or CalculationService()
        self._retriever = retriever or Retriever(InMemoryDocumentIndex())
        self._stage0_builder = StageZeroBuilder()
        if llm_client is not None:
            self._llm_client = llm_client
        elif llm is not None:
            self._llm_client = _LegacyLLMAdapter(llm)
        else:
            self._llm_client = None
        self._llm = llm
        self._prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
        self._planner = RetrievalPlanner()
        self._provenance_validator = ProvenanceValidator(document_store) if document_store else None

    def build_prompt(self, ticker: str, today: str, path: str, metrics_summary: str) -> str:
        return (
            f"{self._prompt_template}\n\n"
            f"Ticker: {ticker}\n"
            f"As of: {today}\n"
            f"Computed path: {path}\n"
            f"Metrics summary:\n{metrics_summary}\n"
        )

    def analyze(
        self,
        ticker: str,
        today: str,
        quarter: CompanyQuarter,
        documents: Iterable[Document],
        history: Optional[List[CompanyQuarter]] = None,
    ) -> Dict[str, object]:
        history = history or []
        calc_result = self._calc_service.calculate(quarter, history)
        normalized_quarter = calc_result.quarter
        normalized_history = calc_result.history
        path_decision = determine_path(normalized_quarter, normalized_history)
        path = path_decision.path
        metrics_summary = self._summarize_metrics(calc_result.metrics)
        prompt = self.build_prompt(ticker, today, path, metrics_summary)

        provenance_issues: List[str] = []
        if self._provenance_validator:
            issues = self._provenance_validator.validate_metrics(calc_result.metrics)
            provenance_issues = [f"{issue.metric}: {issue.reason}" for issue in issues]

        llm_payload = self._invoke_llm(prompt)
        stage0_rows = self._stage0_builder.build(
            calc_result.metrics,
            normalized_quarter.metadata,
            path,
        )
        evidence = self._collect_evidence(documents, normalized_quarter, path)
        self._attach_stage0_evidence(stage0_rows, evidence)
        stage0_payload = {key: [row.model_dump() for row in rows] for key, rows in stage0_rows.items()}
        metrics_payload = [self._metric_payload(metric) for metric in calc_result.metrics]
        fallback = self._fallback_payload(
            path,
            calc_result.metrics,
            stage0_payload,
            metrics_payload,
            calc_result.valuation,
        )

        merged = {
            "output_0": llm_payload.get("output_0") or fallback["output_0"],
            "stage_0": llm_payload.get("stage_0") or fallback["stage_0"],
            "stage_1": llm_payload.get("stage_1") or fallback["stage_1"],
            "provenance": llm_payload.get("provenance") or [],
            "metrics": metrics_payload,
            "reverse_dcf": llm_payload.get("reverse_dcf") or fallback["reverse_dcf"],
            "final_gate": llm_payload.get("final_gate") or fallback["final_gate"],
            "path_reasons": path_decision.reasons,
            "provenance_issues": provenance_issues,
        }

        merged.setdefault("provenance", []).extend(evidence)
        merged["evidence"] = evidence
        return merged

    def _invoke_llm(self, prompt: str) -> Dict[str, object]:
        client = self._llm_client
        if client is None:
            return {}
        raw = client.generate(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _summarize_metrics(self, metrics: List[Metric]) -> str:
        parts = []
        for metric in metrics[:5]:
            parts.append(f"{metric.name}: {metric.value}")
        return "\n".join(parts)

    def _collect_evidence(
        self,
        documents: Iterable[Document],
        quarter: CompanyQuarter,
        path: str,
    ) -> List[Dict[str, str]]:
        planner_output = self._planner.build_queries(quarter, path)
        intent_results = self._planner.top_results(planner_output, self._retriever)
        snippets: List[Dict[str, str]] = []
        for intent, results in intent_results.items():
            for result in results:
                snippets.append({"intent": intent, **result})
        return snippets

    def _attach_stage0_evidence(
        self,
        stage0_rows: Dict[str, List[GateRow]],
        evidence: List[Dict[str, str]],
    ) -> None:
        if not evidence:
            return
        intent_map = {
            "pricing_power": "Moat",
            "kpi_definition": "Accounting Sanity",
            "debt_footnote": "Imminent Solvency",
            "auditor_opinion": "Fraud/Controls",
            "segment_notes": "Circle of Competence",
            "supplier_finance": "Balance-sheet Survival",
        }
        aggregated: Dict[str, List[str]] = {}
        for item in evidence:
            intent = item.get("intent")
            if not intent:
                continue
            gate = intent_map.get(intent)
            if not gate:
                continue
            excerpt = item.get("excerpt") or item.get("text")
            if not excerpt:
                continue
            aggregated.setdefault(gate, []).append(excerpt)

        if not aggregated:
            return

        for bucket in (stage0_rows.get("hard", []), stage0_rows.get("soft", [])):
            for row in bucket:
                snippets = aggregated.get(row.gate)
                if snippets:
                    row.evidence = snippets

    def _fallback_payload(
        self,
        path: str,
        metrics: List[Metric],
        stage0: Dict[str, List[Dict[str, object]]],
        metrics_payload: List[Dict[str, object]],
        valuation: Optional[ValuationBundle],
    ) -> Dict[str, object]:
        metric_map = {metric.name: metric for metric in metrics}

        def numeric(name: str, default: float = 0.0) -> float:
            metric = metric_map.get(name)
            if metric and isinstance(metric.value, (int, float)):
                return float(metric.value)
            return default

        revenue = numeric("Revenue")
        fcf = numeric("FCF")
        roic_value = numeric("ROIC")
        leverage = numeric("Net Debt / EBITDA")

        headline = self._headline(stage0, path, valuation)
        stage_0 = stage0
        stage_1 = self._stage_one_summary(revenue, fcf, roic_value, leverage, valuation)
        reverse_dcf = self._reverse_dcf_payload(valuation, fcf)
        final_gate = self._final_gate_payload(path, valuation)
        return {
            "output_0": headline,
            "stage_0": stage_0,
            "stage_1": stage_1,
            "reverse_dcf": reverse_dcf,
            "final_gate": final_gate,
            "metrics": metrics_payload,
            "provenance": metrics_payload,
            "evidence": [],
        }

    def _headline(
        self,
        stage0: Dict[str, List[Dict[str, object]]],
        path: str,
        valuation: Optional[ValuationBundle],
    ) -> str:
        hard_rows = stage0.get("hard", []) if isinstance(stage0, dict) else []
        hard_pass = all(row.get("result") == "Pass" for row in hard_rows if isinstance(row, dict))
        hard_text = "PASS" if hard_pass else "FAIL"
        final_row = next((row for row in hard_rows if row.get("gate") == "Final Decision Gate"), {})
        final_text = str(final_row.get("result", "WATCH")).upper()
        if valuation:
            wacc_point = valuation.wacc.point
            lower = valuation.wacc.lower
            upper = valuation.wacc.upper
            terminal_g = valuation.terminal_growth
            hurdle = valuation.hurdle
            return (
                f"{path} path. Hard gates: {hard_text}. Final Decision Gate: {final_text}. "
                f"WACC={wacc_point:.1%} ({lower:.1%}–{upper:.1%}), g={terminal_g:.1%}, "
                f"Hurdle IRR={hurdle:.1%}."
            )
        return (
            f"{path} path. Hard gates: {hard_text}. Final Decision Gate: {final_text}. "
            "WACC=NA, g=NA, Hurdle IRR=NA."
        )

    def _stage_one_summary(
        self,
        revenue: float,
        fcf: float,
        roic_value: float,
        leverage: float,
        valuation: Optional[ValuationBundle],
    ) -> str:
        base = (
            "Latest revenue ${:,.0f} with free cash flow ${:,.0f}. ROIC sits at {:.1%} "
            "with net leverage {:.2f}x."
        ).format(revenue, fcf, roic_value, leverage)
        if valuation:
            return (
                f"{base} Deterministic WACC is {valuation.wacc.point:.1%} "
                f"(band {valuation.wacc.lower:.1%}-{valuation.wacc.upper:.1%}); "
                f"terminal growth anchored at {valuation.terminal_growth:.1%} "
                f"with hurdle IRR {valuation.hurdle:.1%}."
            )
        return base + " Valuation inputs unavailable; monitor once market data is loaded."

    def _reverse_dcf_payload(
        self,
        valuation: Optional[ValuationBundle],
        fallback_fcf: float,
    ) -> Dict[str, object]:
        if not valuation:
            growth_cases = {"Bear": 0.0, "Base": 0.0, "Bull": 0.0}
            scenarios = [
                {"name": name, "fcf_path": [0.0] * 5, "irr": None}
                for name in ("Bear", "Base", "Bull")
            ]
            return {
                "wacc": {
                    "point": None,
                    "band": None,
                    "cost_of_equity": None,
                    "cost_of_debt_after_tax": None,
                    "weights": None,
                    "inputs": None,
                },
                "terminal_growth": {"value": None, "inputs": None},
                "hurdle": {"value": None, "details": None},
                "base_irr": None,
                "scenarios": scenarios,
                "sensitivity": {},
                "price": None,
                "shares": None,
                "net_debt": None,
                "ttm_fcf": fallback_fcf,
                "fcf_paths": growth_cases,
                "notes": "Valuation metadata missing; populate to unlock deterministic DCF.",
            }

        irr = valuation.irr_analysis
        scenarios_payload: List[Dict[str, object]] = [
            {
                "name": "Base",
                "fcf_path": list(valuation.fcf_paths.get("Base", ())),
                "irr": irr.irr,
            }
        ]
        for scenario in irr.scenarios:
            scenarios_payload.append(
                {
                    "name": scenario.name,
                    "fcf_path": list(scenario.fcf_path),
                    "irr": scenario.irr,
                }
            )

        return {
            "wacc": {
                "point": valuation.wacc.point,
                "band": [valuation.wacc.lower, valuation.wacc.upper],
                "cost_of_equity": valuation.wacc.cost_of_equity,
                "cost_of_debt_after_tax": valuation.wacc.cost_of_debt_after_tax,
                "weights": valuation.wacc.weights,
                "inputs": valuation.wacc.inputs,
            },
            "terminal_growth": {
                "value": valuation.terminal_growth,
                "inputs": valuation.terminal_inputs,
            },
            "hurdle": {
                "value": valuation.hurdle,
                "details": valuation.hurdle_details,
            },
            "base_irr": irr.irr,
            "scenarios": scenarios_payload,
            "sensitivity": irr.sensitivity,
            "price": valuation.price,
            "shares": valuation.shares,
            "net_debt": valuation.net_debt,
            "ttm_fcf": valuation.ttm_fcf,
            "fcf_paths": {name: list(path) for name, path in valuation.fcf_paths.items()},
            "notes": valuation.notes,
        }

    def _final_gate_payload(
        self,
        path: str,
        valuation: Optional[ValuationBundle],
    ) -> Dict[str, Dict[str, str]]:
        hurdle_text = "Hurdle policy not derived"
        if valuation:
            details = valuation.hurdle_details
            base = details.get("base")
            adj = details.get("adjustment_bps")
            rationale = details.get("rationale", "")
            if isinstance(base, (int, float)):
                base_display = f"{float(base):.1%}"
            else:
                base_display = str(base)
            if isinstance(adj, (int, float)):
                adj_display = f"{float(adj):.0f}"
            else:
                adj_display = str(adj)
            hurdle_text = f"Base {base_display}, adjustment {adj_display} bps. {rationale}"

        return {
            "variant": {
                "definition": "Compare current thesis variant vs. consensus; deterministic fallback summarises path status.",
                "pass_fail": "Pass" if path == "Mature" else "Watch",
                "evidence": "Deterministic calculators only; load LLM analysis for richer narrative.",
            },
            "price_power": {
                "definition": "Review pricing power excerpts from retrieved evidence.",
                "pass_fail": "TBD",
                "evidence": "See evidence intents for pricing power and segment notes.",
            },
            "owner_eps_path": {
                "definition": "Track FCF per share vs. hurdle and reverse-DCF outputs.",
                "pass_fail": "TBD",
                "evidence": "Base/Bull/Bear IRRs available in reverse DCF block.",
            },
            "why_now": {
                "definition": "Reconcile catalyst timing with Stage-0 flip-triggers.",
                "pass_fail": "TBD",
                "evidence": "Soft gate flip-triggers hold the monitoring plan.",
            },
            "kill_switch": {
                "definition": hurdle_text,
                "pass_fail": "TBD",
                "evidence": "Define capital-at-risk exit metric alongside hurdle policy.",
            },
        }

    def _metric_payload(self, metric: Metric) -> Dict[str, object]:
        payload = {
            "metric": metric.name,
            "value": metric.value,
            "unit": metric.unit,
            "period": metric.period,
            "source_doc_id": metric.source_doc_id,
            "page_or_section": metric.page_or_section,
            "quote": metric.quote,
            "url": str(metric.url),
        }
        if metric.metadata:
            payload["metadata"] = metric.metadata
        return payload
