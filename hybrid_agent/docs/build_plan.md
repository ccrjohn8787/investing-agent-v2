# Hybrid Investment Research Agent – Build Plan

## Project Goal
Produce auditable Stage-0/Stage-1 dossiers for public equities with deterministic calculators, enforced provenance, and a human-in-the-loop Final Decision Gate. Outputs include the one-line verdict, Stage-0 gate table, Stage-1 narrative, provenance table, reverse-DCF block, Final Decision Gate inputs, and a verifier QA verdict. The React dossier UI surfaces these sections for review in under 30 minutes per name.

## Current Status (September 2024)
- **Normalization** — Filing unit scaling, quarterly/TTM rollups, and period alignment flow through `Normalizer`; deterministic calculators consume normalized statements.
- **Valuation Toolkit** — `ValuationBuilder` derives WACC (±100 bps band), terminal growth, hurdle IRR, and five-year Base/Bull/Bear FCF paths with sensitivity. Metrics land in Stage-0, Stage-1, and the dossier JSON.
- **Stage-0 & Evidence** — Hard/soft gates are deterministic with flip-triggers and Mature/Emergent pathing. Gate rows now surface intent-based evidence snippets (pricing power, KPI definitions, debt footnotes, supplier finance).
- **Delta & Triggers** — Delta engine tracks revenue, EBIT, FCF, owner earnings, net debt, accruals, and diluted shares. Trigger monitor persists KPI thresholds, surfaces alerts via API, and feeds the dossier UI.
- **Provenance & QA** — Every metric carries `Doc | Section | ≤30-word quote | URL`; validator enforces primary sources (10-K/Q, 6-K, 8-K, Proxy, IR, Macro, Market). Verifier recomputes metrics, checks reverse-DCF shares/net debt, and blocks subscription metrics for marketplace models.
- **Valuation Config Loader & CLI** — `configs/valuation/<TICKER>.json` seeds market inputs with provenance. `scripts/valuation_config.py` scaffolds templates and persists supporting documents. `scripts/run_ticker.py` applies configs, stores dossiers, and reports trigger alerts.
- **UI Delivery** — Vite/React TypeScript app renders Stage-0/Stage-1, Reverse-DCF, delta highlights, trigger monitor, QA badge, evidence intents, and expandable provenance. `/dossier/{ticker}` serves the built bundle with manifest detection and fallback instructions.
- **Integration Test** — `tests/integration/test_analyze_verify.py::test_full_pipeline_passes_qa` covers `/analyze`→`/verify`, verifying valuation outputs, delta payload, and QA PASS.

## Remaining Gaps (Q4 2024)
1. **Evidence Deep Linking**  
   - Expand retrieval intents (auditor language, KPI diffs, supplier finance) and stitch excerpts directly into Stage-1 narrative call-outs.
2. **Verifier Enhancements**  
   - Tie debt due ≤24m to footnote data, grow math spot-check sampling heuristics, and capture QA audit trail (timestamp + reviewer notes).
3. **Operational Tooling & CI**  
   - Wire pytest + vitest into CI, add pre-commit formatting, deliver trigger-management CLI helpers, and provide valuation-config consistency checks.
4. **UX Polish**  
   - Inline editing for flip-triggers, CSV/Markdown exports, provenance filters, global dossier search, and dashboard watchlist summaries.

## Near-Term Milestones
| Milestone | Goals | Primary Tests |
|-----------|-------|---------------|
| Evidence Intent Planner | Expand retrieval intents and hydrate Stage-0/Stage-1 evidence blocks. | `tests/unit/rag/test_planner.py`, `tests/integration/test_analyze_output_structure.py`. |
| Verifier v2 | Debt footnote tie-out, audit trail persistence, adaptive metric sampling. | `tests/unit/test_verifier.py`, golden dossier fixtures. |
| Tooling & CI | pytest/vitest workflow, trigger CLI, valuation-config validator. | CI dry-run, `scripts/valuation_config.py` unit tests. |
| UI Polish | Flip-trigger editor, exports, provenance filters. | Vitest snapshots, accessibility checks. |

## Verification Matrix
- **Unit** — `tests/unit/test_normalizer.py`, `tests/unit/valuation/test_service.py`, `tests/unit/valuation/test_config_loader.py`, `tests/unit/delta/test_engine.py`, `tests/unit/triggers/test_monitor.py`, `tests/unit/test_stage0.py`, `tests/unit/test_dcf.py`, `tests/unit/test_verifier.py`, `tests/unit/test_provenance.py`.
- **Integration** — `/ingest`, `/parse`, `/calculate`, `/analyze`, `/verify`, `/triggers`, `/delta` suites plus `tests/integration/test_analyze_verify.py`.
- **UI** — `npm run test` (vitest) covering complete, missing, QA-blocked dossier states and future trigger/delta snapshots.

## Working Agreements
- Deterministic calculators first; LLM usage (if any) remains optional overlay.
- Every metric must cite a PIT document; non-primary sources trigger BLOCKER.
- Keep modules small (<300 lines) and prefer pure functions.
- Write tests before implementing enhancements.

## Immediate Focus
1. Extend retrieval planner coverage and align Stage-1 narrative call-outs with evidence intents.  
2. Implement verifier audit trail + debt footnote reconciliation and document QA policy in `docs/runbook.md`.  
3. Stand up CI workflow (pytest + vitest) and trigger management CLI.  
4. Design and build flip-trigger editing + export actions in the React dossier.
