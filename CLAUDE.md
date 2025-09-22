# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Backend
- `make setup` - Create virtual environment and install Python dependencies
- `make run` - Start the FastAPI server with uvicorn (auto-reload enabled)
- `make test` - Run pytest test suite with coverage
- `make lint` - Run Python compilation checks (compileall)

### Frontend (React Dossier UI)
- `cd hybrid_agent/assets/dossier && npm install` - Install Node.js dependencies
- `cd hybrid_agent/assets/dossier && npm run dev` - Start Vite development server
- `cd hybrid_agent/assets/dossier && npm run build` - Build production React bundle
- `cd hybrid_agent/assets/dossier && npm run test` - Run vitest test suite

### Python Dependencies
Located in `hybrid_agent/infra/requirements.txt` - includes FastAPI, uvicorn, pandas, scikit-learn, pytest, and more.

## Architecture Overview

This is a hybrid investment research agent with a FastAPI backend and React frontend, organized into distinct service layers:

### Core Components
- **Ingest Service** (`hybrid_agent/ingest/`) - Fetches SEC documents via EDGAR API with retry and hashing
- **Parse & Normalize** (`hybrid_agent/parse/`) - Processes SEC XBRL data and PDF documents
- **Calculators** (`hybrid_agent/calculators/`) - Pure functions for financial metrics (ROIC, DCF, leverage, etc.)
- **RAG System** (`hybrid_agent/rag/`) - TF-IDF based document retrieval with in-memory indexing
- **Agents** (`hybrid_agent/agents/`) - AnalystAgent and VerifierAgent for orchestration and QA
- **Delta Engine** (`hybrid_agent/delta/`) - Stores and tracks changes in analysis results
- **Triggers** (`hybrid_agent/triggers/`) - Monitoring system for threshold-based alerts

### API Endpoints
FastAPI app (`hybrid_agent/api.py`) exposes:
- `/ingest` - Document ingestion
- `/calculate` - Metric calculations
- `/analyze` - Agent analysis
- `/verify` - Verification and QA
- `/delta` - Change tracking
- `/triggers` - Alert management
- `/reports/{ticker}` - Stored analysis results
- `/dashboard` - HTML summary view
- `/dossier/{ticker}` - React UI for detailed analysis

### Data Models
Centralized Pydantic models in `hybrid_agent/models.py` ensure type safety and provenance tracking across all components.

### Storage
- Point-in-time documents: `data/pit_documents/` (auto-created)
- JSON-based persistence for deltas, triggers, and reports
- In-memory TF-IDF vector store with optional disk persistence

### Testing Strategy
- Unit tests in `tests/unit/` for individual modules
- Integration tests in `tests/integration/` for API endpoints and workflows
- React component tests using vitest and Testing Library

## Project Structure Notes
- Follows the layout described in `AGENTS.md` with `hybrid_agent/` as the main package
- Configuration files in `hybrid_agent/configs/`
- Documentation in `hybrid_agent/docs/` (architecture.md, runbook.md, etc.)
- Assets including React UI in `hybrid_agent/assets/`
- Development scripts in `scripts/` directory