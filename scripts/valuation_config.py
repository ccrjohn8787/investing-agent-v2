#!/usr/bin/env python3
"""Utility helpers for managing valuation configuration files."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict

from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import Document
from hybrid_agent.valuation.config_loader import ValuationConfigLoader

_DEFAULT_BASE = Path("hybrid_agent/configs/valuation")


def _ensure_base_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def handle_init(args: argparse.Namespace) -> None:
    ticker = args.ticker.upper()
    base = Path(args.directory or _DEFAULT_BASE)
    _ensure_base_dir(base)
    output = base / f"{ticker}.json"
    if output.exists() and not args.force:
        raise SystemExit(f"Config {output} already exists. Use --force to overwrite.")

    template: Dict[str, Any] = {
        "valuation": {
            "risk_free_rate": 0.0,
            "equity_risk_premium": 0.0,
            "beta": 0.0,
            "cost_of_debt": 0.0,
            "tax_rate": 0.21,
            "market_equity_value": 0.0,
            "market_debt_value": 0.0,
            "equity_adjustment_bps": 0.0,
            "share_price": 0.0,
            "shares_diluted": 0.0,
            "net_debt": 0.0,
            "terminal_inputs": {"inflation": 0.02, "real_gdp": 0.015},
            "hurdle": {
                "base": 0.15,
                "adjustment_bps": 0.0,
                "rationale": "",
            },
            "fcf_paths": {
                "Base": [0.0, 0.0, 0.0, 0.0, 0.0],
                "Bull": [0.0, 0.0, 0.0, 0.0, 0.0],
                "Bear": [0.0, 0.0, 0.0, 0.0, 0.0],
            },
            "notes": "",
        },
        "provenance": {
            "WACC-point": {
                "source_doc_id": f"MACRO-{ticker}-VALUATION-{date.today().year}",
                "page_or_section": "Valuation Inputs",
                "quote": "",
                "url": "",
            }
        },
        "documents": [
            {
                "id": f"MACRO-{ticker}-VALUATION-{date.today().year}",
                "ticker": "MACRO",
                "doc_type": "Macro",
                "title": f"{ticker} Valuation Inputs {date.today():%Y-%m-%d}",
                "date": f"{date.today():%Y-%m-%d}",
                "url": "",
                "content": "",
            }
        ],
    }
    output.write_text(json.dumps(template, indent=2), encoding="utf-8")
    print(f"Wrote template to {output}")


def handle_persist_docs(args: argparse.Namespace) -> None:
    base = Path(args.directory or _DEFAULT_BASE)
    loader = ValuationConfigLoader(base_path=base)
    config = loader.load(args.ticker.upper())
    if not config:
        raise SystemExit(f"Config for {args.ticker} not found in {base}")
    documents = config.get("documents", [])
    if not documents:
        print("No documents defined in config; nothing to persist.")
        return
    store = DocumentStore(Path(args.store or "data/pit_documents"))
    for doc_payload in documents:
        content = doc_payload.get("content", "")
        doc_data = {key: value for key, value in doc_payload.items() if key != "content"}
        if not doc_data.get("pit_hash"):
            doc_data["pit_hash"] = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
        document = Document(**doc_data)
        store.save(document, content.encode("utf-8", errors="ignore"))
    print(f"Persisted {len(documents)} documents for {args.ticker.upper()} to {store}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Valuation config utilities")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create a valuation config template")
    init_parser.add_argument("ticker", help="Ticker symbol")
    init_parser.add_argument("--directory", help="Output directory", default=str(_DEFAULT_BASE))
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    init_parser.set_defaults(func=handle_init)

    persist_parser = subparsers.add_parser("persist-docs", help="Persist embedded macro documents to the PIT store")
    persist_parser.add_argument("ticker", help="Ticker symbol")
    persist_parser.add_argument("--directory", help="Config directory", default=str(_DEFAULT_BASE))
    persist_parser.add_argument("--store", help="Document store path", default="data/pit_documents")
    persist_parser.set_defaults(func=handle_persist_docs)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
