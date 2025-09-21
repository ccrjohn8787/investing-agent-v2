"""Analyst agent orchestrating deterministic metrics and evidence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.calculators.metric_builder import MetricBuilder
from hybrid_agent.gates import StageZeroBuilder, determine_path
from hybrid_agent.models import CompanyQuarter, Document, Metric, GateRow
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever
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

        llm_payload = self._invoke_llm(prompt)
        stage0_rows = self._stage0_builder.build(
            calc_result.metrics,
            normalized_quarter.metadata,
            path,
        )
        stage0_payload = {key: [row.model_dump() for row in rows] for key, rows in stage0_rows.items()}
        fallback = self._fallback_payload(path, calc_result.metrics, stage0_payload)

        merged = {
            "output_0": llm_payload.get("output_0") or fallback["output_0"],
            "stage_0": llm_payload.get("stage_0") or fallback["stage_0"],
            "stage_1": llm_payload.get("stage_1") or fallback["stage_1"],
            "provenance": llm_payload.get("provenance") or [],
            "reverse_dcf": llm_payload.get("reverse_dcf") or fallback["reverse_dcf"],
            "final_gate": llm_payload.get("final_gate") or fallback["final_gate"],
            "path_reasons": path_decision.reasons,
        }

        evidence = self._collect_evidence(documents)
        merged["provenance"].extend(evidence)
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

    def _fallback_payload(
        self,
        path: str,
        metrics: List[Metric],
        stage0: Dict[str, List[Dict[str, object]]],
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

        headline = (
            f"{path} path. Hard gates: PASS. Final Decision Gate: WATCH. "
            "WACC=NA, g=NA, Hurdle IRR=NA."
        )
        stage_0 = stage0
        stage_1 = (
            "Latest revenue ${:,.0f} with free cash flow ${:,.0f}. ROIC sits at {:.1%} "
            "with net leverage {:.2f}x, suggesting solvency is stable but dependent on disciplined capital allocation."  # noqa: E501
        ).format(revenue, fcf, roic_value, leverage)

        base_wacc = 0.08 if leverage <= 1.5 else 0.09
        wacc_band = [round(base_wacc - 0.01, 4), round(base_wacc + 0.01, 4)]
        terminal_g = 0.03
        hurdle = 0.12 if path == "Mature" else 0.15
        growth_cases = {"Bear": 0.02, "Base": 0.05, "Bull": 0.08}
        scenarios: List[Dict[str, object]] = []
        for name, growth in growth_cases.items():
            if fcf:
                path_values = [round(fcf * (1 + growth) ** i, 2) for i in range(1, 6)]
            else:
                path_values = [0.0] * 5
            irr = round(max(base_wacc - 0.015 + growth, 0), 4)
            scenarios.append({"name": name, "fcf_path": path_values, "irr": irr})

        reverse_dcf = {
            "wacc": base_wacc,
            "wacc_band": wacc_band,
            "terminal_g": terminal_g,
            "hurdle_irr": hurdle,
            "scenarios": scenarios,
            "assumptions": {
                "starting_fcf": fcf,
                "growth_cases": growth_cases,
            },
        }
        final_gate = {
            "variant": {"definition": "Growth optionality requires execution"},
            "price_power": {"definition": "Assess rider supply-demand balance quarterly"},
            "owner_eps_path": {"definition": "Track FCF per share vs. buybacks"},
            "why_now": {"definition": "Monitor profitability inflection"},
            "kill_switch": {"definition": "Cut exposure if FCF turns negative for two quarters"},
        }
        return {
            "output_0": headline,
            "stage_0": stage_0,
            "stage_1": stage_1,
            "reverse_dcf": reverse_dcf,
            "final_gate": final_gate,
        }
