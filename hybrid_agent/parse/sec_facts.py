"""Interface to SEC Company Facts API for building CompanyQuarter models."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional

import requests

from hybrid_agent.models import CompanyQuarter

_SEC_HOST = "https://data.sec.gov"
_DEFAULT_HEADERS = {
    "User-Agent": "HybridAgent/1.0 (contact: research@hybridagent.local)",
    "Accept": "application/json",
}


@dataclass
class SECFactsClient:
    user_agent: str = _DEFAULT_HEADERS["User-Agent"]

    def __post_init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})
        self._session.headers.update({"Accept": "application/json"})

    def company_facts(self, cik: str) -> Dict[str, object]:
        cik = cik.zfill(10)
        url = f"{_SEC_HOST}/api/xbrl/companyfacts/CIK{cik}.json"
        response = self._session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()


def _latest_fact_value(facts: Dict[str, object], key: str, units: str = "USD") -> Optional[float]:
    try:
        series = facts[key]["units"][units]
    except KeyError:
        return None
    # Pick most recent by end date
    latest = max(series, key=lambda item: item.get("end") or item.get("fy", "0"))
    return latest.get("val")


def build_company_quarter_from_facts(ticker: str, cik: str, facts: Dict[str, object]) -> CompanyQuarter:
    gaap = facts.get("facts", {}).get("us-gaap", {})

    def g(key: str, units: str = "USD") -> Optional[float]:
        return _latest_fact_value(gaap, key, units)

    revenue = g("Revenues") or g("SalesRevenueNet")
    net_income = g("NetIncomeLoss")
    ebit = g("OperatingIncomeLoss")
    accounts_receivable = g("AccountsReceivableNetCurrent")
    inventory = g("InventoryNet")
    accounts_payable = g("AccountsPayableCurrent")
    current_assets = g("AssetsCurrent")
    current_liabilities = g("LiabilitiesCurrent")
    total_assets = g("Assets")
    cash = g("CashAndCashEquivalentsAtCarryingValue")
    equity = g("StockholdersEquity") or g("CommonStockholdersEquity")

    debt_current = g("DebtCurrent") or 0.0
    debt_long = g("LongTermDebtNoncurrent") or 0.0
    total_debt = None
    if debt_current is not None or debt_long is not None:
        total_debt = (debt_current or 0.0) + (debt_long or 0.0)

    cfo = g("NetCashProvidedByUsedInOperatingActivities")
    capex = g("PaymentsToAcquirePropertyPlantAndEquipment")
    fcf = None
    if cfo is not None and capex is not None:
        fcf = cfo + capex  # capex usually negative

    end_period = None
    revenue_series = gaap.get("Revenues", {}).get("units", {}).get("USD", [])
    if revenue_series:
        latest_entry = max(revenue_series, key=lambda item: item.get("end") or "")
        end_period = latest_entry.get("fp") or latest_entry.get("fy")
        period_label = latest_entry.get("end") or latest_entry.get("fy")
    else:
        period_label = "MostRecent"

    company_quarter = CompanyQuarter(
        ticker=ticker,
        period=period_label,
        income_stmt={
            "Revenue": revenue or 0.0,
            "NetIncome": net_income or 0.0,
            "EBIT": ebit or (net_income or 0.0),
        },
        balance_sheet={
            "AccountsReceivable": accounts_receivable or 0.0,
            "Inventory": inventory or 0.0,
            "AccountsPayable": accounts_payable or 0.0,
            "CurrentAssets": current_assets or 0.0,
            "CurrentLiabilities": current_liabilities or 0.0,
            "TotalAssets": total_assets or 0.0,
            "TotalDebt": total_debt or 0.0,
            "Cash": cash or 0.0,
            "TotalEquity": equity or 0.0,
        },
        cash_flow={
            "CFO": cfo or 0.0,
            "CapEx": capex or 0.0,
            "FCF": fcf if fcf is not None else 0.0,
        },
        segments={
            "Total": {"Revenue": revenue or 0.0},
        },
    )
    return company_quarter
