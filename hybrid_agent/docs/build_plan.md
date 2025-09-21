# Hybrid Investment Research Agent – Build Plan

## Project Goal
Deliver an automated Stage-0 screen and Stage-1 draft for public equities while guaranteeing provenance and leaving final trade deployment to a human. Outputs include the one-line verdict, Stage-0 gate table, Stage-1 one-pager, provenance table, reverse-DCF block, Final Decision Gate inputs, and a verifier QA verdict.

## Engineering Approach
- **TDD first**: write failing tests per milestone before implementing features.
- **Deterministic core**: calculators remain pure, auditable functions.
- **Strict provenance**: every metric ties back to a `Document` record with PIT hash.
- **Separation of concerns**: ingestion → parsing → calculations → retrieval → analyst/verifier agents → delta/trigger services → API/UI.

## Milestones & Acceptance Tests

| # | Milestone | Goals | Primary Tests (to write first) |
|---|-----------|-------|--------------------------------|
| 1 | PIT Ingest Service | Fetch SEC/IR artifacts, persist as immutable `Document` entries, expose `/ingest`. | `tests/unit/ingest/test_edgar_client.py` (fetch & hash, retry), `tests/unit/ingest/test_store.py` (idempotent writes), `tests/integration/test_ingest_endpoint.py` (mock URLs → JSON payload). |
| 2 | Parse & Normalize | Generate `CompanyQuarter` objects with structured statements and segment tables. | `tests/unit/parse/test_xbrl_parser.py`, `tests/unit/parse/test_pdf_tables.py`, `tests/integration/test_parse_pipeline.py` (fixture filings → normalized outputs). |
| 3 | Calculator Orchestrator | Run deterministic calculators, emit `Metric` objects with provenance. | `tests/unit/calculate/test_metric_builder.py`, `tests/integration/test_calculate_endpoint.py` (coverage ≥90% or ABSTAIN). |
| 4 | Evidence Retriever (RAG) | Index documents, return quoted spans with metadata. | `tests/unit/rag/test_index.py`, `tests/unit/rag/test_retrieve.py`, `tests/integration/test_retriever_roundtrip.py`. |
| 5 | Analyst Agent DAG | Compose Outputs 0–4 per spec using calculators + retriever. | `tests/integration/test_analyze_output_structure.py`, `tests/unit/agents/test_analyst_prompt_vars.py`. |
| 6 | Verifier QA Engine | Apply rule-based QA and issue PASS/BLOCKER. | `tests/unit/agents/test_verifier_rules.py`, `tests/integration/test_verifier_blockers.py`. |
| 7 | Delta Engine & Trigger Monitor | Compute deltas, maintain flip-trigger alerts. | `tests/unit/delta/test_engine.py`, `tests/unit/triggers/test_monitor.py`, `tests/integration/test_trigger_alerts.py`. |
| 8 | API Surface & UI Stubs | FastAPI endpoints + minimal dashboard/export. | `tests/integration/test_api_contract.py`, `tests/integration/test_export_endpoints.py`. |

## Immediate Next Steps (Milestone 1)
1. Author failing tests listed for the ingest service.
2. Implement EDGAR/IR clients, PIT storage, and `/ingest` endpoint to satisfy tests.
3. Iterate until all milestone tests pass, then proceed to Milestone 2.

All future work should align with this roadmap and expand documentation as services mature.
