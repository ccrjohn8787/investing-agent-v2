"""Pydantic data contracts for the hybrid investment research agent."""
from __future__ import annotations

from typing import Dict, List, Optional, Literal, Union, Any

from pydantic import BaseModel, Field, HttpUrl


class Document(BaseModel):
    """Represents a point-in-time primary source document."""

    id: str = Field(..., description="Stable identifier for the document in the PIT store")
    ticker: str = Field(..., description="Public ticker symbol associated with the document")
    doc_type: Literal[
        "10-K",
        "20-F",
        "10-Q",
        "6-K",
        "8-K",
        "Proxy",
        "IR-Deck",
        "Transcript",
        "Macro",
        "Market",
    ] = Field(..., description="Document classification")
    title: str = Field(..., description="Document title as provided by the source")
    date: str = Field(..., description="ISO 8601 date the document was filed or published")
    url: HttpUrl = Field(..., description="Canonical URL pointing to the fetched copy")
    pit_hash: str = Field(..., description="Content hash used to guarantee immutability")
    pdf_pages: Optional[int] = Field(
        None, description="Number of pages when the document is a PDF"
    )


class Metric(BaseModel):
    """Numeric or textual metric with provenance and optional dependency graph."""

    name: str
    value: Union[float, str]
    unit: str
    period: str
    source_doc_id: str
    page_or_section: str
    quote: str
    url: HttpUrl
    inputs: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompanyQuarter(BaseModel):
    """Quarterly financial statement snapshot with per-segment details."""

    ticker: str
    period: str
    income_stmt: Dict[str, float]
    balance_sheet: Dict[str, float]
    cash_flow: Dict[str, float]
    segments: Dict[str, Dict[str, float]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GateRow(BaseModel):
    """Single row in the Stage-0 gate table."""

    gate: str
    hard_or_soft: Literal["Hard", "Soft"]
    what_it_means: str
    metrics_sources: List[str]
    pass_rule: str
    result: Literal["Pass", "Soft-Pass", "Fail"]
    flip_trigger: Optional[str] = None
    evidence: Optional[List[str]] = None


class FinalGate(BaseModel):
    """Structured decision inputs for the Final Decision Gate."""

    variant: Dict[str, str]
    price_power: Dict[str, str]
    owner_eps_path: Dict[str, str]
    why_now: Dict[str, str]
    kill_switch: Dict[str, str]


class DCFInputs(BaseModel):
    """Inputs used to drive the deterministic reverse-DCF engine."""

    shares_diluted: float
    price: float
    net_debt: float
    ttm_fcf: float
    wacc: float
    wacc_band: List[float]
    terminal_g: float
    hurdle_irr: float
    notes: str


class DCFScenario(BaseModel):
    """Projected free cash flow scenario with implied IRR."""

    name: Literal["Bear", "Base", "Bull"]
    fcf_path: List[float]
    irr: float


class QAResult(BaseModel):
    """Verifier judgement for an analyst dossier."""

    status: Literal["PASS", "BLOCKER"]
    reasons: List[str]
