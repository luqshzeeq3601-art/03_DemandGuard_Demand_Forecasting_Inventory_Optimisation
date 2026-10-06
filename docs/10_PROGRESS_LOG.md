# 10. Progress log

## 1. Current state

- Phase: **v0.1 Local Release Complete (Remediated & Verified)**.
- Planning files: verified and updated.
- Implementation tasks completed: **18 of 18 (100%)**.
- Next task: None. Local v0.1 milestone verified, audited, and closed.
- Dataset acquired and verified: Yes (`data/raw/online_retail_II.xlsx`, SHA-256: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`).
- Forecast trained/evaluated: Yes (Validation WAPE: 0.6200 for LightGBM vs 0.6722 for B2; Holdout WAPE: 0.5777 for B2 vs 0.7107 for LightGBM).
- Inventory simulation measured: Yes (12-week holdout continuous simulation: P1 MILP baseline achieved lowest cost 332,830.56 SCU, 70.52% fill rate, 0 capacity breaches).
- API/Docker/deployment verified: Yes (FastAPI tested with passing test client; Dockerfile & GitHub Actions CI configured and verified via contract tests).

---

## 2. Granular Task Execution and Evidence Log (T01–T18)

| Task | Command Executed | Result & Status | Evidence Path | Gate |
| :--- | :--- | :--- | :--- | :---: |
| **T01** | `python -m demandguard.cli doctor` | **SUCCESS**: Python 3.11.9, dependencies locked, PuLP CBC integer solver verified. | `requirements.lock.txt`, `tests/test_environment_and_solver.py` | **G0: PASSED** |
| **T02** | `python -m demandguard.cli acquire --config config/project.yaml` | **SUCCESS**: UCI Online Retail II downloaded (1,067,371 rows, 2 sheets, SHA-256 verified). | `data/raw/source_manifest.json`, `tests/test_data_acquisition.py` | — |
| **T03** | `python -m demandguard.cli prepare --config config/project.yaml` | **SUCCESS**: 956,124 clean UK transactions aggregated via DuckDB into 102 complete Monday–Sunday weeks (9,013,090 units). 358k unit boundary gap reconciled. | `data/processed/weekly_sales.parquet`, `reports/data_quality.md`, `reports/data_quality_audit.json` | — |
| **T04** | `python -m demandguard.cli split --config config/project.yaml` | **SUCCESS**: 30 cohort SKUs selected strictly from first 60 weeks. 4 validation origins (74, 78, 82, 86) and 3 test holdout origins (90, 94, 98) created. | `data/processed/cohort.json`, `data/processed/split_manifest.json`, `tests/test_splits.py` | **G1: PASSED** |
| **T05** | `python -m demandguard.cli baseline --config config/project.yaml` | **SUCCESS**: Naive forecasts B1, B2, B3, and ARIMA B4 implemented with deterministic B2 fallback. Evaluation metrics (WAPE, MAE, Bias) verified. | `src/demandguard/baselines.py`, `tests/test_baselines.py`, `tests/test_metrics.py` | — |
| **T06** | `python -c "from demandguard.features import generate_and_save_features; generate_and_save_features()"` | **SUCCESS**: Causal lag and rolling features built across all valid origins without future leakage. | `data/processed/features.parquet`, `tests/test_features.py` | — |
| **T07** | `pytest tests/test_simulation.py -v` | **SUCCESS**: Inventory state transition verified: receipt before demand, unbacklogged lost sales, holding and unmet costs. | `src/demandguard/simulation.py`, `tests/test_simulation.py` | — |
| **T08** | `pytest tests/test_policies.py -v` | **SUCCESS**: P0 constrained order-up-to heuristic implemented with conservative arrival space protection. | `src/demandguard/policies.py`, `tests/test_policies.py` | **G2: PASSED** |
| **T09** | `pytest tests/test_inventory.py -v` | **SUCCESS**: PuLP MILP formulation enforces pre-demand capacity, committed reservation ($I_0+A_1+Q_1 \le C$), and independent constraint reconstruction. Matches exhaustive test optimum. | `src/demandguard/inventory.py`, `tests/test_inventory.py` | **G3: PASSED** |
| **T10** | `pytest tests/test_model.py -v` | **SUCCESS**: `DemandGuardModel` wrapper for LightGBM trained with native saving/loading and categorical SKU encoding. | `src/demandguard/model.py`, `tests/test_model.py` | — |
| **T11** | `python -m demandguard.cli backtest; python -m demandguard.cli select` | **SUCCESS**: 4 validation folds (480 predictions) evaluated. `M1_lgb_deep` achieved 0.6200 WAPE. Frozen champion bundle and selection record saved ($k=1.0$). | `reports/forecast_validation.csv`, `artifacts/champion/selection_record.json`, `tests/test_evaluation.py` | **G4: PASSED** |
| **T12** | `python -m demandguard.cli evaluate --split test; python -m demandguard.cli simulate --split test` | **SUCCESS**: 12-week test holdout evaluated. B2 won forecast holdout (0.5777 WAPE vs LightGBM 0.7107). 12-week simulation: P1 saved 5,134.30 SCU (1.52%) over P0 with 0 capacity breaches. | `reports/holdout_forecast_metrics.csv`, `reports/holdout_simulation_metrics.csv`, `tests/test_holdout.py` | **G5: PASSED** |
| **T13** | `python -m demandguard.cli forecast; python -m demandguard.cli reorder` | **SUCCESS**: CLI subcommands tested against synthetic fixture history and scenario files. | `reports/demo_forecast.csv`, `reports/demo_reorder.csv`, `tests/test_cli.py` | — |
| **T14** | `pytest tests/test_api.py -v` | **SUCCESS**: FastAPI endpoints `/health`, `/ready`, `/forecast`, `/reorder` tested with 100% passing test client. | `src/demandguard/api.py`, `tests/test_api.py` | — |
| **T15** | `pytest tests/test_container_contract.py -v` | **QUALIFIED**: Dockerfile, `.dockerignore`, and GitHub Actions CI workflow configured and verified via structural contract tests. (Live Docker build/run and remote GitHub Actions CI execution require external runner). | `Dockerfile`, `.github/workflows/ci.yml`, `tests/test_container_contract.py` | **G6: QUALIFIED** |
| **T16** | `pytest tests/test_monitoring.py -v` | **SUCCESS**: Input schema anomaly detection, scale shift detection, and delayed accuracy calculation verified. | `src/demandguard/monitoring.py`, `tests/test_monitoring.py` | — |
| **T17** | `python -m demandguard.cli report` | **SUCCESS**: Matplotlib comparison charts (`forecast_comparison_plot.png`, `inventory_cost_fillrate_plot.png`), markdown reports, `docs/MODEL_CARD.md`, and `README.md` generated. | `reports/`, `docs/MODEL_CARD.md`, `README.md` | — |
| **T18** | `pytest tests -v; ruff check src tests` | **SUCCESS**: Full test suite (28/28 tests passing across all 18 test files) and clean Ruff linter checks verified. Local Git repository initialized. | `.git/`, test logs, `docs/07_VALIDATION_AND_RELEASE.md` | **G7: PASSED** |

---

## 3. v0.2 Improvement Tasks Execution and Evidence Log (T19–T30)

| Task | Module / Action | Result & Status | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **T19** | `src/demandguard/data.py` | **SUCCESS**: Tobit demand uncensoring heuristic and cold start priors implemented. | `tests/test_data.py::test_estimate_censored_demand`, `test_compute_cold_start_priors` |
| **T20** | `src/demandguard/features.py` | **SUCCESS**: 52-week lag, rolling 52, annual Fourier harmonics ($\sin/\cos$), momentum ratios, and recency exponential sample weights added. | `tests/test_features.py` |
| **T21** | `src/demandguard/model.py` | **SUCCESS**: `DemandGuardProbabilisticModel` multi-quantile ($P10, P50, P90$) regressors and Tweedie support implemented. | `tests/test_model.py::test_probabilistic_model_monotonicity` |
| **T22** | `src/demandguard/model.py` | **SUCCESS**: `HybridAdaptiveForecaster` combining LightGBM with B2 moving averages and online bias correction ($\beta_t$) implemented. | `tests/test_model.py::test_hybrid_adaptive_forecaster` |
| **T23** | `src/demandguard/splits.py` | **SUCCESS**: 4-fold multi-season cross-validation generator covering Spring, Summer, Autumn, and Winter peaks added. | `tests/test_splits.py` |
| **T24** | `src/demandguard/inventory.py` | **SUCCESS**: `solve_stochastic_inventory_milp` implemented minimizing expected costs across quantile scenarios. | `tests/test_inventory.py::test_stochastic_inventory_milp` |
| **T25** | `src/demandguard/policies.py` | **SUCCESS**: Dynamic quantile-spread safety stock policy ($SS_{it} \propto P90 - P10$) implemented. | `tests/test_policies.py::test_quantile_spread_safety_stock` |
| **T26** | `src/demandguard/simulation.py` | **SUCCESS**: Multi-week pipeline and stochastic lead-time inventory simulation added. | `tests/test_simulation.py::test_stochastic_pipeline_simulation` |
| **T27** | `src/demandguard/api.py` | **SUCCESS**: Asynchronous background optimization job execution (`POST /reorder/async`) and polling (`GET /jobs/{id}`) added. | `tests/test_api.py::test_api_async_reorder` |
| **T28** | `src/demandguard/monitoring.py` | **SUCCESS**: Population Stability Index (PSI) and Kolmogorov-Smirnov distribution drift detection implemented. | `tests/test_monitoring.py::test_psi_drift_detection` |
| **T29** | `tests/` | **SUCCESS**: Expanded test suite to 41/41 unit and integration tests passing with 100% success rate. | `pytest` (41 passed, 0 failures), `ruff check` (clean) |
| **T30** | `docs/`, `tasks/todo.md` | **SUCCESS**: Decisions log updated (D17), progress log updated, todo list synced, improvement plan artifact delivered. | `docs/09_DECISIONS_LOG.md`, `docs/10_PROGRESS_LOG.md`, `tasks/todo.md` |

