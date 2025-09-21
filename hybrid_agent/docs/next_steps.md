# Implementation Plan – Hybrid Investment Agent (Q4 2024)

This document tracks the remaining engineering work needed to deliver the dossier experience described in the latest review. Each workstream is expected to ship with unit tests, integration coverage, and UI validation where applicable.

---

## 1. Financial Normalizer
- Detect currency/unit scaling (thousands/millions/billions) and convert to base units.
- Align income statement, balance sheet, and cash flow periods; raise errors for mismatched periods.
- Produce quarterly keys (`YYYY-Q#`) and trailing-twelve-month aggregates (`TTM-YYYYQ#`) for revenue, GP, EBIT, CFO, FCF, AR, inventory, diluted shares.
- Add unit tests (`tests/unit/test_normalizer.py::test_ttm_rollup`).

## 2. WACC / Terminal Growth / Hurdle Module
- Implement deterministic derivation using: risk-free (FRED Treasury), ERP (Damodaran), beta (regression or Damodaran unlevered), cost of debt, tax rate, market weights.
- Return point estimate plus ±100 bps band and full input provenance.
- Unit test (`tests/unit/test_wacc.py::test_wacc_derivation_inputs_provenance`).

## 3. Reverse-DCF Engine
- Compute Base/Bull/Bear IRRs from 5-year FCF paths, shares, price, net debt, WACC, terminal `g`.
- Produce sensitivity grid (`wacc±100bps`, `g±50bps`).
- Unit test (`tests/unit/test_dcf.py::test_irr_monotonicity_and_sensitivity`).

## 4. Stage-0 Gate Builder & Pathing
- Use deterministic calculators to assign Pass/Soft-Pass/Fail and auto-generate flip-triggers + deadlines for each soft gate.
- Implement Mature vs. Emergent logic (TTM metrics + 8-quarter segment coverage).
- Unit test (`tests/unit/test_stage0.py::test_hard_gate_rules`).

## 5. Provenance Enforcement & Evidence Retrieval
- Require provenance fields (`doc_id`, `date`, `page/section`, `quote`, `url`) on every `Metric`.
- Add substring validator that reads PIT documents and confirms the quoted text exists.
- Expand evidence retriever with per-metric query intents (pricing power, KPI definition changes, debt footnote, auditor opinion, segment notes, supplier finance).
- Unit tests (`tests/unit/test_provenance.py::test_quote_substring_validation`, retriever cases).

## 6. Verifier Enhancements
- Recompute five random metrics; block when difference >1%, wrong units, or periods mismatch.
- Enforce: EBIT/Interest & FCF/Interest periods match, debt due ≤24m ties to footnote, DCF share count equals latest filing, segment margins based on reported revenue, reject subscription-only metrics for non-subscription businesses.
- Block dossiers missing hard gate verdicts or using non-primary URLs.
- Unit test (`tests/unit/test_verifier.py::test_block_on_non_primary_and_period_mismatch`).

## 7. API Contract & UI
- `/analyze` returns dossier JSON matching the React schema (Stage-0 tables, Stage-1 cards, Reverse-DCF inputs/scenarios, Final Gate, QA, provenance list).
- `/verify` returns `QA = PASS | BLOCKER` with reason strings; integration test `tests/integration/test_analyze_verify.py::test_full_pipeline_passes_qa`.
- Update the React `DossierView` to render the mockup layout with expandable provenance table and QA badges.
- UI tests:  
  - Complete dossier.  
  - Missing Stage-0/Stage-1 (render “NA”).  
  - QA = BLOCKER (red badge, reasons list).

## 8. Documentation & Runbook Updates
- Keep this plan and `docs/build_plan.md` in sync as milestones are delivered.
- Extend runbook with new CLI steps (normalizer checks, WACC inputs, DCF usage, UI smoke tests).

---

**Verification Checklist Before Sign-off**
1. All unit and integration tests above pass (`pytest`).
2. `scripts/run_ticker.py TICKER` produces dossier JSON with Stage-0/Stage-1/Reverse-DCF/Final Gate sections populated and QA PASS when appropriate.
3. `/dashboard` renders the dossier with human-readable copies of each section.
4. Verifier blocks dossiers when provenance is missing or inconsistencies appear.
5. Reviewer can trace every number to primary-source quotes and provenance fields.
