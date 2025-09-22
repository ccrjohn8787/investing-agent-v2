#!/usr/bin/env python3
"""Run hybrid agent pipeline for a given ticker using SEC data."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Dict

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from hybrid_agent.agents import AnalystAgent, VerifierAgent
from hybrid_agent.agents.llm import LLMClient, GrokClient, OpenAIClient
from hybrid_agent.calculate import CalculationService
from hybrid_agent.delta.delta_engine import DeltaEngine
from hybrid_agent.ingest.edgar import EDGARClient
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import Document, CompanyQuarter
from hybrid_agent.parse import (
    SECFactsClient,
    FilingExtractor,
    build_company_quarter_from_facts,
)
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever, TfidfVectorStore
from hybrid_agent.reports.store import ReportStore
from hybrid_agent.triggers.monitor import TriggerMonitor
from hybrid_agent.valuation.config_loader import apply_valuation_config

# Minimal ticker to CIK mapping for demo purposes
CIK_MAP = {
    "UBER": "1543151",
    "UPWK": "1627475",
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
    document = fetch_latest_10k(ticker, store)

    facts_client = SECFactsClient()
    facts = facts_client.company_facts(cik)
    quarter = build_company_quarter_from_facts(ticker, cik, facts)

    doc_path = Path("data/pit_documents") / ticker / f"{document.id}.bin"
    text_content = doc_path.read_bytes().decode("latin-1", errors="ignore")
    # Parse detailed statements from the downloaded 10-K HTML
    extractor = FilingExtractor()
    statement_data = extractor.extract(text_content)
    quarter = _merge_statement_data(quarter, statement_data, document)
    quarter = apply_valuation_config(quarter, ticker, store=store)
    quarter.metadata.setdefault("business_model", "marketplace")

    # Build retriever index with the downloaded document content (basic chunking)
    index = InMemoryDocumentIndex(chunk_size=120)
    index.add(document, text_content)
    vector_store = TfidfVectorStore()
    vector_store.add(document, text_content)
    retriever = Retriever(index, vector_store=vector_store)

    calc_service = CalculationService()
    calc_snapshot = calc_service.calculate(quarter)

    metrics_map = {
        metric.name: metric.value
        for metric in calc_snapshot.metrics
        if isinstance(metric.value, (int, float))
    }

    llm_client = _build_llm_client()
    analyst_kwargs = {
        "calculation_service": calc_service,
        "retriever": retriever,
        "document_store": store,
    }
    if llm_client is not None:
        analyst_kwargs["llm_client"] = llm_client
    analyst = AnalystAgent(**analyst_kwargs)
    analyst_result = analyst.analyze(ticker, "2024-09-20", quarter, [document])
    dossier = analyst_result

    delta_engine = DeltaEngine()
    delta_payload: Dict[str, Dict[str, float]] = delta_engine.fetch(ticker)
    trigger_monitor = TriggerMonitor()
    trigger_alerts = trigger_monitor.evaluate(ticker, metrics_map, date.today())
    trigger_list = trigger_monitor.list_triggers(ticker)

    verifier = VerifierAgent(calc_service, document_store=store)
    verifier_result = verifier.verify(quarter, dossier)

    payload = {
        "analyst": analyst_result,
        "verifier": verifier_result.model_dump(),
        "dossier": dossier,
        "delta": delta_payload,
        "triggers": trigger_list,
        "trigger_alerts": trigger_alerts,
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
    analyst_payload = serializable["analyst"]
    analyst_payload.setdefault("delta", delta_payload)
    analyst_payload.setdefault("triggers", trigger_list)
    analyst_payload.setdefault("trigger_alerts", trigger_alerts)
    ReportStore().save_report(
        ticker,
        analyst_payload,
        serializable["verifier"],
        delta=delta_payload,
        triggers=trigger_list,
        trigger_alerts=trigger_alerts,
    )
    args.output.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    print(f"Analyst verdict: {analyst_result['output_0']}")
    print(f"Verifier QA: {verifier_result.status}")
def _merge_statement_data(quarter: CompanyQuarter, statements, document: Document) -> CompanyQuarter:
    """Merge extracted statement values into CompanyQuarter model."""

    payload = quarter.model_dump()
    income = payload.get("income_stmt", {})
    balance = payload.get("balance_sheet", {})
    cash_flow = payload.get("cash_flow", {})
    provenance = payload.get("metadata", {}).get("provenance", {})

    def fetch(source: Dict[str, float], candidates: list[str]) -> Optional[float]:
        for candidate in candidates:
            for key, value in source.items():
                if candidate.lower() in key.lower():
                    return value
        return None

    def set_provenance(field: str, labels: Dict[str, str]):
        if field not in provenance:
            for key, label in labels.items():
                if field.lower() in key.lower():
                    provenance[field] = {
                        "quote": label,
                        "source_doc_id": document.id,
                        "page_or_section": "filing table",
                        "url": str(document.url),
                        "date": document.date,
                    }
                    break

    revenue = fetch(statements.income_statement, ["revenue", "sales"])
    if revenue is not None:
        income["Revenue"] = revenue
        set_provenance("Revenue", statements.income_provenance)
    net_income = fetch(statements.income_statement, ["net income", "net earnings"])
    if net_income is not None:
        income["NetIncome"] = net_income
        set_provenance("NetIncome", statements.income_provenance)
    ebit = fetch(statements.income_statement, ["operating income", "earnings before interest"])
    if ebit is not None:
        income["EBIT"] = ebit
        set_provenance("EBIT", statements.income_provenance)

    assets = fetch(statements.balance_sheet, ["total assets"])
    if assets is not None:
        balance["TotalAssets"] = assets
        set_provenance("TotalAssets", statements.balance_provenance)
    cash = fetch(statements.balance_sheet, ["cash", "cash equivalents"])
    if cash is not None:
        balance["Cash"] = cash
        set_provenance("Cash", statements.balance_provenance)
    equity = fetch(statements.balance_sheet, ["stockholders' equity", "shareholders' equity"])
    if equity is not None:
        balance["TotalEquity"] = equity
        set_provenance("TotalEquity", statements.balance_provenance)

    cfo = fetch(statements.cash_flow, ["net cash provided", "net cash used by operating"])
    if cfo is not None:
        cash_flow["CFO"] = cfo
        set_provenance("CFO", statements.cash_provenance)
    capex = fetch(statements.cash_flow, ["payments to acquire", "capital expenditures"])
    if capex is not None:
        cash_flow["CapEx"] = capex
        if cfo is not None:
            cash_flow["FCF"] = cfo + capex
            set_provenance("FCF", statements.cash_provenance)

    metadata = payload.get("metadata", {})
    metadata.setdefault("currency", statements.currency)
    metadata.setdefault("unit_scale", statements.unit_scale)
    if statements.unit_text:
        metadata.setdefault("unit_text", statements.unit_text)
    metadata.setdefault("provenance", provenance)

    payload["income_stmt"] = income
    payload["balance_sheet"] = balance
    payload["cash_flow"] = cash_flow
    payload["metadata"] = metadata
    return CompanyQuarter(**payload)


def _build_llm_client() -> Optional[LLMClient]:
    try:
        if os.getenv("GROK_API_KEY"):
            return GrokClient()
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIClient()
    except RuntimeError:
        return None
    return None


if __name__ == "__main__":
    main()
