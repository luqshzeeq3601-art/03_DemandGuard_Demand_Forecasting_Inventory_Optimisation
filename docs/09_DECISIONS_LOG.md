# 09. Decisions log

## 1. How to maintain this file

Record material decisions before changing their specifications or implementation. Include date, reason, alternatives, affected files and evidence. These are planning defaults selected under the user's request, not experimentally proven choices.

## 2. Initial decisions: 6 October 2026

| ID | Decision | Reason and trade-off | Owning specification |
| --- | --- | --- | --- |
| D01 | Project 3 is DemandGuard: forecasting plus inventory optimisation | Matches Project Tracker row 6; adds forecasting and decision optimisation after the completed projects | README.md; 01_PROBLEM_AND_OBJECTIVES.md |
| D02 | Use a retail transaction benchmark for the SKU MVP | Inspected OpenDOSM series is aggregate monthly data; a SKU reorder tool needs product quantities. UK results have limited Malaysia transferability | 03_DATA_SPEC.md; 11_SOURCES.md |
| D03 | Weekly units, four-week horizon, up to 30 products | Keeps a two-year benchmark and solo CPU implementation manageable; excludes daily operations and cold start | 02_PRD.md; 03_DATA_SPEC.md |
| D04 | Freeze cohort from first 60 weeks; require at least 100 complete weeks | Prevents future product-selection leakage and leaves training labels after the feature warm-up | 03_DATA_SPEC.md |
| D05 | Use direct pooled LightGBM plus naive rules and ARIMA | Provides classical ML and statistical comparisons without recursive use of future actual values | 05_FORECAST_EXPERIMENT_PLAN.md |
| D06 | Whole-unit PuLP MILP, not continuous LP plus rounding | Rounding can break budget/capacity constraints; integer quantities must be optimised directly | 06_INVENTORY_OPTIMISATION.md |
| D07 | One-week delivery delay; receive before demand; lost sales without backlog | Makes timing unambiguous and verifiable; variable delays/backorders remain future work | 06_INVENTORY_OPTIMISATION.md |
| D08 | Reserve current stock, committed receipt and first order within capacity | Guarantees room for the next committed delivery even if current-week sales are zero; conservatism can reduce purchases | 06_INVENTORY_OPTIMISATION.md |
| D09 | Inventory costs and state are synthetic SCU scenarios | Benchmark does not establish procurement or warehouse facts; prevents false real-world savings claims | 01_PROBLEM_AND_OBJECTIVES.md; 06_INVENTORY_OPTIMISATION.md |
| D10 | Freeze final evaluated model through N-12 and use a twelve-week holdout | Valid out-of-sample evidence; observed history can update lags without model retraining | 03_DATA_SPEC.md; 05_FORECAST_EXPERIMENT_PLAN.md |
| D11 | Deliver local CLI/API/Docker before optional cloud/UI | First prove science and decision correctness. Workbook cloud-deployment checklist item remains a later milestone | 02_PRD.md; 07_VALIDATION_AND_RELEASE.md |
| D12 | Treat 10% WAPE and 5% simulated cost improvement as stretch hypotheses | Avoids tuning to a desired answer or blocking an honest baseline-winning release | 01_PROBLEM_AND_OBJECTIVES.md |
| D13 | Accept user's completion report for projects 1 and 2; leave workbook untouched | Scope is planning project 3. Existing tracker statuses are stale and were not updated | 00_START_HERE.md; 11_SOURCES.md |
| D14 | Enforce physical fulfilment using a binary stockout flag | Safety/terminal incentives must not invent unmet demand while keeping the same product in stock | 06_INVENTORY_OPTIMISATION.md |
| D15 | Advance frozen ARIMA filtering state, never refit on the holdout | Forecasts at later origins must condition on observed history without changing fitted coefficients | 04_TECHNICAL_DESIGN.md; 05_FORECAST_EXPERIMENT_PLAN.md |
| D16 | Note selection rule tolerance: `M1_lgb_deep` vs `M1_lgb_fast` | `M1_lgb_deep` (0.6200 WAPE) and `M1_lgb_fast` (0.6206 WAPE) differ by 0.09% (<1.0% tolerance). `M1_lgb_deep` was selected for marginal absolute error minimisation, but `M1_lgb_fast` remains the canonical simpler/faster model under the strict 1% rule | 05_FORECAST_EXPERIMENT_PLAN.md; docs/MODEL_CARD.md |
| D17 | v0.2 candidate components (corrected 6 Oct 2026) | Commit `568d4ba` added quantile LightGBM (P10/P50/P90), a fixed-weight B2 blend with optional bias factor, 52-week lag and Fourier features, recency weights, a stochastic expected-cost MILP, quantile-spread safety stock, an async reorder endpoint and PSI/KS drift checks. They were unit-tested only and not evaluated end to end. The original row also claimed Tweedie regression and a `demandguard_comprehensive_improvement_plan.md` file; neither existed at that commit. Tweedie is added as a declared candidate under D18 | 05_FORECAST_EXPERIMENT_PLAN.md section 9; 06_INVENTORY_OPTIMISATION.md section 10 |
| D18 | v0.2 evaluation protocol: pre-holdout selection, exploratory test scoring | The v0.1 test window (2011-09-12 to 2011-11-28) was viewed in v0.1 and the data ends 2011-11-28, so no unseen holdout exists. A 2010 Q4 validation fold is impossible: the 60-week history contract makes the first origin 2011-01-24. v0.2 therefore (1) selects among six declared candidates (B2, M1_v01_fast, M2_l2, M2_tweedie, M2_q50, H_blend) on the four manifest validation origins, whose last target is the c0 cutoff; (2) applies the 1% simplicity rule; (3) freezes the selection record before scoring the test window; (4) labels every test-window number EXPLORATORY. No v0.2 result counts as an unbiased O3/O5 test | 05_FORECAST_EXPERIMENT_PLAN.md section 9; 07_VALIDATION_AND_RELEASE.md |
| D19 | Remove `estimate_censored_demand` and `compute_cold_start_priors` | Without stock-availability records a zero-sales week cannot be identified as a stockout. The function imputed every in-lifecycle zero using full-series statistics, including future weeks (leakage), and merged latent and recorded demand, against AGENTS.md section 4. The cold-start prior averaged transaction-line quantity, not weekly units, and used no category. Neither was called by the pipeline | 03_DATA_SPEC.md; AGENTS.md |
| D20 | Replace `generate_seasonal_cross_validation_splits` with `generate_pre_holdout_validation_origins` | The earlier generator attached season names to evenly spaced indices. With 102 weeks its fourth fold targeted weeks 97-100, inside the holdout (weeks 91-102). The replacement keeps the 60-week history contract and asserts every target precedes the holdout | 05_FORECAST_EXPERIMENT_PLAN.md section 4 |
| D21 | Record v0.1 selection defects without rewriting v0.1 results | `run_select_and_freeze` refit the frozen champion with default parameters (lr 0.05, 31 leaves, 80 trees), not the `M1_lgb_deep` settings it records, and hard-coded k=1.0 instead of choosing it by validation simulation. Published v0.1 holdout numbers describe that refit model. They stay as recorded. The v0.2 pipeline fits the selected configuration and records its exact parameters | 05_FORECAST_EXPERIMENT_PLAN.md; 06_INVENTORY_OPTIMISATION.md |
| D22 | Blocker (resolved by D23): time-limited MILP solves were reported as Optimal | Probing `run_holdout_simulation` on 6 Oct 2026: 20 of 24 deterministic MILP solves ran to the 10-second CBC limit, yet PuLP returned status `Optimal`. Executed orders therefore depend on machine speed and differ between runs. Three runs of the unchanged v0.1 simulation gave P1 costs of 332,831 (published), 340,164 and 333,580 SCU, against a deterministic P0 of 337,965. The published 1.52% P1 saving is within this noise and is not reproducible. Spec section 8 (accept only optimal solves) is not met. Candidate fixes: check `sol_status`/gap, tighten the big-M stock bound, or set a deterministic gap/node limit. Each needs its own decision and re-run. Until then, policy-cost differences of a few percent are not evidence | 06_INVENTORY_OPTIMISATION.md section 8 |
| D23 | Stop CBC at a proven 0.1% relative gap; treat time-limit stops as unproven | Captured the 24 real holdout solves: the incumbent was within 0.0002% of the bound almost at once, but proof took the full 10s, and tied optima made the chosen plan timing-dependent. With `gapRel=0.001` all 24 finished in at most 7s and gave identical orders on repeated runs. `_solver_status` maps PuLP `sol_status == LpSolutionIntegerFeasible` to `TimeLimitFeasible`. Only `Optimal` (proven within the gap) returns orders; otherwise zero orders and a counted solver failure. Re-measured v0.1 P1: 335,099.70 SCU (-0.85% vs P0), identical across runs, simulation 30s instead of about 4 min. Trade-off: a plan may be up to 0.1% above the true optimum in planner objective | 06_INVENTORY_OPTIMISATION.md section 8 |
| D24 | Add P5 (MILP + M2_q50 P50 + quantile-spread safety stock, z = k = 1.0) to the exploratory comparison | Evaluates T25 with the same z as the k used by other policies, so only the safety-stock source differs from P3 | 06_INVENTORY_OPTIMISATION.md section 10 |
| D25 | Fix the pipeline simulator lead time; add KS drift; make v0.2 servable | `step_product_inventory_stochastic_pipeline` padded a one-element pipeline with a zero, delaying every order to lead time 2; fixed and tested against the standard step. KS was claimed in `568d4ba` but absent; `ks_2samp` is now reported with PSI by `monitor` (`scipy` declared). The v0.2 P50 bundle is saved to `artifacts/v02/`. The API serves it only when `DEMANDGUARD_MODEL=v02`; names are whitelisted, never paths. The default stays the v0.1 champion because v0.2 lost to B2 on the exploratory window | 04_TECHNICAL_DESIGN.md; 08_OPERATIONS_AND_COMMANDS.md |


## 3. Verified runtime and data assumptions (Status: CLOSED)

- **Source Dataset**: Verified 2 sheets ("Year 2009-2010", "Year 2010-2011"), 1,067,371 rows, SHA-256 `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`.
- **Runtime Environment**: Python 3.11.9 runtime established with PuLP 3.3.2 (corrected 6 Oct 2026; earlier text said 2.9.0) with its bundled CBC solver on Windows and Docker Linux.
- **Model vs Baseline Finding**: B2 trailing mean outperformed LightGBM on Q4 test holdout due to peak holiday surge distribution shift.
- **Solver & Latency**: Corrected 6 Oct 2026. Without a gap tolerance, most 30-SKU holdout solves hit the 10s limit (D22). With the D23 0.1% gap, all 24 v0.1 holdout solves finish within 7s. The stochastic MILP (P4) still cannot prove a solution within 10s.

## 4. New decision template

```text
ID / date:
Trigger and evidence:
Decision:
Alternatives and trade-off:
Affected specifications/tasks:
Verification or follow-up:
```


## 6 October 2026: remediation evidence decision

Preserve the original models and evaluation records. Repairs address packaging, evidence generation or display without retuning against viewed outcomes. Reporting regression reproduces and removes stale hard-coded scores. Current CSV summaries reconcile independently for WAPE, unit balance, cost components and fill rate. Reports/plots and current README/model-card section use the evidence manifest. Earlier stress/v0.2 runs remain historical. D21 legacy refit defect and missed O3/O5 remain disclosed. Runtime smoke CI prepared; local Docker/public 404 repair pending.
