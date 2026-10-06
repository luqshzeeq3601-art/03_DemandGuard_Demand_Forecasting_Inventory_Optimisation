# 00. Execution guide

## 1. The agreed project

DemandGuard is project 3: forecast product sales, then choose constrained reorder quantities. The MVP is a local demonstration with a CLI, API and evidence report.

The user reports that projects 1 and 2 are complete. The workbook still shows all project statuses as `Not started`; this is a stale tracker value, not a reason to restart those projects. The workbook was inspected without editing it.

## 2. Defaults that are already chosen

| Decision | Default |
| --- | --- |
| Forecast target | Positive recorded unit sales per product per complete week |
| Scope | One warehouse; up to 30 established product codes |
| Forecast horizon | Next four complete weeks |
| Decision frequency | Weekly |
| Primary source | UCI Online Retail II; verify actual workbook structure in T02 |
| Geography | UK transactions as an engineering benchmark; no Malaysian retailer claim |
| Comparison | Last-value, trailing-mean, annual seasonal-naive, ARIMA and LightGBM |
| Inventory model | PuLP mixed-integer linear model with whole-unit orders |
| Lead time | One complete week; timing fixed in 06_INVENTORY_OPTIMISATION.md |
| Delivery | Local CLI, FastAPI, Docker, CI definition, MLflow and reports |
| Device | CPU; GPU not needed |
| Tracker | tasks/todo.md only |
| Effort | 50-70 focused hours; estimate, not a committed calendar deadline |

## 3. Read in this order

1. README.md, AGENTS.md and this file.
2. 01_PROBLEM_AND_OBJECTIVES.md and 02_PRD.md.
3. ../tasks/plan.md and ../tasks/todo.md.
4. 03_DATA_SPEC.md and 05_FORECAST_EXPERIMENT_PLAN.md before data/model work.
5. 06_INVENTORY_OPTIMISATION.md before reorder or simulation work.
6. 04_TECHNICAL_DESIGN.md and 08_OPERATIONS_AND_COMMANDS.md before delivery work.
7. 07_VALIDATION_AND_RELEASE.md before claiming completion.
8. 09_DECISIONS_LOG.md and 10_PROGRESS_LOG.md when resuming.

Supporting references are in 11_SOURCES.md. Filenames above belong to docs/ unless prefixed with `../`.

## 4. First implementation session

1. Start **T01**, not model training: inspect Python, Git, Docker and solver availability; create the isolated project package and lock dependencies.
2. Start **T02**: download only the chosen source, inspect sheet names/columns and write the provenance manifest.
3. Complete T03-T04 before experiments: clean transactions, build complete weekly panels, freeze the cohort and split manifest.
4. Stop a failed gate, write the exact failure and resolve it. Do not skip to the API to hide a failed data or solver prerequisite.

## 5. How to resume

- Read the newest progress entry and verify current files against its evidence.
- Find the next unchecked task whose dependencies are complete.
- Load that task's specifications, execute a bounded change and run its verification.
- Update task status, progress and relevant decisions. Preserve working outputs.
- If an assumption proves wrong, update the documents first and identify affected tasks.

## 6. Document authority

| Question | Owning file |
| --- | --- |
| What should exist? | 02_PRD.md |
| What data and split are allowed? | 03_DATA_SPEC.md |
| Which forecast wins? | 05_FORECAST_EXPERIMENT_PLAN.md |
| How are orders timed and evaluated? | 06_INVENTORY_OPTIMISATION.md |
| What schemas and components exist? | 04_TECHNICAL_DESIGN.md |
| Does it pass? | 07_VALIDATION_AND_RELEASE.md |
| What work is next? | ../tasks/todo.md and 10_PROGRESS_LOG.md |

The first engineering release may use a simple winning baseline. An honest comparison is required; an impressive score is not a substitute for valid evaluation.
