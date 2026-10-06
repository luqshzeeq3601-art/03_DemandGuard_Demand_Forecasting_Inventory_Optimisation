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

## 3. Assumptions requiring verification during execution

- Actual source workbook sheet names, aliases, coverage, duplicates and qualifying product count.
- Python 3.12 availability and a compatible, pinned PuLP/CBC combination on Windows and Docker Linux.
- Historical weekly signal is sufficient for useful forecasting; baselines may outperform ML.
- Latency targets and 50-70-hour effort estimate are feasible on the actual machine and workload.
- A fixed catalogue and the specified simple scenarios are adequate for a portfolio demonstration.

These checks have assigned tasks. None requires inventing data or a result during planning.

## 4. New decision template

```text
ID / date:
Trigger and evidence:
Decision:
Alternatives and trade-off:
Affected specifications/tasks:
Verification or follow-up:
```
