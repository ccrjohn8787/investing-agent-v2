"""Delta engine for quarter-over-quarter and year-over-year comparisons."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

from hybrid_agent.calculators.utils import safe_div
from hybrid_agent.models import CompanyQuarter
from .store import DeltaStore


class DeltaEngine:
    KEY_METRICS = {
        "Revenue": ("income_stmt", "Revenue"),
        "Gross Profit": ("income_stmt", "GrossProfit"),
        "EBIT": ("income_stmt", "EBIT"),
        "CFO": ("cash_flow", "CFO"),
        "FCF": ("cash_flow", "FCF"),
    }

    DERIVED_METRICS: Dict[str, Callable[[CompanyQuarter], Optional[float]]] = {
        "Owner Earnings": lambda quarter: DeltaEngine._owner_earnings(quarter),
        "Net Debt": lambda quarter: DeltaEngine._net_debt(quarter),
        "Accruals Ratio": lambda quarter: DeltaEngine._accruals_ratio(quarter),
        "Accounts Receivable": lambda quarter: DeltaEngine._get(quarter, "balance_sheet", "AccountsReceivable"),
        "Inventory": lambda quarter: DeltaEngine._get(quarter, "balance_sheet", "Inventory"),
        "Shares Diluted": lambda quarter: DeltaEngine._shares_diluted(quarter),
    }

    def __init__(self, store: Optional[DeltaStore] = None) -> None:
        self._store = store or DeltaStore()

    def compute(
        self,
        current: CompanyQuarter,
        prior: CompanyQuarter,
        year_ago: CompanyQuarter,
    ) -> Dict[str, Dict[str, float]]:
        deltas: Dict[str, Dict[str, float]] = {}
        for name, (section, key) in self.KEY_METRICS.items():
            snapshot = self._build_record(
                name,
                getattr(current, section).get(key),
                getattr(prior, section).get(key),
                getattr(year_ago, section).get(key),
            )
            if snapshot:
                deltas[name] = snapshot

        for name, extractor in self.DERIVED_METRICS.items():
            snapshot = self._build_record(
                name,
                extractor(current),
                extractor(prior),
                extractor(year_ago),
            )
            if snapshot:
                deltas[name] = snapshot
        ticker = current.ticker.upper()
        self._store.save(ticker, deltas)
        return deltas

    def fetch(self, ticker: str) -> Dict[str, Dict[str, float]]:
        return self._store.fetch(ticker)

    @staticmethod
    def _build_record(name: str, current: Optional[float], prior: Optional[float], year_ago: Optional[float]) -> Optional[Dict[str, float]]:
        if current is None or prior is None or year_ago is None:
            return None
        qoq = current - prior
        yoy = current - year_ago
        qoq_percent = safe_div(qoq, prior if prior != 0 else None)
        yoy_percent = safe_div(yoy, year_ago if year_ago != 0 else None)
        return {
            "current": current,
            "qoq": qoq,
            "yoy": yoy,
            "qoq_percent": qoq_percent if qoq_percent is not None else 0.0,
            "yoy_percent": yoy_percent if yoy_percent is not None else 0.0,
        }

    @staticmethod
    def _get(quarter: CompanyQuarter, section: str, key: str) -> Optional[float]:
        container = getattr(quarter, section, {})
        return container.get(key)

    @staticmethod
    def _owner_earnings(quarter: CompanyQuarter) -> Optional[float]:
        cfo = quarter.cash_flow.get("CFO")
        capex = quarter.cash_flow.get("CapEx")
        if cfo is None:
            return None
        if capex is None:
            return cfo
        return cfo + capex

    @staticmethod
    def _net_debt(quarter: CompanyQuarter) -> Optional[float]:
        debt = quarter.balance_sheet.get("TotalDebt")
        cash = quarter.balance_sheet.get("Cash")
        if debt is None and cash is None:
            return None
        debt = debt or 0.0
        cash = cash or 0.0
        return debt - cash

    @staticmethod
    def _accruals_ratio(quarter: CompanyQuarter) -> Optional[float]:
        net_income = quarter.income_stmt.get("NetIncome")
        cfo = quarter.cash_flow.get("CFO")
        total_assets = quarter.balance_sheet.get("TotalAssets")
        if net_income is None or cfo is None or total_assets in (None, 0):
            return None
        return safe_div(net_income - cfo, total_assets)

    @staticmethod
    def _shares_diluted(quarter: CompanyQuarter) -> Optional[float]:
        metadata = quarter.metadata or {}
        valuation = metadata.get("valuation") if isinstance(metadata, dict) else None
        if isinstance(valuation, dict):
            shares = valuation.get("shares_diluted")
            if shares is not None:
                return float(shares)
        # fallback to metadata.ttm if present
        ttm = metadata.get("ttm") if isinstance(metadata, dict) else None
        if isinstance(ttm, dict):
            shares = ttm.get("SharesDiluted")
            if shares is not None:
                return float(shares)
        return None
