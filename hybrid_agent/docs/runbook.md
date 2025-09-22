# Runbook – Local Execution

## Prerequisites
- Python 3.9+
- Node 18+ (for the dossier React UI)
- Network access to install dependencies (`fastapi`, `uvicorn`, `pytest`, `react`, `vite`).
- Optional: SEC API keys or document URLs for real ingestion.

## Environment Setup
```bash
make setup  # creates .venv and installs Python dependencies (requires outbound network)
```
If the environment blocks PyPI, install the packages manually or vendor wheels before running `make setup`.

Install front-end dependencies when working on the dossier UI:
```bash
cd hybrid_agent/assets/dossier
npm install
```

## Running the Service Locally
```bash
make run  # launches uvicorn with hybrid_agent.api:app
```
Exposed endpoints:
- `POST /ingest`
- `POST /calculate`
- `POST /analyze`
- `POST /verify`
- `POST /delta`
- `POST /triggers`, `POST /triggers/evaluate`
- `GET /triggers/{ticker}` (persisted trigger definitions)
- `GET /reports/{ticker}` (persisted analyst/verifier/delta/trigger state)
- `GET /dashboard` (HTML summary table)
- `GET /dossier/{ticker}` (React dossier view; see build instructions below)

Use curl or HTTP clients to exercise the API. Refer to `tests/integration/` for request/response fixtures.

## Running Tests
```bash
make test                   # executes pytest suite after dependencies are installed
cd hybrid_agent/assets/dossier && npm run test  # vitest (React UI)
```
Coverage goals: ≥80% for changed Python modules; extend vitest snapshots when introducing new UI states.

## Building & Serving the Dossier UI
```bash
cd hybrid_agent/assets/dossier
npm run build  # outputs dist/ with hashed assets and manifest
```
FastAPI automatically serves the bundle at `/dossier/static/*` and hydrates `/dossier/{ticker}` with `window.__DOSSIER__` when the build (and `manifest.json`) are present. If the build is missing, the route falls back to a plain HTML dump with instructions.

For local iterative work use:
```bash
npm run dev
```
and proxy requests to the running API as needed.

## Valuation Config CLI
Use `scripts/valuation_config.py` to scaffold and maintain ticker configs:
```bash
python scripts/valuation_config.py init UBER                # create template
python scripts/valuation_config.py persist-docs UBER        # persist embedded macro docs to PIT store
```
Configs live under `configs/valuation/<TICKER>.json` and are loaded automatically by `scripts/run_ticker.py` and the API.

## Offline Smoke Test (No External Packages)
When package installation is unavailable, run the smoke test script to validate the deterministic pipeline:
```bash
python3 hybrid_agent/docs/smoke_test.py
```
This uses in-memory data to execute the calculation pipeline, the analyst agent fallback, and the verifier logic. The script prints the analyst verdict, Stage-0 row count, provenance entries, and QA result.

## Real Ticker Demo (UBER)
With network access and dependencies installed, you can fetch Uber's latest 10-K, apply valuation metadata, and run the full analyst/verifier pipeline:
```bash
.venv/bin/python scripts/run_ticker.py UBER uber_output.json
```
The script:
1. Downloads and stores the latest 10-K under `data/pit_documents/`
2. Parses tables via `FilingExtractor` and merges them with SEC Company Facts
3. Loads the valuation config (`configs/valuation/UBER.json`), persists supporting macro documents, and tags the business model
4. Builds the TF–IDF retriever, runs the analyst agent (LLM optional) and deterministic fallbacks
5. Runs verifier QA, computes trigger alerts, and persists the dossier (analyst, verifier, delta, triggers) to `data/runtime/reports.json`

After running the script:
```bash
curl http://localhost:8000/reports/UBER          # raw dossier JSON (includes delta + trigger alerts)
open http://localhost:8000/dashboard             # tabular summary
open http://localhost:8000/dossier/UBER          # React dossier UI (requires npm run build)
```

### Optional LLM integration (Grok / OpenAI)
1. Copy `.env.example` to `.env` and populate one of the keys:
   ```bash
   GROK_API_KEY=sk-...
   # or
   OPENAI_API_KEY=sk-...
   ```
2. Rerun the script or API endpoint; the agent loads `.env` (via `python-dotenv`) and uses Grok first, then OpenAI, otherwise deterministic fallbacks.

### Troubleshooting
- **Missing dossier UI build** — `/dossier/{ticker}` returns a basic HTML page with instructions; run `npm run build` to enable the React bundle.
- **Provenance BLOCKERs** — Ensure all valuation inputs have supporting documents stored in the PIT repository; check quote length (≤30 words) and doc type (`Macro`/`Market` allowed).
- **QA BLOCKER on metric mismatch** — Verify valuation config values match the latest filings; rerun `scripts/run_ticker.py` to refresh stored outputs. Share count and net debt must align with reverse-DCF inputs.
- **Trigger Alerts** — Use `POST /triggers` to register thresholds and `GET /triggers/{ticker}` to review stored definitions. Alerts appear in the dossier UI and `/reports/{ticker}` payload.
