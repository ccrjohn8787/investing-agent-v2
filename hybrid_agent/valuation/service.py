"""Utilities for assembling deterministic valuation bundles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from hybrid_agent.calculators import dcf
from hybrid_agent.models import CompanyQuarter
from hybrid_agent.valuation.wacc import WACCCalculator, WACCInputs, WACCResult


@dataclass
class ValuationBundle:
    """Deterministic valuation outputs used by the analyst fallback."""

    inputs: WACCInputs
    wacc: WACCResult
    terminal_growth: float
    terminal_inputs: Dict[str, float]
    hurdle: float
    hurdle_details: Dict[str, float | str]
    irr_analysis: dcf.IRRAnalysis
    fcf_paths: Dict[str, Tuple[float, ...]]
    price: float
    shares: float
    net_debt: float
    ttm_fcf: Optional[float]
    notes: str


class ValuationBuilder:
    """Builds a :class:`ValuationBundle` from quarter metadata."""

    def __init__(self) -> None:
        self._wacc_calculator = WACCCalculator()

    def build(self, quarter: CompanyQuarter) -> Optional[ValuationBundle]:
        meta = quarter.metadata.get("valuation") if isinstance(quarter.metadata, dict) else None
        if not isinstance(meta, dict):
            return None

        try:
            inputs = self._wacc_inputs(meta)
        except ValueError:
            return None

        wacc_result = self._wacc_calculator.derive(inputs)

        terminal_inputs = self._terminal_inputs(meta)
        terminal_growth = self._terminal_growth(terminal_inputs, wacc_result.point)

        hurdle_details = self._hurdle_details(meta)
        hurdle_value = self._compute_hurdle(hurdle_details)

        pricing = self._pricing_inputs(meta, quarter)
        if pricing is None:
            return None
        price, shares, net_debt = pricing

        try:
            fcf_paths = self._fcf_paths(meta)
        except ValueError:
            return None

        base_path = fcf_paths.get("Base")
        if base_path is None:
            return None

        scenario_inputs = {k: list(v) for k, v in fcf_paths.items() if k != "Base"}
        irr_analysis = dcf.run_irr_analysis(
            price=price,
            shares=shares,
            net_debt=net_debt,
            wacc=wacc_result.point,
            terminal_g=terminal_growth,
            fcf_path=list(base_path),
            scenarios=scenario_inputs if scenario_inputs else None,
        )

        ttm = {}
        if isinstance(quarter.metadata, dict):
            ttm_meta = quarter.metadata.get("ttm")
            if isinstance(ttm_meta, dict):
                ttm = ttm_meta
        ttm_fcf = self._safe_float(ttm.get("FCF"))

        notes = str(meta.get("notes", ""))

        return ValuationBundle(
            inputs=inputs,
            wacc=wacc_result,
            terminal_growth=terminal_growth,
            terminal_inputs=terminal_inputs,
            hurdle=hurdle_value,
            hurdle_details=hurdle_details,
            irr_analysis=irr_analysis,
            fcf_paths=fcf_paths,
            price=price,
            shares=shares,
            net_debt=net_debt,
            ttm_fcf=ttm_fcf,
            notes=notes,
        )

    # ------------------------------------------------------------------
    def _wacc_inputs(self, meta: Dict[str, object]) -> WACCInputs:
        try:
            rf = self._safe_float(meta["risk_free_rate"], required=True)
            erp = self._safe_float(meta["equity_risk_premium"], required=True)
            beta = self._safe_float(meta["beta"], required=True)
            rd = self._safe_float(meta["cost_of_debt"], required=True)
            tax = self._safe_float(meta["tax_rate"], required=True)
            equity_value = self._safe_float(meta["market_equity_value"], required=True)
            debt_value = self._safe_float(meta["market_debt_value"], required=True)
            adjustment = self._safe_float(meta.get("equity_adjustment_bps", 0.0))
        except KeyError as exc:  # defensive guard for required keys
            raise ValueError(f"missing valuation input: {exc}") from exc

        return WACCInputs(
            risk_free_rate=rf,
            equity_risk_premium=erp,
            beta=beta,
            cost_of_debt=rd,
            tax_rate=tax,
            market_equity_value=equity_value,
            market_debt_value=debt_value,
            equity_adjustment_bps=adjustment,
        )

    def _terminal_inputs(self, meta: Dict[str, object]) -> Dict[str, float]:
        raw = meta.get("terminal_inputs")
        if not isinstance(raw, dict):
            return {"inflation": 0.02, "real_gdp": 0.01}
        inflation = self._safe_float(raw.get("inflation"), default=0.02)
        gdp = self._safe_float(raw.get("real_gdp"), default=0.01)
        return {"inflation": inflation, "real_gdp": gdp}

    def _terminal_growth(self, inputs: Dict[str, float], wacc_point: float) -> float:
        baseline = inputs.get("inflation", 0.02) + inputs.get("real_gdp", 0.01)
        capped = min(baseline, max(wacc_point - 0.005, 0.0))
        return capped

    def _hurdle_details(self, meta: Dict[str, object]) -> Dict[str, float | str]:
        raw = meta.get("hurdle")
        if not isinstance(raw, dict):
            return {"base": 0.15, "adjustment_bps": 0.0, "rationale": "Base policy (15%)."}
        base = self._safe_float(raw.get("base"), default=0.15)
        adjustment = self._safe_float(raw.get("adjustment_bps"), default=0.0)
        rationale = str(raw.get("rationale", "Deterministic hurdle policy."))
        return {"base": base, "adjustment_bps": adjustment, "rationale": rationale}

    def _compute_hurdle(self, details: Dict[str, float | str]) -> float:
        base = self._safe_float(details.get("base"), default=0.15)
        adjustment_bps = self._safe_float(details.get("adjustment_bps"), default=0.0)
        return max(base + adjustment_bps / 10_000.0, 0.0)

    def _pricing_inputs(
        self,
        meta: Dict[str, object],
        quarter: CompanyQuarter,
    ) -> Optional[Tuple[float, float, float]]:
        price = self._safe_float(meta.get("share_price"))
        shares = self._safe_float(meta.get("shares_diluted"))
        net_debt = self._safe_float(meta.get("net_debt"))
        if net_debt is None:
            debt = self._safe_float(quarter.balance_sheet.get("TotalDebt"), default=0.0)
            cash = self._safe_float(quarter.balance_sheet.get("Cash"), default=0.0)
            net_debt = debt - cash
        if price is None or shares is None or net_debt is None:
            return None
        return price, shares, net_debt

    def _fcf_paths(self, meta: Dict[str, object]) -> Dict[str, Tuple[float, ...]]:
        raw_paths = meta.get("fcf_paths")
        if not isinstance(raw_paths, dict):
            raise ValueError("valuation metadata missing fcf_paths")
        results: Dict[str, Tuple[float, ...]] = {}
        for name, values in raw_paths.items():
            if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
                raise ValueError("fcf path must be iterable")
            converted = tuple(float(v) for v in values)
            if len(converted) == 0:
                raise ValueError("fcf path cannot be empty")
            results[name] = converted
        return results

    # ------------------------------------------------------------------
    def _safe_float(
        self,
        value: object,
        *,
        default: Optional[float] = None,
        required: bool = False,
    ) -> Optional[float]:
        if value is None:
            if required:
                raise ValueError("required float missing")
            return default
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            if required:
                raise ValueError("invalid float value") from exc
            return default
