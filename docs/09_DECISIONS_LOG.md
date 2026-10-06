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

## 3. Verified runtime and data assumptions (Status: CLOSED)

- **Source Dataset**: Verified 2 sheets ("Year 2009-2010", "Year 2010-2011"), 1,067,371 rows, SHA-256 `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`.
- **Runtime Environment**: Python 3.11.9 runtime established with pinned PuLP 2.9.0 and CBC solver on Windows and Docker Linux.
- **Model vs Baseline Finding**: B2 trailing mean outperformed LightGBM on Q4 test holdout due to peak holiday surge distribution shift.
- **Solver & Latency**: CBC integer solver runs in <0.2s for 30 SKUs, well within the 10s budget.

## 4. New decision template

```text
ID / date:
Trigger and evidence:
Decision:
Alternatives and trade-off:
Affected specifications/tasks:
Verification or follow-up:
```
