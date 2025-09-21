"""XBRL parser utilities."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Union

from hybrid_agent.models import CompanyQuarter


class XBRLParser:
    """Parses simplified XBRL JSON payloads into `CompanyQuarter`s."""

    def parse(self, source: Union[Path, str]) -> CompanyQuarter:
        path = Path(source)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._to_company_quarter(payload)

    def _to_company_quarter(self, payload: Mapping[str, Any]) -> CompanyQuarter:
        return CompanyQuarter(
            ticker=payload["ticker"],
            period=payload["period"],
            income_stmt=dict(payload.get("income_statement", {})),
            balance_sheet=dict(payload.get("balance_sheet", {})),
            cash_flow=dict(payload.get("cash_flow", {})),
            segments={
                name: dict(values)
                for name, values in payload.get("segments", {}).items()
            },
        )
