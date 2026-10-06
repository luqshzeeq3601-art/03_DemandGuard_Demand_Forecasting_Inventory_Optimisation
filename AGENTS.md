# DemandGuard execution instructions

## 1. Communicate clearly

- Explain in direct, simple terms.
- Use short numbered sections and bullets for organised updates.
- State what changed, how it was verified and any remaining limitation.

## 2. Establish context before acting

1. Read README.md and docs/00_START_HERE.md.
2. Read docs/10_PROGRESS_LOG.md and docs/09_DECISIONS_LOG.md.
3. Find the first unfinished, dependency-ready task in tasks/todo.md.
4. Read the task's owning specification before implementation.

The project must be executable from these files without the original conversation. Local documents define project decisions; official documentation may be checked for current library behaviour. Do not silently replace a chosen dataset, horizon, split or inventory policy.

## 3. Act as engineer and project manager

- Engineer: establish data quality, prevent leakage, test decision timing and preserve reproducibility.
- Project manager: keep the MVP bounded, work in dependency order and record evidence after each session.
- Routine implementation choices within the specifications may proceed without another confirmation.
- A later user instruction to start the project authorises the documented local implementation. This planning handoff itself does not start implementation.
- Scope changes must be recorded in docs/09_DECISIONS_LOG.md and reflected in owning specifications before code changes.

## 4. Scientific rules

- Split by calendar time across all products. Never shuffle time-series rows.
- Use features and labels available at each origin only. Fit cohort selection and preprocessing using the allowed historical prefix.
- Freeze selection before the final holdout. Do not tune after viewing holdout results.
- Compare against simple forecasts and a constrained inventory policy.
- Keep recorded sales, latent demand and simulated shortage outcomes distinct.
- Report measured results honestly, including a baseline winning or an improvement target being missed.

## 5. Implementation rules

- Scope edits to this project; preserve projects 1 and 2 and the portfolio workbook.
- Put production logic in `src/demandguard/`; notebooks may explore but must not own required pipelines.
- Use typed functions, explicit schemas, named configuration fields and small modules.
- Add meaningful tests for leakage, model alignment, inventory balances and constraint handling.
- Preserve immutable raw input and record checksums, configuration, code revision and package versions.
- Use trusted local model artifacts. Reject arbitrary artifact paths or remote model uploads.
- Keep raw customer identifiers, local environments and generated large artifacts out of public source control.

## 6. Completion and resumption

- Do not tick a task until its acceptance criteria and verification pass.
- Update tasks/todo.md and docs/10_PROGRESS_LOG.md after each completed task or meaningful blocker.
- Log command, result, evidence path and next task. An unsuccessful run remains unsuccessful.
- Use docs/07_VALIDATION_AND_RELEASE.md before claiming a milestone or release is complete.
- Commands in docs/08_OPERATIONS_AND_COMMANDS.md are planned interfaces until corresponding tasks implement and verify them.
