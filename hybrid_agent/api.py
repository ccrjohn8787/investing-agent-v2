"""FastAPI surface for the hybrid investment research agent."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import urllib.request

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from hybrid_agent.calculate.service import CalculationService
from hybrid_agent.delta.delta_engine import DeltaEngine
from hybrid_agent.ingest.edgar import EDGARClient, FetchError
from hybrid_agent.ingest.service import IngestService
from hybrid_agent.ingest.store import DocumentStore
from hybrid_agent.models import CompanyQuarter, Document, Metric, QAResult
from hybrid_agent.triggers.monitor import TriggerMonitor
from hybrid_agent.agents import AnalystAgent, VerifierAgent
from hybrid_agent.rag import InMemoryDocumentIndex, Retriever

app = FastAPI()


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


def _default_ingest_service() -> IngestService:
    store = DocumentStore(base_path=Path("data/pit_documents"))

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


class AnalyzeRequest(BaseModel):
    ticker: str
    today: str
    quarter: CompanyQuarter
    documents: List[AnalyzeDocument]


class AnalyzeResponse(BaseModel):
    output_0: str
    stage_0: List[dict]
    stage_1: str
    provenance: List[dict]
    reverse_dcf: dict
    final_gate: dict


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, calc_service: CalculationService = Depends(get_calculation_service)) -> AnalyzeResponse:
    index = InMemoryDocumentIndex()
    documents = []
    for doc_payload in request.documents:
        doc = Document.parse_obj(doc_payload.dict(exclude={"content"}))
        documents.append(doc)
        if doc_payload.content:
            index.add(doc, doc_payload.content)
    retriever = Retriever(index)
    agent = AnalystAgent(calculation_service=calc_service, retriever=retriever)
    result = agent.analyze(
        ticker=request.ticker,
        today=request.today,
        quarter=CompanyQuarter(**request.quarter.model_dump()),
        documents=documents,
    )
    return AnalyzeResponse(**result)


class VerifyRequest(BaseModel):
    quarter: CompanyQuarter
    dossier: dict


class VerifyResponse(QAResult):
    pass


@app.post("/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest, calc_service: CalculationService = Depends(get_calculation_service)) -> VerifyResponse:
    agent = VerifierAgent(calc_service)
    result = agent.verify(
        quarter=CompanyQuarter(**request.quarter.model_dump()),
        dossier=request.dossier,
    )
    return VerifyResponse(status=result.status, reasons=result.reasons)


class DeltaRequest(BaseModel):
    current: CompanyQuarter
    prior: CompanyQuarter
    year_ago: CompanyQuarter


class DeltaResponse(BaseModel):
    deltas: dict


def get_delta_engine() -> DeltaEngine:
    engine = getattr(app.state, "delta_engine", None)
    if engine is None:
        engine = DeltaEngine()
        app.state.delta_engine = engine
    return engine


@app.post("/delta", response_model=DeltaResponse)
def compute_delta(request: DeltaRequest, engine: DeltaEngine = Depends(get_delta_engine)) -> DeltaResponse:
    result = engine.compute(
        CompanyQuarter(**request.current.model_dump()),
        CompanyQuarter(**request.prior.model_dump()),
        CompanyQuarter(**request.year_ago.model_dump()),
    )
    return DeltaResponse(deltas=result)


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


def get_trigger_monitor() -> TriggerMonitor:
    monitor = getattr(app.state, "trigger_monitor", None)
    if monitor is None:
        monitor = TriggerMonitor()
        app.state.trigger_monitor = monitor
    return monitor


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


def _parse_date(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value).date()
