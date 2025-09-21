"""Deterministic Stage-0 gate builder and path selection."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence

from hybrid_agent.models import CompanyQuarter, GateRow, Metric


@dataclass
class PathDecision:
    path: str
    reasons: List[str]


class StageZeroBuilder:
    def __init__(self, *, flip_trigger_horizon_days: int = 90) -> None:
        self._flip_trigger_horizon = flip_trigger_horizon_days

    def build(
        self,
        metrics: List[Metric],
        metadata: Dict[str, object],
        path: str,
    ) -> Dict[str, List[GateRow]]:
        metric_map = {metric.name: metric for metric in metrics}
        ttm = metadata.get("ttm", {}) if isinstance(metadata.get("ttm"), dict) else {}

        hard_gates = [
            self._circle_of_competence(metric_map, ttm),
            self._fraud_controls(metric_map),
            self._imminent_solvency(metric_map, ttm),
            self._valuation(metric_map),
            self._final_gate(path),
        ]

        soft_gates = [
            self._accounting_sanity(metric_map),
            self._balance_sheet_survival(metric_map, ttm),
            self._unit_economics(metric_map),
            self._industry(),
            self._moat(metric_map),
            self._management(),
        ]

        return {
            "hard": hard_gates,
            "soft": soft_gates,
        }

    # Hard gates -----------------------------------------------------------

    def _circle_of_competence(self, metrics: Dict[str, Metric], ttm: Dict[str, float]) -> GateRow:
        revenue = self._metric_value(metrics, "Revenue") or ttm.get("Revenue")
        result = "Pass" if revenue and revenue > 0 else "Fail"
        return GateRow(
            gate="Circle of Competence",
            hard_or_soft="Hard",
            what_it_means="Disclosures sufficient for analysis",
            metrics_sources=[self._source(metrics.get("Revenue"))],
            pass_rule="Revenue > 0 and segment disclosure present",
            result=result,
        )

    def _fraud_controls(self, metrics: Dict[str, Metric]) -> GateRow:
        accruals = self._metric_value(metrics, "Accruals Ratio")
        result = "Pass" if accruals is not None and -0.1 <= accruals <= 0.1 else "Fail"
        return GateRow(
            gate="Fraud/Controls",
            hard_or_soft="Hard",
            what_it_means="Accruals within healthy bounds",
            metrics_sources=[self._source(metrics.get("Accruals Ratio"))],
            pass_rule="Accruals ratio within +/-10%",
            result=result,
        )

    def _imminent_solvency(self, metrics: Dict[str, Metric], ttm: Dict[str, float]) -> GateRow:
        net_leverage = self._metric_value(metrics, "Net Debt / EBITDA")
        fcf = ttm.get("FCF")
        passes = False
        if net_leverage is not None and net_leverage <= 4:
            passes = True
        if fcf is not None and fcf > 0:
            passes = True
        result = "Pass" if passes else "Fail"
        return GateRow(
            gate="Imminent Solvency",
            hard_or_soft="Hard",
            what_it_means="Company can service near-term obligations",
            metrics_sources=[self._source(metrics.get("Net Debt / EBITDA"))],
            pass_rule="Net leverage <=4x or TTM FCF > 0",
            result=result,
        )

    def _valuation(self, metrics: Dict[str, Metric]) -> GateRow:
        roic = self._metric_value(metrics, "ROIC")
        wacc_point = self._metric_value(metrics, "WACC-point")
        passes = roic is not None and wacc_point is not None and roic >= wacc_point
        result = "Pass" if passes else "Fail"
        return GateRow(
            gate="Valuation",
            hard_or_soft="Hard",
            what_it_means="Returns exceed cost of capital",
            metrics_sources=[self._source(metrics.get("ROIC")), self._source(metrics.get("WACC-point"))],
            pass_rule="ROIC >= WACC",
            result=result,
        )

    def _final_gate(self, path: str) -> GateRow:
        result = "Pass" if path == "Mature" else "Fail"
        return GateRow(
            gate="Final Decision Gate",
            hard_or_soft="Hard",
            what_it_means="All hard gates satisfied and business classified as Mature",
            metrics_sources=[],
            pass_rule="Path = Mature and prior hard gates pass",
            result=result,
        )

    # Soft gates -----------------------------------------------------------

    def _accounting_sanity(self, metrics: Dict[str, Metric]) -> GateRow:
        accruals = self._metric_value(metrics, "Accruals Ratio")
        result = "Pass" if accruals is not None and abs(accruals) <= 0.15 else "Soft-Pass"
        flip = None
        if result == "Soft-Pass":
            flip = self._flip_trigger("Track accrual trend vs peers")
        return GateRow(
            gate="Accounting Sanity",
            hard_or_soft="Soft",
            what_it_means="Earnings quality remains solid",
            metrics_sources=[self._source(metrics.get("Accruals Ratio"))],
            pass_rule="Accruals ratio within +/-15%",
            result=result,
            flip_trigger=flip,
        )

    def _balance_sheet_survival(self, metrics: Dict[str, Metric], ttm: Dict[str, float]) -> GateRow:
        cash = ttm.get("Cash")
        fcf = ttm.get("FCF")
        result = "Pass" if cash and cash > 0 and fcf and fcf > 0 else "Soft-Pass"
        flip = None
        if result == "Soft-Pass":
            flip = self._flip_trigger("Refresh liquidity plan; monitor FCF")
        return GateRow(
            gate="Balance-sheet Survival",
            hard_or_soft="Soft",
            what_it_means="Liquidity runway supports thesis",
            metrics_sources=[self._source(metrics.get("FCF"))],
            pass_rule="Positive cash and FCF",
            result=result,
            flip_trigger=flip,
        )

    def _unit_economics(self, metrics: Dict[str, Metric]) -> GateRow:
        take_rate = self._metric_value(metrics, "Take Rate")
        result = "Pass" if take_rate and take_rate > 0.1 else "Soft-Pass"
        flip = None
        if result == "Soft-Pass":
            flip = self._flip_trigger("Revisit unit economics vs plan")
        return GateRow(
            gate="Unit Economics",
            hard_or_soft="Soft",
            what_it_means="Contribution margins support scale",
            metrics_sources=[self._source(metrics.get("Take Rate"))],
            pass_rule="Take rate >10%",
            result=result,
            flip_trigger=flip,
        )

    def _industry(self) -> GateRow:
        return GateRow(
            gate="Industry",
            hard_or_soft="Soft",
            what_it_means="Industry structure remains attractive",
            metrics_sources=[],
            pass_rule="Industry TAM and competition remain favorable",
            result="Soft-Pass",
            flip_trigger=self._flip_trigger("Refresh TAM & competitive notes"),
        )

    def _moat(self, metrics: Dict[str, Metric]) -> GateRow:
        return GateRow(
            gate="Moat",
            hard_or_soft="Soft",
            what_it_means="Defensible competitive advantages",
            metrics_sources=[self._source(metrics.get("Pricing Power"))],
            pass_rule="Evidence of moat remains intact",
            result="Soft-Pass",
            flip_trigger=self._flip_trigger("Review pricing power evidence"),
        )

    def _management(self) -> GateRow:
        return GateRow(
            gate="Management",
            hard_or_soft="Soft",
            what_it_means="Execution and governance remain strong",
            metrics_sources=[],
            pass_rule="No new governance concerns",
            result="Soft-Pass",
            flip_trigger=self._flip_trigger("Check governance disclosures"),
        )

    # Helpers --------------------------------------------------------------

    def _metric_value(self, metrics: Dict[str, Metric], name: str) -> Optional[float]:
        metric = metrics.get(name)
        if metric and isinstance(metric.value, (int, float)):
            return float(metric.value)
        return None

    def _source(self, metric: Optional[Metric]) -> str:
        if not metric:
            return "n/a"
        parts = [metric.source_doc_id, metric.page_or_section, str(metric.url)]
        return " | ".join(filter(None, parts))

    def _flip_trigger(self, description: str) -> str:
        due_date = date.today() + timedelta(days=self._flip_trigger_horizon)
        return f"{description} — due {due_date.isoformat()}"


def determine_path(current: CompanyQuarter, history: Sequence[CompanyQuarter]) -> PathDecision:
    metadata = current.metadata
    ttm = metadata.get("ttm", {}) if isinstance(metadata.get("ttm"), dict) else {}

    failures: List[str] = []
    fcf = ttm.get("FCF")
    if fcf is None or fcf <= 0:
        failures.append("TTM FCF <= 0")

    ebit = ttm.get("EBIT")
    if ebit is None or ebit <= 0:
        failures.append("TTM EBIT <= 0")

    net_debt = current.balance_sheet.get("TotalDebt", 0.0) - current.balance_sheet.get("Cash", 0.0)
    ebitda = ebit if ebit is not None else 0.0
    leverage_ok = False
    if ebitda and ebitda > 0:
        leverage = net_debt / ebitda
        leverage_ok = leverage <= 1.0 or net_debt <= 0
    if not leverage_ok:
        failures.append("Net leverage >1x or net debt positive")

    if len(history) < 8 or any(len(q.segments or {}) == 0 for q in history[-8:]):
        failures.append("Segment disclosure < 8 quarters")

    path = "Mature" if not failures else "Emergent"
    return PathDecision(path=path, reasons=failures)
