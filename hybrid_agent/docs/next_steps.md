# Next Steps – Hybrid Investment Agent

## Completed (Q3–Q4 2024)
- Normalizer with unit scaling, TTM rollups, and period alignment.
- Deterministic valuation stack (WACC, terminal g, hurdle IRR, reverse-DCF scenarios & sensitivity) plus valuation config loader & CLI.
- Stage-0 gate engine with flip-triggers, Mature/Emergent path logic, and intent-linked evidence snippets.
- Delta engine (revenue, EBIT, FCF, owner earnings, net debt, accruals, diluted shares) and trigger monitor persisted to API + UI.
- Provenance validator (quote substring audit + primary-source enforcement including Macro/Market docs).
- Verifier enhancements (metric spot-checks, hard-gate coverage, reverse-DCF share/net-debt checks, marketplace subscription guardrail).
- React dossier UI with QA badge, Stage-0/Stage-1, Reverse-DCF, delta highlights, trigger monitor, evidence intents, and provenance toggle.
- Integration test covering `/analyze` → `/verify` with QA PASS, valuation outputs, and empty trigger lists.

## In Flight / Upcoming
1. **Evidence Deep Linking**
   - Extend `RetrievalPlanner` intents (auditor language, KPI diffs, supplier finance) and surface call-outs inside Stage-1 cards.
   - Attribute evidence snippets to gate rows and Stage-1 sections with metadata for reviewer audit.

2. **Verifier Audit Trail**
   - Tie debt due ≤24m to footnote data, grow sampling heuristics, and persist QA audit trail (timestamp, reviewer, notes) in `ReportStore`.

3. **Tooling & CI**
   - Stand up pytest + vitest workflow, add pre-commit formatting hooks, and deliver trigger-management CLI helpers.
   - Add valuation-config validator to flag stale prices, missing provenance, and out-of-band inputs.

4. **UI Polish**
   - Inline editing for flip-triggers, CSV/Markdown exports, provenance filters, and global dossier search.
   - Dashboard watchlist summary including trigger status and QA outcomes.

## Testing Targets
- `pytest -q` (Python backend) and `npm run test` (React UI) as the default verification gate.
- Maintain ≥80% coverage on changed Python modules; extend vitest snapshots for new UI states.

## Coordination Notes
- Valuation configs live under `configs/valuation/`; use `scripts/valuation_config.py init <ticker>` to scaffold templates and `scripts/valuation_config.py persist-docs <ticker>` to seed macro documents.
- Build the UI with `npm install && npm run build` inside `hybrid_agent/assets/dossier`; FastAPI `/dossier/{ticker}` serves the hashed bundle with fallback instructions when absent.
- `scripts/run_ticker.py` applies valuation configs, stores analyst/verifier outputs in `data/runtime/reports.json`, and records trigger alerts for the dashboard/UI.

Use this checklist to drive weekly planning; update as the remaining backlog items close.
