"""Builds Metrics from normalized financial statements."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from hybrid_agent.calculators import (
    accruals,
    balance_sheet,
    unit_econ,
    working_capital,
)
from hybrid_agent.calculators.roic import nopat, invested_capital, roic as roic_calc
from hybrid_agent.models import CompanyQuarter, Metric

_SYSTEM_DOC_ID = "SYSTEM-DERIVED"
_SYSTEM_URL = "https://localhost/system"
_SYSTEM_QUOTE = "Derived from normalized statements"


@dataclass
class MetricBuilder:
    period_label: str = "TTM"

    def build(self, quarter: CompanyQuarter) -> List[Metric]:
        metrics: List[Metric] = []
        metrics.append(self._metric_from_value(
            "Revenue",
            quarter.income_stmt.get("Revenue"),
            unit="USD",
            quarter=quarter,
            inputs=None,
        ))
        metrics.append(self._build_fcf(quarter))
        metrics.append(self._build_dso(quarter))
        metrics.append(self._build_dih(quarter))
        metrics.append(self._build_dpo(quarter))
        metrics.append(self._build_ccc(quarter))
        metrics.append(self._build_accruals(quarter))
        metrics.append(self._build_net_leverage(quarter))
        metrics.append(self._build_roic(quarter))
        metrics.append(self._metric_from_value(
            "NRR",
            None,
            unit="ratio",
            quarter=quarter,
            inputs=["subscription_disclosures"],
        ))
        return metrics

    def metric_from_value(
        self,
        name: str,
        value: Optional[float],
        *,
        unit: str,
        quarter: CompanyQuarter,
        inputs: Optional[List[str]],
    ) -> Metric:
        return self._metric_from_value(
            name,
            value,
            unit=unit,
            quarter=quarter,
            inputs=inputs,
        )

    def _metric_from_value(
        self,
        name: str,
        value: Optional[float],
        *,
        unit: str,
        quarter: CompanyQuarter,
        inputs: Optional[List[str]],
    ) -> Metric:
        metric_value: Union[float, str]
        if value is None:
            metric_value = "ABSTAIN"
        else:
            metric_value = value
        source_info = self._lookup_provenance(name, quarter)
        source_doc_id = source_info.get("source_doc_id", _SYSTEM_DOC_ID)
        page_or_section = source_info.get("page_or_section", "n/a")
        quote = source_info.get("quote", _SYSTEM_QUOTE)
        url = source_info.get("url", _SYSTEM_URL)
        return Metric(
            name=name,
            value=metric_value,
            unit=unit,
            period=quarter.period,
            source_doc_id=source_doc_id,
            page_or_section=page_or_section,
            quote=quote,
            url=url,
            inputs=inputs,
            metadata={k: v for k, v in source_info.items() if k not in {"source_doc_id", "page_or_section", "quote", "url"}},
        )

    def _lookup_provenance(self, name: str, quarter: CompanyQuarter) -> Dict[str, object]:
        if not isinstance(quarter.metadata, dict):
            return {}
        provenance_sources = []
        main = quarter.metadata.get("provenance")
        if isinstance(main, dict):
            provenance_sources.append(main)
        valuation_meta = quarter.metadata.get("valuation")
        if isinstance(valuation_meta, dict):
            valuation_prov = valuation_meta.get("provenance")
            if isinstance(valuation_prov, dict):
                provenance_sources.append(valuation_prov)
        for source in provenance_sources:
            info = source.get(name)
            if isinstance(info, dict):
                return info
        return {}

    def _build_fcf(self, quarter: CompanyQuarter) -> Metric:
        fcf = quarter.cash_flow.get("FCF")
        if fcf is None and "CFO" in quarter.cash_flow and "CapEx" in quarter.cash_flow:
            fcf = quarter.cash_flow["CFO"] + quarter.cash_flow["CapEx"]
        return self._metric_from_value("FCF", fcf, unit="USD", quarter=quarter, inputs=["CFO", "CapEx"])

    def _build_dso(self, quarter: CompanyQuarter) -> Metric:
        value = working_capital.days_sales_outstanding(
            quarter.balance_sheet.get("AccountsReceivable"),
            quarter.income_stmt.get("Revenue"),
        )
        return self._metric_from_value("DSO", value, unit="days", quarter=quarter, inputs=["AccountsReceivable", "Revenue"])

    def _build_dih(self, quarter: CompanyQuarter) -> Metric:
        value = working_capital.days_inventory_on_hand(
            quarter.balance_sheet.get("Inventory"),
            quarter.income_stmt.get("CostOfGoodsSold", quarter.income_stmt.get("COGS")),
        )
        return self._metric_from_value("DIH", value, unit="days", quarter=quarter, inputs=["Inventory", "COGS"])

    def _build_dpo(self, quarter: CompanyQuarter) -> Metric:
        value = working_capital.days_payables_outstanding(
            quarter.balance_sheet.get("AccountsPayable"),
            quarter.income_stmt.get("CostOfGoodsSold", quarter.income_stmt.get("COGS")),
        )
        return self._metric_from_value("DPO", value, unit="days", quarter=quarter, inputs=["AccountsPayable", "COGS"])

    def _build_ccc(self, quarter: CompanyQuarter) -> Metric:
        dso = working_capital.days_sales_outstanding(
            quarter.balance_sheet.get("AccountsReceivable"),
            quarter.income_stmt.get("Revenue"),
        )
        dio = working_capital.days_inventory_on_hand(
            quarter.balance_sheet.get("Inventory"),
            quarter.income_stmt.get("CostOfGoodsSold", quarter.income_stmt.get("COGS")),
        )
        dpo = working_capital.days_payables_outstanding(
            quarter.balance_sheet.get("AccountsPayable"),
            quarter.income_stmt.get("CostOfGoodsSold", quarter.income_stmt.get("COGS")),
        )
        value = working_capital.cash_conversion_cycle(dso, dio, dpo)
        return self._metric_from_value("CCC", value, unit="days", quarter=quarter, inputs=["DSO", "DIH", "DPO"])

    def _build_accruals(self, quarter: CompanyQuarter) -> Metric:
        accrual_value = accruals.accruals_ratio(
            quarter.income_stmt.get("NetIncome"),
            quarter.cash_flow.get("CFO"),
            quarter.balance_sheet.get("TotalAssets"),
        )
        return self._metric_from_value(
            "Accruals Ratio",
            accrual_value,
            unit="ratio",
            quarter=quarter,
            inputs=["NetIncome", "CFO", "TotalAssets"],
        )

    def _build_net_leverage(self, quarter: CompanyQuarter) -> Metric:
        value = balance_sheet.net_leverage_ratio(
            quarter.balance_sheet.get("TotalDebt"),
            quarter.balance_sheet.get("Cash"),
            quarter.income_stmt.get("EBITDA", quarter.income_stmt.get("EBIT")),
        )
        return self._metric_from_value(
            "Net Debt / EBITDA",
            value,
            unit="x",
            quarter=quarter,
            inputs=["TotalDebt", "Cash", "EBITDA"],
        )

    def _build_roic(self, quarter: CompanyQuarter) -> Metric:
        nopat_value = nopat(quarter.income_stmt.get("EBIT"), 0.21)
        invested = invested_capital(
            quarter.balance_sheet.get("TotalEquity"),
            quarter.balance_sheet.get("TotalDebt"),
            quarter.balance_sheet.get("Cash"),
        )
        value = roic_calc(nopat_value, invested) if nopat_value is not None else None
        return self._metric_from_value(
            "ROIC",
            value,
            unit="ratio",
            quarter=quarter,
            inputs=["EBIT", "TaxRate", "InvestedCapital"],
        )
