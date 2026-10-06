# 02. Product requirements document

## 1. Product summary

DemandGuard is a local decision-support tool for weekly replenishment. Given cleaned sales history and an inventory scenario, it forecasts the next four weeks and exports an affordable, capacity-aware reorder worklist.

**Release:** v0.1 local demonstrator. **Status:** specified, not implemented. **Owner:** user.

## 2. Product boundary

| In the MVP | Outside the MVP |
| --- | --- |
| One warehouse and up to 30 established products | Multiple warehouses or store transfers |
| Weekly unit-sales forecasting, four horizons | Minute-level or daily operational forecasting |
| Simple baselines, ARIMA and pooled LightGBM | Deep learning, foundation models or LLM agents |
| Whole-unit ordering, fixed one-week lead time | Case packs, minimum order quantities, variable supplier delays |
| Budget and warehouse constraints | Supplier negotiation, purchase-order submission or ERP integration |
| Historical backtesting and synthetic inventory simulation | Realised business impact or causal stockout recovery |
| CLI, FastAPI, Docker, local tracking and reports | Required web dashboard, authentication system or paid cloud platform |

## 3. User journey

1. The engineer validates source data and freezes eligible products and chronological splits.
2. The engineer compares forecasts and selects a model using validation evidence.
3. The planner supplies current stock, scheduled deliveries, weekly budgets and cost assumptions.
4. DemandGuard forecasts four weeks, solves a reorder plan and validates the solution independently.
5. The planner reads the current week's actionable quantities and warnings; later-week quantities remain provisional.
6. The engineer compares policies in a controlled historical simulation and writes the evidence report.

## 4. User stories

| ID | Story | Acceptance |
| --- | --- | --- |
| US1 | As a planner, I need expected sales for each product | Four dated weekly predictions, units clearly stated, model and cutoff identified |
| US2 | As a planner, I need quantities that I can afford | Executable whole-unit worklist obeys this week's budget and declared storage checks |
| US3 | As a manager, I need to see trade-offs | Report includes expected unmet proxy demand, ending stock, spend and scenario assumptions |
| US4 | As an engineer, I need a fair comparison | Chronological backtests and identical simulation conditions for each policy |
| US5 | As a future implementer, I need a reliable starting point | All required decisions and task acceptance criteria are present in the Markdown handoff |

## 5. Functional requirements

| ID | Priority | Requirement | Acceptance evidence |
| --- | --- | --- | --- |
| FR01 | Must | Acquire source with provenance | URL, retrieval time, checksum, sheets and schema in manifest |
| FR02 | Must | Clean sales and create weekly product panel | Exclusion audit and unit-total reconciliation |
| FR03 | Must | Freeze training-only cohort and temporal splits | Machine-readable manifest with exact dates and SKU list |
| FR04 | Must | Run comparable forecast experiments | Predictions aligned to common SKU/origin/horizon keys and complete metrics |
| FR05 | Must | Save a reproducible champion | Artifact bundle, selection reason, configuration and MLflow run identifier |
| FR06 | Must | Produce a constrained reorder plan | Solver status, objective, current orders, provisional future orders and independent checks |
| FR07 | Must | Fail clearly on invalid input or unavailable solver | Typed errors; no fabricated successful plan or unvalidated quantities |
| FR08 | Must | Simulate policies using the same demand and resources | Per-week state log and fair cost/fill-rate comparison |
| FR09 | Must | Provide CLI and local API | Health, forecast and reorder endpoints share the tested services |
| FR10 | Must | Support local operation and maintenance | Docker smoke test, CI definition, monitoring command and runbook |
| FR11 | Must | Publish inspectable project evidence locally | README, model card, limitations, forecast plots and scenario report |
| FR12 | Later | Add a dashboard or public deployment | Separate follow-up after v0.1 passes; not required for local completion |

## 6. Nonfunctional requirements

- **Determinism:** seed 42; data manifest and locked environment recorded. Repeated outputs agree within documented floating-point tolerances.
- **Input scope:** requests contain 1-30 unique supported products and a complete weekly history as defined in the data/API contract.
- **Performance targets:** forecast <=5 seconds and reorder solve <=10 seconds for 30 products and four weeks on the measured local CPU. Record hardware and timings; these are unmeasured targets.
- **Reliability:** solver time limit 10 seconds; v0.1 returns actionable orders only for an optimal, independently valid solution. Other statuses produce a diagnostic response.
- **Observability:** structured run ID, data/model/config versions, timings, status and validation counts; no raw transaction/customer data in logs.
- **Portability:** documented PowerShell workflow and a CPU Linux Docker image; verify both environments rather than assuming solver binaries work everywhere.
- **Safety of inputs:** reject nonfinite/negative stock or costs, invalid budgets, duplicate keys and unknown products. No arbitrary server file path input.

## 7. Failure behaviour

| Condition | Expected behaviour |
| --- | --- |
| Too little historical coverage or missing weeks | Reject with the missing date/product keys; do not silently pad request history |
| Unknown product or duplicate inventory record | Reject with the offending product key |
| Zero weekly budget | Solve the allowed zero-order case and show unmet-demand trade-offs if feasible |
| Initial stock plus committed receipts exceeds capacity | Reject inconsistent scenario before solving |
| Solver missing, infeasible or time-limited | Return diagnostic status with no executable order worklist |
| Model artifact missing or incompatible | Readiness fails; forecast endpoint returns an explicit service error |
| Forecast fails to beat baselines | Retain the strongest valid baseline and document the result |

## 8. Definition of product completion

1. Mandatory FR01-FR11 pass the evidence gates in 07_VALIDATION_AND_RELEASE.md.
2. The test holdout has been evaluated under the frozen protocol and all targets are reported as achieved or missed.
3. Worklist quantities obey constraints and simulation state transitions reconcile.
4. A fresh local checkout can follow the runbook without this conversation.
5. No unmeasured business improvement, Malaysian deployment or public hosting claim appears in the release documentation.

## 9. Change control

- Adjust implementation details within these requirements as needed and log material decisions.
- Changing the source, forecast grain, horizon, final holdout or decision timing requires coordinated specification updates.
- Real procurement, public publishing and billable hosting are separate actions from the local MVP.
