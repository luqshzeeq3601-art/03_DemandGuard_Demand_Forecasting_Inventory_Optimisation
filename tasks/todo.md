# DemandGuard implementation checklist

## 1. Status and rules

- Current implementation status: **complete; 18/18 tasks complete**.
- Next task: none (v0.1 local release complete).
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

## 7. v0.2 Improvement Tasks (T19–T30)

- [x] **T19 — Implement Tobit demand unbiasing and cold start priors**
  - Acceptance: latent demand unbiasing for stockout weeks implemented; category cold start priors generated.
  - Verify: `tests/test_data.py::test_estimate_censored_demand`, `test_compute_cold_start_priors` pass.
  - Files: `src/demandguard/data.py`, `tests/test_data.py`.

- [x] **T20 — Add annual seasonality, Fourier harmonics, and recency weights**
  - Acceptance: lag-52, rolling-52, Fourier terms ($\sin/\cos$), momentum ratios, and sample weights added.
  - Verify: `tests/test_features.py` passes without chronological leakage.
  - Files: `src/demandguard/features.py`, `tests/test_features.py`.

- [x] **T21 — Implement multi-quantile LightGBM and Tweedie regressors**
  - Acceptance: $P10, P50, P90$ pinball loss models trained with verified monotonic predictions ($P10 \le P50 \le P90$).
  - Verify: `tests/test_model.py::test_probabilistic_model_monotonicity` passes.
  - Files: `src/demandguard/model.py`, `tests/test_model.py`.

- [x] **T22 — Implement adaptive online bias correction and hybrid ensembling**
  - Acceptance: dynamic ratio tracking ($\beta_t$) and hybrid forecast blending with B2 baseline.
  - Verify: `tests/test_model.py::test_hybrid_adaptive_forecaster` passes.
  - Files: `src/demandguard/model.py`, `tests/test_model.py`.

- [x] **T23 — Implement multi-season 4-fold cross-validation scheme**
  - Acceptance: 4 distinct seasonal folds (Spring, Summer, Fall, Holiday Peak) generated for multi-year tuning.
  - Verify: `tests/test_splits.py` passes.
  - Files: `src/demandguard/splits.py`, `tests/test_splits.py`.

- [x] **T24 — Implement stochastic MILP inventory optimization**
  - Acceptance: expected cost minimization across quantile demand realizations with zero budget/capacity breaches.
  - Verify: `tests/test_inventory.py::test_stochastic_inventory_milp` passes.
  - Files: `src/demandguard/inventory.py`, `tests/test_inventory.py`.

- [x] **T25 — Deliver dynamic quantile-spread safety stock policy**
  - Acceptance: safety stock buffer scales dynamically with forecast variance ($SS_{it} \propto P90 - P10$).
  - Verify: `tests/test_policies.py::test_quantile_spread_safety_stock` passes.
  - Files: `src/demandguard/policies.py`, `tests/test_policies.py`.

- [x] **T26 — Implement stochastic lead-time inventory simulation harness**
  - Acceptance: multi-period order pipeline queue and stochastic arrivals tracked accurately.
  - Verify: `tests/test_simulation.py::test_stochastic_pipeline_simulation` passes.
  - Files: `src/demandguard/simulation.py`, `tests/test_simulation.py`.

- [x] **T27 — Deliver asynchronous API job queue and polling endpoints**
  - Acceptance: non-blocking `POST /reorder/async` and `GET /jobs/{id}` endpoints.
  - Verify: `tests/test_api.py::test_api_async_reorder` passes.
  - Files: `src/demandguard/api.py`, `tests/test_api.py`.

- [x] **T28 — Implement Population Stability Index (PSI) and distribution drift monitoring**
  - Acceptance: PSI score and drift classification calculated for incoming transaction streams.
  - Verify: `tests/test_monitoring.py::test_psi_drift_detection` passes.
  - Files: `src/demandguard/monitoring.py`, `tests/test_monitoring.py`.

- [x] **T29 — Expand comprehensive test suite and verify 100% pass rate**
  - Acceptance: 41 unit and integration tests passing across all modules; zero Ruff linting errors.
  - Verify: `pytest` (41/41 passing), `ruff check` (clean).
  - Files: `tests/`.

- [x] **T30 — Update documentation, progress log, decisions log, and git commit**
  - Acceptance: D17 logged, progress log synchronized, comprehensive improvement plan delivered.
  - Verify: `docs/09_DECISIONS_LOG.md`, `docs/10_PROGRESS_LOG.md`, `tasks/todo.md`.

