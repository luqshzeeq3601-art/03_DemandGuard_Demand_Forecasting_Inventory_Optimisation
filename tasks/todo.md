# DemandGuard implementation checklist

## 1. Status and rules

- Current implementation status: v0.1 complete (18/18). v0.2: see section 7. Several items are partial or blocked.
- Next task: none scheduled. T22 (online bias correction) remains partial; see progress log for options.
- Mark complete only after acceptance and verification pass; record evidence in ../docs/10_PROGRESS_LOG.md.
- Estimated size: S=1-2 implementation files; M=3-5. Generated outputs and routine task/log updates are additional bookkeeping.
- Commands are the planned interfaces in ../docs/08_OPERATIONS_AND_COMMANDS.md. Implement needed entry points before invoking them.

## 2. Foundation and data

- [x] **T01 — Establish isolated package and solver prerequisites**
  - Acceptance: Python target verified; editable package/doctor works; exact dependency snapshot excludes local editable paths; known tiny solver problem has the expected solution.
  - Verify: import package, `doctor`, solver result and environment/lock hashes recorded; G0 passes.
  - Dependencies: none. Size: M.
  - Files: pyproject.toml, requirements.lock.txt, .gitignore, src/demandguard/__init__.py, src/demandguard/cli.py.
  - Read: technical design, operations, validation gate G0.

- [x] **T02 — Acquire and inspect the chosen source**
  - Acceptance: original workbook retained; actual headers/sheets inspected; source URL, checksum, row counts and license recorded.
  - Verify: `acquire` succeeds on a valid download and rejects wrong content; focused acquisition tests pass.
  - Dependencies: T01. Size: M.
  - Files: src/demandguard/data.py, tests/test_data_acquisition.py, config/project.yaml.
  - Read: data specification sections 1-3; sources.

- [x] **T03 — Produce reconciled weekly sales**
  - Acceptance: cleaning/exclusion rules explicit; complete-week boundaries correct; kept quantities reconcile exactly to the panel.
  - Verify: `prepare`; known-answer SQL fixture and cleaning tests pass; audit unresolved duplicates/gaps before advancing.
  - Dependencies: T02. Size: M.
  - Files: src/demandguard/data.py, queries/weekly_sales.sql, tests/test_data.py.
  - Read: data specification sections 3-6.

- [x] **T04 — Freeze cohort and chronological manifests**
  - Acceptance: first-60-week cohort rule applied; N>=100 and at least 10 SKUs; exact fold/test dates and warm-up training counts recorded.
  - Verify: `split`; changing future sales leaves cohort unchanged; all target windows/labels obey cutoffs; G1 passes.
  - Dependencies: T03. Size: M.
  - Files: src/demandguard/splits.py, tests/test_splits.py, config/project.yaml.
  - Read: data specification sections 5-7.

**Checkpoint G1:** no modelling until provenance, quantities, coverage, cohort and temporal split pass.

## 3. First forecast-to-decision slice

- [x] **T05 — Compare naive forecasts with correct metrics**
  - Acceptance: B1-B3 produce all required SKU/origin/horizon rows; pooled WAPE/MAE/bias and zero-denominator rules verified.
  - Verify: `baseline`; hand-calculated forecast/metric fixtures and alignment tests pass.
  - Dependencies: T04. Size: M.
  - Files: src/demandguard/baselines.py, src/demandguard/evaluation.py, src/demandguard/cli.py, tests/test_baselines.py, tests/test_metrics.py.
  - Read: forecast experiment plan sections 1-4 and 6.

- [x] **T06 — Implement causal direct-horizon features**
  - Acceptance: feature dates/labels align; sixty-week history contract applied; transformations use historical prefixes only.
  - Verify: future-mutation tests, horizon label-cutoff tests and hand-computed lag/rolling examples pass.
  - Dependencies: T04. Size: M.
  - Files: src/demandguard/features.py, tests/test_features.py, config/project.yaml.
  - Read: forecast experiment plan section 3; data split contract.

- [x] **T07 — Implement the shared inventory state transition**
  - Acceptance: receipt/order/demand timing correct; unmet units are lost sales; costs and ending pipeline reconcile.
  - Verify: known multiweek traces, zero-demand trace and no-double-receipt tests pass.
  - Dependencies: T05. Size: M.
  - Files: src/demandguard/simulation.py, tests/test_simulation.py, config/scenario.yaml.
  - Read: inventory specification sections 2 and 4-7.

- [x] **T08 — Deliver the constrained reference rule**
  - Acceptance: P0 deterministic whole-unit orders obey budget and conservative arrival-space reservation; baseline slice runs end to end.
  - Verify: two-product contention tests and a small synthetic forecast->rule->simulation run; G2 passes.
  - Dependencies: T07. Size: M.
  - Files: src/demandguard/policies.py, tests/test_policies.py, src/demandguard/cli.py.
  - Read: inventory comparison policies; PRD US1-US4.

**Checkpoint G2:** baseline worklist and shared simulation must be correct before optimiser/model sophistication.

## 4. Optimisation, selection and holdout

- [x] **T09 — Implement and independently validate the MILP**
  - Acceptance: model includes budgets, pre-demand capacity, committed-order reservation, timing, safety slack and terminal value; only optimal validated Q is executable.
  - Verify: tiny exhaustive-enumeration optimum, zero-budget case, invalid capacity and solver-failure tests; batch runtime measured; G3 passes.
  - Dependencies: T08. Size: M.
  - Files: src/demandguard/inventory.py, src/demandguard/contracts.py, tests/test_inventory.py.
  - Read: full inventory specification; reorder contract.

- [x] **T10 — Add LightGBM and ARIMA candidate policies**
  - Acceptance: pooled direct model consumes causal features; ARIMA failures have deterministic logged fallback; saved bundles reproduce predictions.
  - Verify: model/schema/serialization tests and all-product validation predictions; no final test scoring.
  - Dependencies: T05, T06. Size: M.
  - Files: src/demandguard/model.py, src/demandguard/baselines.py, tests/test_model.py, tests/test_baselines.py, config/project.yaml.
  - Read: forecast experiment plan; artifact contract.

- [x] **T11 — Run bounded validation and freeze selection**
  - Acceptance: four folds and <=12 LightGBM configurations compared; champion and k chosen by declared rules; selection record and tracking evidence saved without test outcomes.
  - Verify: aligned comparisons, recorded fit failures and nonempty per-fold training sets; `backtest` and `select`; G4 passes.
  - Dependencies: T09, T10. Size: M.
  - Files: src/demandguard/evaluation.py, src/demandguard/model.py, src/demandguard/cli.py, tests/test_evaluation.py, config/scenario.yaml.
  - Read: forecast selection rules; inventory validation/k selection rules.

- [x] **T12 — Evaluate frozen forecasts and inventory policies**
  - Acceptance: three forecast test windows and one continuous twelve-week policy comparison use frozen settings; failures and achieved/missed targets are reported.
  - Verify: test access requires selection record; no holdout refit/tuning; pipeline/stock/cost reconciliations and G5 pass.
  - Dependencies: T11. Size: M.
  - Files: src/demandguard/evaluation.py, src/demandguard/simulation.py, src/demandguard/policies.py, src/demandguard/cli.py, tests/test_holdout.py.
  - Read: forecast final holdout; inventory fair simulation/outcomes; validation G5.

**Checkpoint G5:** freeze findings and limitations before presentation; do not tune to improve the final test story.

## 5. Engineering delivery

- [x] **T13 — Finish the documented CLI and synthetic examples**
  - Acceptance: implemented commands share services and return explicit failures; a synthetic history/scenario produces dated forecasts and a feasible worklist.
  - Verify: CLI integration tests and runbook commands against examples; raw customer identifiers absent.
  - Dependencies: T12. Size: M.
  - Files: src/demandguard/cli.py, tests/test_cli.py, tests/fixtures/demo_history.csv, tests/fixtures/demo_scenario.yaml.
  - Read: operations and forecast/reorder contracts.

- [x] **T14 — Serve forecast and reorder contracts through FastAPI**
  - Acceptance: health/readiness/forecast/reorder endpoints follow declared schemas and statuses; no executable worklist on failed solve.
  - Verify: synthetic valid/invalid requests, cold readiness and post-load latency; API integration tests pass.
  - Dependencies: T13. Size: M.
  - Files: src/demandguard/api.py, src/demandguard/contracts.py, tests/test_api.py.
  - Read: technical API contract; PRD failure behaviour.

- [x] **T15 — Verify container and CI quality gates**
  - Acceptance: CPU image contains compatible dependencies/solver and trusted artifact provisioning; CI checks lint/unit/integration tests with synthetic fixtures.
  - Verify: actual `docker build/run`, readiness, known solver fixture and API request inspected; record if external CI has not run.
  - Dependencies: T14. Size: M.
  - Files: Dockerfile, .dockerignore, .github/workflows/ci.yml, requirements-linux.lock.txt if needed, tests/test_container_contract.py.
  - Read: operations serving commands; validation delivery gate.

- [x] **T16 — Add data and delayed forecast monitoring**
  - Acceptance: input anomalies, demand-scale changes and available delayed error metrics are distinct; absent target labels show unavailable; no automatic retraining.
  - Verify: stable and deliberately shifted fixtures; `monitor` outputs tested; G6 passes with CLI/API/container evidence.
  - Dependencies: T15. Size: M.
  - Files: src/demandguard/monitoring.py, tests/test_monitoring.py, src/demandguard/cli.py.
  - Read: validation monitoring requirements; operations section 7.

## 6. Evidence and release

- [x] **T17 — Write the measured portfolio report and model card**
  - Acceptance: real forecast/policy metrics, comparison plots, assumptions and limitations linked; distinguish baseline versus ML contribution and simulation versus real impact.
  - Verify: `report`; independently check representative metric totals and inspect figures at normal size; no unmeasured outcome claims.
  - Dependencies: T16. Size: M.
  - Files: src/demandguard/reporting.py, README.md, docs/MODEL_CARD.md, tests/test_reporting.py.
  - Read: objectives; validation release contents; recorded evaluation artifacts.

- [x] **T18 — Prove fresh local reproduction and close v0.1**
  - Acceptance: disposable clean local setup reproduces required workflow using documented data/artifact steps; every mandatory gate has evidence; next steps/limitations recorded.
  - Verify: fresh environment, focused and integration suite, API and container smoke; G7 passes; update completion evidence and logs.
  - Dependencies: T17. Size: S for any documentation repairs.
  - Files: docs/08_OPERATIONS_AND_COMMANDS.md and README.md if reproduction exposes command omissions.
  - Read: full validation/release gate; operations; progress log.

**Final checkpoint G7:** local implementation is complete when T01-T18 and mandatory requirements are verified. Dashboard, cloud hosting, new datasets and public publishing remain separate follow-ups.

## 7. v0.2 tasks (status corrected 6 Oct 2026)

Commit `568d4ba` ticked T19-T30 on unit tests alone. Statuses below reflect end-to-end evidence; see decisions D17-D22.

- [ ] **T19 — Demand uncensoring and cold-start priors: WITHDRAWN (D19)**
  - The function leaked future data and had no availability signal to justify it. Removed with its tests.

- [x] **T20 — Annual lag, Fourier and recency-weight features**
  - Evidence: used by M2 candidates in `experiment-v02` (`reports/v02_validation.csv`).

- [x] **T21 — Quantile LightGBM and Tweedie candidates**
  - Tweedie did not exist at `568d4ba`; it is now the declared candidate `M2_tweedie`. Evidence: `reports/v02_validation.csv`.

- [ ] **T22 — Hybrid blend and online bias correction: PARTIAL**
  - Fixed 0.5 blend (`H_blend`) evaluated. Online bias correction is not evaluated: no unbiased bias signal exists inside a fold.

- [x] **T23 — Pre-holdout rolling validation origins (replaced, D20)**
  - `generate_pre_holdout_validation_origins` plus `tests/test_splits.py::test_pre_holdout_validation_origins_never_touch_holdout`.

- [x] **T24 — Stochastic MILP: EVALUATED (exploratory) — not executable at the 10s limit**
  - Per-scenario pre-demand capacity added. Under D23 the P4 solve never proves a solution within 10s (12 of 12 weeks), so it places no orders. Evidence: `reports/v02_exploratory_simulation.csv`.

- [x] **T25 — Quantile-spread safety stock: EVALUATED (exploratory, D24)**
  - Policy P5: +25.1% cost vs P0 and worse than P3, because the P50 forecast is biased low.

- [x] **T26 — Multi-period pipeline simulation: FIXED and verified (D25)**
  - Lead-time bug fixed (one-element pipeline became lead time 2). `tests/test_simulation.py::test_pipeline_step_matches_standard_step_for_one_week_lead_time` passes. Not needed by the lead-time-1 scenario.

- [x] **T27 — Async reorder endpoint**
  - `tests/test_api.py::test_api_async_reorder`. Limitation: in-memory job store, lost on restart; runs the deterministic MILP.

- [x] **T28 — PSI/KS drift monitoring: INTEGRATED (D25)**
  - `monitor` reports PSI and KS on SKUs shared with the reference. KS was missing at `568d4ba` and is now added. `tests/test_monitoring.py::test_monitoring_pipeline_reports_distribution_drift`.

- [x] **T29 — Test suite**
  - Includes selection-rule and fold-overlap tests added 6 Oct 2026.

- [x] **T30 — Documentation correction**
  - D17 corrected; D18-D22 added; specs 05 section 9 and 06 section 10 updated; this list re-statused.

- [x] **T31 — Run the D18 v0.2 experiment end to end**
  - Command: `python -m demandguard.cli experiment-v02`. Evidence: `reports/v02_experiment.md`, `artifacts/v02/selection_record.json`.

- [x] **T32 — Resolve D22 (time-limited MILP reported as Optimal) (D23)**
  - `gapRel=0.001`; `TimeLimitFeasible` is not executable. `simulate` run twice gave identical output (30s). Holdout simulation, k grid, stress scenarios, `report` and `experiment-v02` re-run. `tests/test_inventory.py::test_time_limited_solve_is_not_reported_optimal`.

- [x] **T33 — Make the v0.2 champion servable (D25)**
  - P50 bundle in `artifacts/v02/`. CLI and API share `build_inference_features`; v0.1 demo forecasts unchanged (max diff 0.0). `DEMANDGUARD_MODEL=v02` is whitelisted; `tests/test_api.py::test_api_model_selection_rejects_untrusted_names`.
