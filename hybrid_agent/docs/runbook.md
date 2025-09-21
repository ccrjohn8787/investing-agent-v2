# Runbook – Local Execution

## Prerequisites
- Python 3.9+
- Network access to install dependencies (`fastapi`, `uvicorn`, `pytest`).
- Optional: SEC API keys or document URLs for real ingestion.

## Environment Setup
```
make setup  # creates .venv and installs FastAPI + pytest (requires outbound network)
```
If the environment blocks PyPI, install the packages manually or vendor wheels before running `make setup`.

## Running the Service Locally
```
make run  # launches uvicorn with hybrid_agent.api:app
```
Exposed endpoints:
- `POST /ingest`
- `POST /calculate`
- `POST /analyze`
- `POST /verify`
- `POST /delta`
- `POST /triggers`, `POST /triggers/evaluate`

Use curl or HTTP clients to exercise the API. Refer to `tests/integration/` for request/response examples.

## Running Tests
```
make test  # executes pytest suite after dependencies are installed
```
Coverage goals: ≥80% for changed code; extend tests when adding calculators or agents.

## Offline Smoke Test (No External Packages)
When package installation is unavailable, run the smoke test script to validate the deterministic pipeline:
```
python3 hybrid_agent/docs/smoke_test.py
```
This uses in-memory data to execute the calculation pipeline, the analyst agent fallback, and the verifier logic. The script prints the analyst verdict, Stage-0 row count, provenance entries, and QA result.

## Real Ticker Demo (UBER)
With network access and dependencies installed, you can fetch Uber's latest 10-K, build financial metrics from the SEC Company Facts API, and run the full analyst/verifier pipeline:
```
python3 scripts/run_ticker.py UBER uber_output.json
```
The script executes the following steps:
- Downloads and stores the latest 10-K filing under `data/pit_documents/`
- Calls the SEC Company Facts endpoint to assemble a `CompanyQuarter`
- Runs deterministic calculators, populates Stage-0 gates, and invokes the analyst agent
- Generates provenance entries and verifies the dossier; the resulting JSON (default `uber_output.json`) includes analyst outputs and a QA verdict.
