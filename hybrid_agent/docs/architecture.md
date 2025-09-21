# Hybrid Investment Research Agent – Architecture Overview

## High-Level Flow
1. **Ingest Service** (`hybrid_agent.ingest`)
   - `EDGARClient` fetches primary documents with retry + hashing.
   - `DocumentStore` persists immutable PIT copies.
   - `/ingest` FastAPI route coordinates the process.
2. **Parse + Normalize** (`hybrid_agent.parse`)
   - `SECFactsClient` pulls company facts from the SEC XBRL API and `build_company_quarter_from_facts` assembles `CompanyQuarter` models (current primary path).
   - `XBRLParser` and `PDFTableExtractor` remain available for local JSON/PDF parsing.
   - `Normalizer` standardises units and produces deep copies for calculators.
3. **Deterministic Calculators** (`hybrid_agent.calculators`)
   - Pure functions compute working-capital, accruals, leverage, ROIC, and DCF scaffolding.
   - `MetricBuilder` translates `CompanyQuarter` data into provenance-ready `Metric` objects.
   - `/calculate` endpoint surfaces the combined metric set.
4. **Evidence Retrieval (RAG)** (`hybrid_agent.rag`)
   - `InMemoryDocumentIndex` chunk documents.
   - `Retriever` returns quoted spans for qualitative gates.
5. **Agents** (`hybrid_agent.agents`)
   - **AnalystAgent** orchestrates calculators + RAG, builds prompts, and merges LLM output with fallbacks and provenance.
   - **VerifierAgent** deterministically re-computes metrics, audits sources, and enforces hard-gate completeness to return `QAResult`.
6. **Delta & Trigger Services**
   - `DeltaEngine` compares quarter-over-quarter and year-over-year movements.
   - `TriggerMonitor` tracks KPI thresholds and deadlines, exposed via `/delta` and `/triggers` endpoints.
7. **API Surface** (`hybrid_agent.api`)
   - FastAPI app exposes `/ingest`, `/calculate`, `/analyze`, `/verify`, `/delta`, and `/triggers` routes.
   - Dependency injection wires services for testing overrides.

## Data Contracts
- Centralised in `hybrid_agent/models.py` (Pydantic). All components exchange `Document`, `Metric`, `CompanyQuarter`, `QAResult`, etc., ensuring provenance and type validation.

## Testing Strategy
- Unit tests per module family (`tests/unit/...`) exercise calculators, ingest, RAG, agents, delta, and trigger logic.
- Integration tests (`tests/integration/...`) validate endpoint behaviour, agent orchestration, and trigger workflows without external network dependencies.
- `Makefile` targets (`make test`) will run the suite once dependencies are installed (network required to install FastAPI & pytest).

## Deployment Notes
- Default storage path for PIT documents: `data/pit_documents/` (created on demand).
- Network access is required for live data fetching and for installing dependencies via `make setup`.
- For local runs without network, use the sample Python snippet (see `docs/runbook.md`) to exercise calculators and agents with in-memory data.
