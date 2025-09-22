"""FastAPI surface for the hybrid investment research agent."""
from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.delta.delta_engine import DeltaEngine
from hybrid_agent.delta.store import DeltaStore
from hybrid_agent.ingest.edgar import EDGARClient, FetchError
from hybrid_agent.ingest.service import IngestService
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import CompanyQuarter, Document, Metric, QAResult
from hybrid_agent.triggers.monitor import TriggerMonitor
from hybrid_agent.triggers.store import TriggerStore
from hybrid_agent.agents import AnalystAgent, VerifierAgent
from hybrid_agent.reports.store import ReportStore
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever, TfidfVectorStore

app = FastAPI()

_FRONTEND_DIST = Path(__file__).resolve().parent / "assets/dossier/dist"
if _FRONTEND_DIST.exists():
    app.mount("/dossier/static", StaticFiles(directory=_FRONTEND_DIST), name="dossier_static")


class IngestDocumentPayload(BaseModel):
    doc_type: str
    title: str
    date: str
    url: HttpUrl


class IngestRequest(BaseModel):
    ticker: str
    documents: List[IngestDocumentPayload]


class IngestResponse(BaseModel):
    ticker: str
    documents: List[Document]


def get_document_store() -> DocumentStore:
    store = getattr(app.state, "document_store", None)
    if store is None:
        store = DocumentStore(base_path=Path("data/pit_documents"))
        app.state.document_store = store
    return store


def _default_ingest_service() -> IngestService:
    store = get_document_store()

    def _http_get(url: str) -> bytes:
        with urllib.request.urlopen(url) as response:  # type: ignore[call-arg]
            return response.read()

    client = EDGARClient(http_get=_http_get)
    return IngestService(client=client, store=store)


def get_ingest_service() -> IngestService:
    service = getattr(app.state, "ingest_service", None)
    if service is None:
        service = _default_ingest_service()
        app.state.ingest_service = service
    return service


@app.post("/ingest", response_model=IngestResponse)
def ingest_documents(
    request: IngestRequest, service: IngestService = Depends(get_ingest_service)
) -> IngestResponse:
    try:
        stored_docs = service.ingest(request.ticker, request.documents)
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return IngestResponse(ticker=request.ticker, documents=stored_docs)


class CalculationRequest(CompanyQuarter):
    pass


class CalculationResponse(BaseModel):
    ticker: str
    period: str
    metrics: List[Metric]


def _default_calculation_service() -> CalculationService:
    return CalculationService()


def get_calculation_service() -> CalculationService:
    service = getattr(app.state, "calc_service", None)
    if service is None:
        service = _default_calculation_service()
        app.state.calc_service = service
    return service


@app.post("/calculate", response_model=CalculationResponse)
def calculate_metrics(
    request: CalculationRequest,
    service: CalculationService = Depends(get_calculation_service),
) -> CalculationResponse:
    result = service.calculate(CompanyQuarter(**request.model_dump()))
    return CalculationResponse(
        ticker=result.ticker,
        period=result.period,
        metrics=result.metrics,
    )


class AnalyzeDocument(Document):
    content: Optional[str] = None


def get_delta_engine() -> DeltaEngine:
    engine = getattr(app.state, "delta_engine", None)
    if engine is None:
        engine = DeltaEngine(store=DeltaStore())
        app.state.delta_engine = engine
    return engine


def get_trigger_monitor() -> TriggerMonitor:
    monitor = getattr(app.state, "trigger_monitor", None)
    if monitor is None:
        monitor = TriggerMonitor(store=TriggerStore())
        app.state.trigger_monitor = monitor
    return monitor


class AnalyzeRequest(BaseModel):
    ticker: str
    today: str
    quarter: CompanyQuarter
    documents: List[AnalyzeDocument]
    history: Optional[List[CompanyQuarter]] = None


class AnalyzeResponse(BaseModel):
    output_0: str
    stage_0: Dict[str, List[dict]]
    stage_1: str
    provenance: List[dict]
    evidence: List[dict]
    reverse_dcf: dict
    final_gate: dict
    path_reasons: List[str]
    provenance_issues: List[str]
    metrics: List[dict]
    delta: Dict[str, dict]
    triggers: List[dict]
    trigger_alerts: List[dict]


def get_report_store() -> ReportStore:
    store = getattr(app.state, "report_store", None)
    if store is None:
        store = ReportStore()
        app.state.report_store = store
    return store


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    calc_service: CalculationService = Depends(get_calculation_service),
    report_store: ReportStore = Depends(get_report_store),
    delta_engine: DeltaEngine = Depends(get_delta_engine),
    trigger_monitor: TriggerMonitor = Depends(get_trigger_monitor),
) -> AnalyzeResponse:
    index = InMemoryDocumentIndex()
    vector_store = TfidfVectorStore()
    documents = []
    for doc_payload in request.documents:
        doc = Document.parse_obj(doc_payload.dict(exclude={"content"}))
        documents.append(doc)
        if doc_payload.content:
            index.add(doc, doc_payload.content)
            vector_store.add(doc, doc_payload.content)
    retriever = Retriever(index, vector_store=vector_store)
    document_store = get_document_store()
    history_objects = request.history or []
    history_models = [CompanyQuarter(**item.model_dump()) for item in history_objects]
    agent = AnalystAgent(
        calculation_service=calc_service,
        retriever=retriever,
        document_store=document_store,
    )
    result = agent.analyze(
        ticker=request.ticker,
        today=request.today,
        quarter=CompanyQuarter(**request.quarter.model_dump()),
        documents=documents,
        history=history_models,
    )
    calc_snapshot = calc_service.calculate(CompanyQuarter(**request.quarter.model_dump()), history_models)
    delta_payload: Dict[str, dict] = {}
    if history_models:
        prior = history_models[-1]
        year_index = -4 if len(history_models) >= 4 else 0
        year_ago = history_models[year_index]
        delta_payload = delta_engine.compute(calc_snapshot.quarter, prior, year_ago)

    metrics_map = {
        metric.name: metric.value
        for metric in calc_snapshot.metrics
        if isinstance(metric.value, (int, float))
    }
    trigger_alerts: List[dict] = []
    try:
        today_date = _date.fromisoformat(request.today)
    except ValueError:
        today_date = _date.today()
    if metrics_map:
        trigger_alerts = trigger_monitor.evaluate(request.ticker, metrics_map, today_date)
    trigger_list = trigger_monitor.list_triggers(request.ticker)
    # Persist analyst snapshot without verifier info yet
    report_store.save_report(
        request.ticker,
        result,
        {"status": "PENDING", "reasons": []},
        delta=delta_payload,
        triggers=trigger_list,
        trigger_alerts=trigger_alerts,
    )
    enriched = dict(result)
    enriched.update(
        {
            "delta": delta_payload,
            "triggers": trigger_list,
            "trigger_alerts": trigger_alerts,
        }
    )
    return AnalyzeResponse(**enriched)


class VerifyRequest(BaseModel):
    quarter: CompanyQuarter
    dossier: dict


class VerifyResponse(QAResult):
    pass


@app.post("/verify", response_model=VerifyResponse)
def verify(
    request: VerifyRequest,
    calc_service: CalculationService = Depends(get_calculation_service),
    report_store: ReportStore = Depends(get_report_store),
) -> VerifyResponse:
    document_store = get_document_store()
    agent = VerifierAgent(calc_service, document_store=document_store)
    result = agent.verify(
        quarter=CompanyQuarter(**request.quarter.model_dump()),
        dossier=request.dossier,
    )
    ticker = request.quarter.ticker
    snapshot = report_store.fetch(ticker)
    report_store.save_report(ticker, snapshot.get("analyst", {}), result.model_dump())
    return VerifyResponse(status=result.status, reasons=result.reasons)


class DeltaRequest(BaseModel):
    current: CompanyQuarter
    prior: CompanyQuarter
    year_ago: CompanyQuarter


class DeltaResponse(BaseModel):
    deltas: dict


@app.post("/delta", response_model=DeltaResponse)
def compute_delta(request: DeltaRequest, engine: DeltaEngine = Depends(get_delta_engine)) -> DeltaResponse:
    result = engine.compute(
        CompanyQuarter(**request.current.model_dump()),
        CompanyQuarter(**request.prior.model_dump()),
        CompanyQuarter(**request.year_ago.model_dump()),
    )
    return DeltaResponse(deltas=result)


@app.get("/delta/{ticker}", response_model=DeltaResponse)
def get_delta_snapshot(ticker: str, engine: DeltaEngine = Depends(get_delta_engine)) -> DeltaResponse:
    data = engine.fetch(ticker)
    return DeltaResponse(deltas=data)


class TriggerUpsertRequest(BaseModel):
    ticker: str
    name: str
    threshold: float
    comparison: str
    deadline: str  # ISO date


class TriggerEvaluateRequest(BaseModel):
    ticker: str
    metrics: dict
    today: str


class TriggerResponse(BaseModel):
    alerts: List[dict]


@app.post("/triggers", response_model=dict)
def upsert_trigger(request: TriggerUpsertRequest, monitor: TriggerMonitor = Depends(get_trigger_monitor)) -> dict:
    monitor.upsert(
        ticker=request.ticker,
        name=request.name,
        threshold=request.threshold,
        comparison=request.comparison,
        deadline=_parse_date(request.deadline),
    )
    return {"status": "ok"}


@app.post("/triggers/evaluate", response_model=TriggerResponse)
def evaluate_triggers(request: TriggerEvaluateRequest, monitor: TriggerMonitor = Depends(get_trigger_monitor)) -> TriggerResponse:
    alerts = monitor.evaluate(
        ticker=request.ticker,
        metrics=request.metrics,
        today=_parse_date(request.today),
    )
    return TriggerResponse(alerts=alerts)


@app.get("/triggers/{ticker}", response_model=TriggerResponse)
def list_triggers_endpoint(ticker: str, monitor: TriggerMonitor = Depends(get_trigger_monitor)) -> TriggerResponse:
    triggers = monitor.list_triggers(ticker)
    return TriggerResponse(alerts=triggers)


@app.get("/reports/{ticker}", response_model=dict)
def get_report(ticker: str, store: ReportStore = Depends(get_report_store)) -> dict:
    report = store.fetch(ticker)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(store: ReportStore = Depends(get_report_store)) -> HTMLResponse:
    reports = store.all_reports()
    rows = []
    for ticker, payload in reports.items():
        analyst = payload.get("analyst", {})
        verifier = payload.get("verifier", {})
        verdict = analyst.get("output_0", "n/a")
        qa_status = verifier.get("status", "PENDING")
        rows.append(
            f"<tr><td>{ticker}</td><td>{verdict}</td><td>{qa_status}</td></tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='3'>No reports yet</td></tr>")
    html = f"""
    <html>
      <head>
        <title>Hybrid Agent Dashboard</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 2rem; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
          th {{ background: #f4f4f4; }}
        </style>
      </head>
      <body>
        <h1>Hybrid Agent Dossiers</h1>
        <table>
          <thead><tr><th>Ticker</th><th>Analyst Verdict</th><th>QA Status</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/dossier/{ticker}", response_class=HTMLResponse)
def dossier_view(ticker: str, store: ReportStore = Depends(get_report_store)) -> HTMLResponse:
    report = store.fetch(ticker)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    dist = _frontend_dist()
    if dist is None:
        html = _fallback_dossier_html(ticker, report)
        return HTMLResponse(content=html)
    manifest = _load_manifest(dist)
    if manifest is None:
        html = _fallback_dossier_html(ticker, report)
        return HTMLResponse(content=html)
    entry = manifest.get("src/main.tsx") or manifest.get("src/main.ts")
    if not entry:
        html = _fallback_dossier_html(ticker, report)
        return HTMLResponse(content=html)

    scripts = [entry.get("file")]
    styles = entry.get("css", [])
    data_json = json.dumps(report)
    ticker_upper = ticker.upper()
    css_tags = "\n".join(
        f'<link rel="stylesheet" href="/dossier/static/{href}">' for href in styles
    )
    script_tags = "\n".join(
        f'<script type="module" src="/dossier/static/{src}"></script>'
        for src in scripts
        if src
    )
    preload = (
        f"<script>window.__DOSSIER__ = {data_json};"
        f" window.__DOSSIER_TICKER__ = '{ticker_upper}';</script>"
    )
    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "  <head>\n"
        "    <meta charset=\"UTF-8\" />\n"
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
        f"    <title>Dossier — {ticker_upper}</title>\n"
        f"    {css_tags}\n"
        "  </head>\n"
        "  <body>\n"
        "    <div id=\"root\"></div>\n"
        f"    {preload}\n"
        f"    {script_tags}\n"
        "  </body>\n"
        "</html>"
    )
    return HTMLResponse(content=html)


def _parse_date(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value).date()


def _frontend_dist() -> Optional[Path]:
    if _FRONTEND_DIST.exists():
        return _FRONTEND_DIST
    return None


def _load_manifest(dist: Path) -> Optional[dict]:
    manifest_path = dist / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _fallback_dossier_html(ticker: str, report: dict) -> str:
    data_json = json.dumps(report, indent=2)
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "  <head><meta charset=\"UTF-8\" /><title>Dossier Fallback</title></head>\n"
        "  <body>\n"
        f"    <h1>Dossier for {ticker.upper()}</h1>\n"
        "    <p>React build not found. Run <code>npm install</code> and <code>npm run build</code> inside <code>hybrid_agent/assets/dossier</code>.</p>\n"
        "    <pre>"
        f"{data_json}"
        "</pre>\n"
        "  </body>\n"
        "</html>"
    )
