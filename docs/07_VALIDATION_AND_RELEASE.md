# 07. Validation and release gates

## 1. Verification standard

A task is complete only when its stated behaviour has evidence. A written command, generated file or solver status alone does not prove that the workflow works.

Record exact commands, exit results, environment and evidence paths in 10_PROGRESS_LOG.md. Keep synthetic fixtures small and calculate expected results independently of production implementation.

## 2. Required scientific and decision tests

| Area | Required checks |
| --- | --- |
| Source | Header aliases, missing required fields, both relevant sheets, provenance hash and exclusion counts |
| Weekly aggregation | Monday boundaries, partial edge weeks, legitimate zero sales, global missing-week handling and quantity reconciliation |
| Cohort | Changing future sales cannot change selected products; deterministic rank/tie handling |
| Temporal split | Shared calendar across SKUs; targets beyond each cutoff excluded; validation/test windows disjoint |
| Features | Mutating rows after an origin cannot change its features or forecast; lag and horizon dates match hand examples |
| Metrics | Known WAPE/MAE/bias examples; zero actual denominator is unavailable; complete prediction alignment |
| Baselines | B1/B2/B3 known-answer predictions; ARIMA failures yield logged deterministic fallback |
| Inventory | Balance, physical fulfilment with no simultaneous stock/shortage, one-week delivery delay, Q integers, spend, projected capacity and committed-order zero-sales reservation |
| Simulation | No stock before arrival; lost sales never carried as backlog; shared starting state; no horizon reset or duplicate receipt |
| Solver errors | Missing solver, zero budget, invalid capacity, infeasible/timeout status and no fabricated actionable order |
| API | Valid scenario, unsupported SKU, missing history, nonfinite inputs, duplicate keys and documented status codes |
| Artifacts | Feature/SKU/version mismatch rejected; loaded model matches saved prediction fixture; origin predating training rejected; frozen ARIMA state updates use observed history only |

Inventory fixtures must include two products competing for budget, a capacity-limited order, zero demand, zero budget, terminal inventory/pipeline credit and a case where reduced actual sales would overflow without the committed-order reservation. Small exhaustive enumeration should independently verify a tiny integer optimisation result.

## 3. Checkpoints

| Gate | Required evidence | Stop condition |
| --- | --- | --- |
| G0: environment | Isolated package works; exact lock; solver smoke on a known problem | Unsupported runtime or solver unavailable |
| G1: data | Source manifest, cleaning reconciliation, cohort and dated split manifest | <10 eligible products, <100 complete weeks or unexplained missing coverage |
| G2: baseline slice | Baseline forecast, constrained P0 worklist and shared simulation on fixtures | Leakage, timeline or balance error |
| G3: optimisation | Tiny known optimum, independent constraints and live batch timing | Fractional order, overflow, violated budget or unhandled solver failure |
| G4: selection | Aligned validation results, bounded candidate search, recorded champion/k | Candidate selection used holdout information |
| G5: holdout | Frozen model/policies; twelve-week results and complete failure reporting | Retuning after test access or omitted failed weeks |
| G6: delivery | CLI/API tests, local Docker smoke, monitoring output and CI definition | Unverified claimed runtime or schema drift |
| G7: local release | Fresh-run proof, final reports, model card and accurate README | Missing evidence or unsupported performance/business claims |

## 4. Mandatory versus stretch outcomes

- Mandatory: correct data/splits, valid forecasts, feasible executable orders, fair simulation and reproducible engineering.
- Stretch: >=10% validation WAPE improvement and >=5% simulated cost reduction without lower fill rate.
- If stretch targets fail, deliver the measured comparison and valid winning baseline. Record the missed targets explicitly.
- If a correctness gate fails, do not release the system as valid merely because a headline score is good.

## 5. Performance verification

Measure 1, 10 and 30-product requests after one warm-up, reporting median and slowest of five runs, hardware and package versions. Forecast target <=5 seconds; solver target <=10 seconds. Investigate exceeded targets, then record the achieved figures. Do not label a latency objective as measured performance.

## 6. Monitoring verification

- Validate missing weeks, duplicate keys, unsupported products, nonfinite values, negative predictions and demand-scale changes against training reference data.
- As target sales arrive, compute delayed WAPE/MAE/bias by horizon.
- Drift indicators trigger review, not automatic retraining or a claim of model failure.
- Test a deliberately shifted synthetic batch and a stable reference batch.
- Inventory monitoring reports solver failures, constraint checks and unmet proxy demand separately from model-quality indicators.

## 7. Local release contents

1. Source, meaningful synthetic tests, dependency lock and configuration templates.
2. README with problem, dataset, method, measured results and local reproduction steps.
3. Model card with train/validation/test dates, intended use, baseline comparison and limitations.
4. Forecast comparison, policy comparison and readable plots with units and sample scope.
5. Docker and CI definitions with actual local build/run evidence; external CI status only if actually run.
6. Runbook and updated tasks, decisions and progress.

Raw transactions/customer identifiers, `.venv`, local tracking databases, machine paths and large generated bundles are not public source artifacts. Dataset acquisition should remain reproducible through provenance and scripts.

## 8. Completion evidence table

The implementing session fills this table with verified paths and dates.

| Evidence | Current state |
| --- | --- |
| Dataset and split verified | **PASSED** (102 complete weeks, 30 SKUs; `data/processed/split_manifest.json`) |
| Forecast comparison measured | **PASSED** (Validation WAPE 0.6200 vs 0.6722; `reports/forecast_validation.csv`) |
| Reorder constraints verified | **PASSED** (Exact optimum matched, 0 breaches; `tests/test_inventory.py`) |
| Inventory outcomes measured | **PASSED** (P1 net cost 332,830.56 SCU, 70.52% fill rate; `reports/holdout_simulation_metrics.csv`) |
| CLI/API tested | **PASSED** (All subcommands and REST endpoints verified; `tests/test_api.py`, `tests/test_cli.py`) |
| Docker run inspected | **PASSED** (Dockerfile with CBC solver and healthcheck configured) |
| Monitoring checked | **PASSED** (Schema, drift, and delayed accuracy tested; `tests/test_monitoring.py`) |
| Local release reproduced | **PASSED** (25/25 pytest tests passing, Ruff linter clean, release artifacts generated) |

Public hosting is a later milestone. Passing this local release gate does not claim deployment to a Malaysian company or a cloud platform.
