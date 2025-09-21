#!/usr/bin/env python3
"""Run hybrid agent pipeline for a given ticker using SEC data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hybrid_agent.agents import AnalystAgent, VerifierAgent
from hybrid_agent.calculate import CalculationService
from hybrid_agent.ingest.edgar import EDGARClient
from hybrid_agent.ingest.service import IngestService
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import Document
from hybrid_agent.parse import SECFactsClient, build_company_quarter_from_facts
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever

# Minimal ticker to CIK mapping for demo purposes
CIK_MAP = {
    "UBER": "1543151",
}


def fetch_latest_10k(ticker: str, store: DocumentStore) -> Document:
    cik = CIK_MAP.get(ticker.upper())
    if not cik:
        raise ValueError(f"Ticker {ticker} not in CIK mapping")
    # Use the SEC submissions API to locate latest 10-K
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": "HybridAgent/1.0 (contact: research@hybridagent.local)",
        "Accept": "application/json",
    })
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    response = session.get(submissions_url, timeout=30)
    response.raise_for_status()
    data = response.json()
    filings = data.get("filings", {}).get("recent", {})
    for form, accession, primary_doc, filing_date in zip(
        filings.get("form", []),
        filings.get("accessionNumber", []),
        filings.get("primaryDocument", []),
        filings.get("filingDate", []),
    ):
        if form == "10-K":
            archive_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik):d}/{accession.replace('-', '')}/{primary_doc}"
            client = EDGARClient()
            document, content = client.fetch_document(
                ticker=ticker.upper(),
                doc_type="10-K",
                title=f"{ticker.upper()} {filing_date} 10-K",
                date=filing_date,
                url=archive_url,
            )
            store.save(document, content)
            return document
    raise RuntimeError("No 10-K filing found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hybrid agent pipeline for a ticker")
    parser.add_argument("ticker", help="Ticker symbol, e.g., UBER")
    parser.add_argument("output", type=Path, help="Path to write analyst output JSON")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    cik = CIK_MAP.get(ticker)
    if not cik:
        raise SystemExit(f"Ticker {ticker} not supported in demo mapping")

    store = DocumentStore(Path("data/pit_documents"))
    ingest_service = IngestService(client=EDGARClient(), store=store)

    document = fetch_latest_10k(ticker, store)

    facts_client = SECFactsClient()
    facts = facts_client.company_facts(cik)
    quarter = build_company_quarter_from_facts(ticker, cik, facts)

    # Build retriever index with the downloaded document content (basic chunking)
    doc_path = Path("data/pit_documents") / ticker / f"{document.id}.bin"
    text_content = doc_path.read_bytes().decode("latin-1", errors="ignore")
    index = InMemoryDocumentIndex(chunk_size=120)
    index.add(document, text_content)
    retriever = Retriever(index)

    calc_service = CalculationService()
    calc_result = calc_service.calculate(quarter)

    metric_map = {metric.name: metric.value for metric in calc_result.metrics}

    def _numeric(name: str) -> Optional[float]:
        value = metric_map.get(name)
        return value if isinstance(value, (int, float)) else None

    net_leverage = _numeric("Net Debt / EBITDA") or 0.0
    roic = _numeric("ROIC") or 0.0

    stage0_rows = [
        {"gate": "Circle of Competence", "result": "Pass"},
        {"gate": "Fraud/Controls", "result": "Pass"},
        {"gate": "Imminent Solvency", "result": "Pass" if net_leverage <= 3 else "Watch"},
        {"gate": "Valuation", "result": "Pass" if roic >= 0.08 else "Needs Review"},
        {"gate": "Final Decision Gate", "result": "Pass"},
    ]

    analyst = AnalystAgent(calculation_service=calc_service, retriever=retriever)
    analyst_result = analyst.analyze(ticker, "2024-09-20", quarter, [document])
    analyst_result["stage_0"] = stage0_rows
    provenance_entries = [
        {
            "metric": metric.name,
            "value": metric.value,
            "document_id": document.id,
            "doc_type": document.doc_type,
            "url": document.url,
        }
        for metric in calc_result.metrics
        if isinstance(metric.value, (int, float))
    ]
    dossier = {
        "provenance": provenance_entries,
        "stage_0": analyst_result.get("stage_0", []),
    }

    verifier = VerifierAgent(calc_service)
    verifier_result = verifier.verify(quarter, dossier)

    payload = {
        "analyst": analyst_result,
        "verifier": verifier_result.model_dump(),
        "dossier": dossier,
    }

    def _convert(item):
        if isinstance(item, dict):
            return {key: _convert(value) for key, value in item.items()}
        if isinstance(item, list):
            return [_convert(value) for value in item]
        if hasattr(item, "__str__") and item.__class__.__name__ == "HttpUrl":
            return str(item)
        return item

    serializable = _convert(payload)
    args.output.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    print(f"Analyst verdict: {analyst_result['output_0']}")
    print(f"Verifier QA: {verifier_result.status}")


if __name__ == "__main__":
    main()
