"""Utilities to extract structured financial statements from SEC HTML filings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from bs4 import BeautifulSoup


@dataclass
class StatementExtractionResult:
    income_statement: Dict[str, float]
    balance_sheet: Dict[str, float]
    cash_flow: Dict[str, float]


class FilingExtractor:
    """Extracts financial statements from SEC filing HTML bodies.

    This is a heuristic parser that looks for consolidated financial statement tables and
    pulls the most recent column of numeric data. It supports the canonical 10-K/10-Q
    layout where statements are presented as HTML tables.
    """

    def __init__(self, *, currency: str = "USD") -> None:
        self.currency = currency

    def extract(self, html: str) -> StatementExtractionResult:
        soup = BeautifulSoup(html, "lxml")
        tables = self._parse_tables(soup)

        income = self._extract_statement(tables, ["operations", "income"], fallback_keys=["Revenues", "Net income"])
        balance = self._extract_statement(tables, ["balance"], fallback_keys=["Total assets", "Total liabilities"])
        cash = self._extract_statement(tables, ["cash flows", "cash flow"], fallback_keys=["Net cash provided", "Cash and cash equivalents"])

        return StatementExtractionResult(
            income_statement=income or {},
            balance_sheet=balance or {},
            cash_flow=cash or {},
        )

    def _extract_statement(
        self,
        tables: List[List[List[str]]],
        keywords: list[str],
        *,
        fallback_keys: list[str],
    ) -> Optional[Dict[str, float]]:
        for table in tables:
            header = " ".join(col.lower() for col in table[0])
            if any(keyword in header for keyword in keywords):
                values = self._table_to_dict(table)
                if values:
                    return values

        # fallback: pick first table containing fallback key in first column
        for table in tables:
            first_column = [row[0].lower() for row in table[1:] if row]
            joined = " ".join(first_column)
            if any(key.lower() in joined for key in fallback_keys):
                values = self._table_to_dict(table)
                if values:
                    return values
        return None

    def _table_to_dict(self, table: List[List[str]]) -> Dict[str, float]:
        if len(table) < 2:
            return {}
        header = [cell.strip().lower() for cell in table[0]]
        if len(header) < 2:
            return {}
        recent_index = len(header) - 1
        statement: Dict[str, float] = {}
        for row in table[1:]:
            if len(row) <= recent_index:
                continue
            key = row[0].strip()
            numeric = self._coerce_number(row[recent_index])
            if key and numeric is not None:
                statement[key] = numeric
        return statement

    @staticmethod
    def _parse_tables(soup: BeautifulSoup) -> List[List[List[str]]]:
        tables: List[List[List[str]]] = []
        for table in soup.find_all("table"):
            matrix: List[List[str]] = []
            for row in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
                if cells:
                    matrix.append(cells)
            if matrix:
                tables.append(matrix)
        return tables

    @staticmethod
    def _coerce_number(value) -> Optional[float]:  # type: ignore[override]
        try:
            if isinstance(value, str):
                value = value.replace(",", "").replace("(", "-").replace(")", "")
            return float(value)
        except (TypeError, ValueError):
            return None
