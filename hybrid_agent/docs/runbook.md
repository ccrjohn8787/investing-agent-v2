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
.venv/bin/python scripts/run_ticker.py UBER uber_output.json
```
The script executes the following steps:
- Downloads and stores the latest 10-K filing under `data/pit_documents/`
- Parses the filing tables via `FilingExtractor` and merges the data with the SEC Company Facts snapshot
- Builds a TF–IDF vector store and runs the analyst agent (LLM optional) and deterministic fallback logic
- Generates provenance entries, runs verifier QA, persists the dossier to `data/runtime/reports.json`, and saves the JSON payload to `uber_output.json`.

After running the script you can view the stored dossier via:
```
curl http://localhost:8000/reports/UBER
```
and load the HTML dashboard at `http://localhost:8000/dashboard` once the FastAPI server is running.

### Optional LLM integration (Grok / OpenAI)
1. Copy `.env.example` to `.env` and populate one of the keys:
   ```
   GROK_API_KEY=sk-...
   # or
   OPENAI_API_KEY=sk-...
   ```
2. Rerun the script or API endpoint; the agent will automatically load `.env` (via `python-dotenv`) and prefer Grok, falling back to OpenAI if configured, or to deterministic summaries otherwise.
