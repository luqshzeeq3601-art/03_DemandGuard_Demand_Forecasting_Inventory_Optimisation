# 08. Operations and planned commands

## 1. Command status

**All project commands below are planned interfaces, not currently executable functionality.** T01 creates the package; later tasks implement each command. Do not report a command as verified until it has been run successfully.

Run from the DemandGuard project root. On Windows, use the project environment's Python explicitly, without depending on shell activation.

## 2. Environment setup (T01)

1. Inspect available Python versions and record the chosen executable. Default target is Python 3.12; `py -3.12` requires an installed Python launcher/runtime and has not been verified here.
2. Create the environment and install the package once pyproject.toml exists.
3. Resolve exact package/solver versions into requirements.lock.txt and record the lock hash. Do not treat an unpinned install as reproducible.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip freeze --exclude-editable > requirements.lock.txt
.\.venv\Scripts\python.exe -m demandguard.cli doctor
```

`doctor` must check package versions, writable output folders, model readiness when relevant and a real tiny solver result. PuLP and CBC installation/API depend on the pinned version; follow verified official guidance and smoke-test rather than assuming a bundled binary.

## 3. Data workflow (T02-T04)

```powershell
.\.venv\Scripts\python.exe -m demandguard.cli acquire --config config/project.yaml
.\.venv\Scripts\python.exe -m demandguard.cli prepare --config config/project.yaml
.\.venv\Scripts\python.exe -m demandguard.cli split --config config/project.yaml
```

- Acquire: manifest and immutable source; validate downloaded size/content/checksum.
- Prepare: cleaning audit, weekly panel and reconciliation.
- Split: training-only cohort and dated origins; fail on unmet data gate.
- Commands must be idempotent for matching hashes and require a new version/output location when source/config changes.

## 4. Modelling and decision workflow (T05-T12)

```powershell
.\.venv\Scripts\python.exe -m demandguard.cli baseline --config config/project.yaml
.\.venv\Scripts\python.exe -m demandguard.cli backtest --config config/project.yaml
.\.venv\Scripts\python.exe -m demandguard.cli select --config config/project.yaml --scenario config/scenario.yaml
.\.venv\Scripts\python.exe -m demandguard.cli evaluate --split test --config config/project.yaml --scenario config/scenario.yaml
.\.venv\Scripts\python.exe -m demandguard.cli forecast --history tests/fixtures/demo_history.csv --output reports/demo_forecast.csv
.\.venv\Scripts\python.exe -m demandguard.cli reorder --history tests/fixtures/demo_history.csv --scenario config/scenario.yaml --output reports/demo_reorder.csv
.\.venv\Scripts\python.exe -m demandguard.cli simulate --split test --config config/project.yaml --scenario config/scenario.yaml
```

`select` writes a frozen selection record, including champion, safety coefficient and hashes, without test outcomes. `evaluate --split test` refuses an unfrozen selection. `simulate --split test` reuses the frozen artifact/settings; it cannot silently fit another model. Selection/reporting details are in the experiment and inventory specifications.

### v0.2 experiment (T31, decision D18)

```powershell
.\.venv\Scripts\python.exe -m demandguard.cli experiment-v02 --config config/project.yaml --scenario config/scenario.yaml
```

This command selects among six declared candidates on pre-holdout origins and writes `artifacts/v02/selection_record.json` before it scores the viewed test window. It then writes `reports/v02_*` files labelled EXPLORATORY. It takes about 3 minutes on a laptop CPU. Results are reproducible run to run (D23). The v0.2 champion bundle is written to `artifacts/v02/`.

To serve it: `$env:DEMANDGUARD_MODEL = "v02"` before starting the API, or `forecast --artifact-dir artifacts/v02` in the CLI. Only the names `champion` (default, v0.1) and `v02` are accepted (D25).

## 5. Tests and quality gates

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp .pytest_tmp
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
```

Run the task's focused test subset first. Broaden to the required checkpoint suite when integrating a phase. Use a workspace-local pytest temporary directory if Windows ACL/cache behaviour interferes; do not skip the failing behaviour itself.

## 6. Local serving and tracking (T13-T15)

```powershell
.\.venv\Scripts\python.exe -m uvicorn demandguard.api:app --host 127.0.0.1 --port 8000
```

In a separate terminal, check `http://127.0.0.1:8000/health`, `/ready` and `/docs`. Send the generated synthetic examples, not raw customer transactions. A working docs page is not proof that reorder decisions are valid.

```powershell
.\.venv\Scripts\mlflow.exe server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts
docker build -t demandguard:local .
docker run --rm -p 127.0.0.1:8000:8000 demandguard:local
```

Tracking configuration, installed MLflow CLI options, artifact provisioning and Docker solver support must be verified during their tasks. A Windows dependency snapshot is not proof of Linux compatibility; resolve and record a Linux lock in T15 if platform-specific dependencies require it. Bind local development services to loopback.

## 7. Monitoring and reporting (T16-T18)

```powershell
.\.venv\Scripts\python.exe -m demandguard.cli monitor --history tests/fixtures/demo_history.csv --output reports/monitoring.json
.\.venv\Scripts\python.exe -m demandguard.cli report --config config/project.yaml --scenario config/scenario.yaml
```

Monitoring reports input checks and demand-scale signals. Delayed forecast errors require observed target weeks and must show unavailable when labels are absent. Reporting consumes recorded evaluation artifacts rather than generating invented result paragraphs.

## 8. Troubleshooting and rollback

- Missing Python: identify a supported installed executable and update the setup instructions with exact evidence.
- Missing CBC: install/provision the solver appropriate to the locked PuLP release; solve the known fixture in host and container.
- Data schema changed: retain raw input, record the mismatch and update mappings with tests.
- Model mismatch: keep the previous trusted bundle; rebuild only after checking feature/cohort hashes.
- Failed constraints: retain diagnostic inputs and solver logs, remove executable status and fix before further simulation.
- Failed experiment: preserve its run record; return to the last valid baseline/artifact. Do not erase unfavourable runs.

## 9. Session handoff

End each session with task IDs completed, files changed, commands/results, measured evidence, blockers and next task. Save this in 10_PROGRESS_LOG.md so the next session can continue from local Markdown.
