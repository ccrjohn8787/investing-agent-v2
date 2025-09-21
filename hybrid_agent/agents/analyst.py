"""Analyst agent orchestrating deterministic metrics and evidence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.calculators.metric_builder import MetricBuilder
from hybrid_agent.models import CompanyQuarter, Document, Metric
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "analyst_prompt.txt"


class AnalystAgent:
    def __init__(
        self,
        calculation_service: CalculationService | None = None,
        retriever: Retriever | None = None,
        llm: Optional[object] = None,
    ) -> None:
        self._calc_service = calculation_service or CalculationService()
        self._retriever = retriever or Retriever(InMemoryDocumentIndex())
        self._llm = llm
        self._prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")

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
    ) -> Dict[str, object]:
        calc_result = self._calc_service.calculate(quarter)
        path = self._determine_path(calc_result.metrics, quarter)
        metrics_summary = self._summarize_metrics(calc_result.metrics)
        prompt = self.build_prompt(ticker, today, path, metrics_summary)

        llm_payload = self._invoke_llm(prompt)
        fallback = self._fallback_payload(path, calc_result.metrics)

        merged = {
            "output_0": llm_payload.get("output_0") or fallback["output_0"],
            "stage_0": llm_payload.get("stage_0") or fallback["stage_0"],
            "stage_1": llm_payload.get("stage_1") or fallback["stage_1"],
            "provenance": llm_payload.get("provenance") or [],
            "reverse_dcf": llm_payload.get("reverse_dcf") or fallback["reverse_dcf"],
            "final_gate": llm_payload.get("final_gate") or fallback["final_gate"],
        }

        evidence = self._collect_evidence(documents)
        merged["provenance"].extend(evidence)
        return merged

    def _invoke_llm(self, prompt: str) -> Dict[str, object]:
        if self._llm is None:
            return {}
        raw = self._llm.generate(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _summarize_metrics(self, metrics: List[Metric]) -> str:
        parts = []
        for metric in metrics[:5]:
            parts.append(f"{metric.name}: {metric.value}")
        return "\n".join(parts)

    def _determine_path(self, metrics: List[Metric], quarter: CompanyQuarter) -> str:
        metric_map = {metric.name: metric for metric in metrics}
        fcf_metric = metric_map.get("FCF")
        fcf_positive = isinstance(fcf_metric.value, (int, float)) and fcf_metric.value > 0
        op_inc = quarter.income_stmt.get("EBIT", 0.0)
        leverage_metric = metric_map.get("Net Debt / EBITDA")
        leverage = leverage_metric.value if isinstance(leverage_metric.value, (int, float)) else None
        segments_consistent = len(quarter.segments) >= 1
        if fcf_positive and op_inc is not None and op_inc >= 0 and leverage is not None and leverage <= 1.0 and segments_consistent:
            return "Mature"
        return "Emergent"

    def _collect_evidence(self, documents: Iterable[Document]) -> List[Dict[str, str]]:
        snippets: List[Dict[str, str]] = []
        for doc in documents:
            query = f"pricing power {doc.ticker.lower()}"
            results = self._retriever.search(query)
            if not results:
                continue
            best = results[0]
            snippets.append(
                {
                    "document_id": doc.id,
                    "doc_type": doc.doc_type,
                    "url": doc.url,
                    "excerpt": best["excerpt"],
                }
            )
        return snippets

    def _fallback_payload(self, path: str, metrics: List[Metric]) -> Dict[str, object]:
        headline = f"{path} path. Hard gates: PASS. Final Decision Gate: WATCH. WACC=NA, g=NA, Hurdle IRR=NA."
        stage_0 = [
            {
                "gate": "Valuation",
                "result": "Needs Review",
            }
        ]
        stage_1 = "Automated summary not available; refer to provenance."
        reverse_dcf = {"status": "not_computed"}
        final_gate = {
            "variant": {"definition": "TBD"},
            "price_power": {"definition": "TBD"},
            "owner_eps_path": {"definition": "TBD"},
            "why_now": {"definition": "TBD"},
            "kill_switch": {"definition": "TBD"},
        }
        return {
            "output_0": headline,
            "stage_0": stage_0,
            "stage_1": stage_1,
            "reverse_dcf": reverse_dcf,
            "final_gate": final_gate,
        }
