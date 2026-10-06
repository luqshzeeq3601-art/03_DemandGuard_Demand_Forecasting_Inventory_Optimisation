# 10. Progress log

## 1. Current state

- Phase: **v0.1 released; v0.2 evaluated (exploratory); D22 resolved by D23**.
- Planning files: verified and updated.
- Implementation tasks completed: **18 of 18 (100%)**.
- Next task: none scheduled (T22 online bias correction remains partial).
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

## 3. v0.2 tasks: corrected status and evidence (6 Oct 2026)

Commit `568d4ba` logged T19-T30 as SUCCESS on unit tests alone and claimed Tweedie support and an improvement-plan file that did not exist. The rows below replace that log. Decisions: D17-D22.

| Task | Status | Command / evidence | Note |
| :--- | :--- | :--- | :--- |
| **T19** | WITHDRAWN | Function and tests removed | Leaked future data; no stockout signal (D19) |
| **T20** | Evaluated | `experiment-v02` -> `reports/v02_validation.csv` | Used by M2 candidates |
| **T21** | Evaluated | same | Tweedie added as `M2_tweedie` |
| **T22** | Partial | same | Fixed blend evaluated; online bias correction not |
| **T23** | Replaced | `pytest tests/test_splits.py` | Old generator overlapped holdout (D20) |
| **T24** | Exploratory, blocked | `reports/v02_exploratory_simulation.csv` | Pre-demand capacity added; D22 open |
| **T25** | Not evaluated | - | Not used by any policy |
| **T26** | Not evaluated | - | Not used by any simulation |
| **T27** | Done | `tests/test_api.py::test_api_async_reorder` | In-memory jobs only |
| **T28** | Not integrated | `tests/test_monitoring.py` | Not called by `monitor` |
| **T29** | Done | `pytest` (43 passed), `ruff check src tests` clean | Adds selection-rule and fold-overlap tests |
| **T30** | Done | Docs 05, 06, 08, 09, README, model card, todo | Corrections recorded |
| **T31** | Done | `python -m demandguard.cli experiment-v02` (about 6 min, exit 0, run twice) | See below |

### T31 results

- Validation (pre-holdout, frozen before test scoring): champion **M2_q50** WAPE 0.5910 vs B2 0.6722, a 12.1% reduction. Forecast metrics were identical across both runs.
- Test window (EXPLORATORY): B2 0.5777, H_blend 0.5797, M2_q50 0.6316 (bias -42%). No candidate beats B2.
- Simulation (EXPLORATORY), run 2: P0 337,965; P1 333,580 (-1.3%); P3 399,109 (+18.1%); P4 360,360 (+6.6%). Zero capacity breaches. P1 cost was 340,164 in run 1 (D22).
- Evidence: `reports/v02_experiment.md`, `reports/v02_validation.csv`, `reports/v02_exploratory_holdout_forecast.csv`, `reports/v02_exploratory_simulation.csv`, `artifacts/v02/selection_record.json`.

### Blocker found

- **D22**: 20 of 24 v0.1 MILP solves hit the 10s CBC limit but report `Optimal`. Three runs of the unchanged v0.1 `simulate` gave P1 costs of 332,831, 340,164 and 333,580, so the published 1.52% P1 saving is not reproducible.
- Next task: **T32**, resolve D22, then re-measure every policy.

## 4. Session: 6 Oct 2026, T24-T28 and T32-T33 completion

| Task | Command | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **T32** | Captured 24 real holdout MILP inputs; benchmarked `gapRel` 1e-4 and 1e-3 twice each | 1e-3: max 7s per solve; identical objectives and orders across runs | `src/demandguard/inventory.py` (D23) |
| **T32** | `python -m demandguard.cli simulate` twice | Identical CSVs, 30s each. P0 337,964.86; P1 335,099.70 (-0.85%); P2 363,667.40 (+7.61%); 0 breaches; 0 unproven solves | `reports/holdout_simulation_metrics.csv` |
| **T32** | `run_k_factor_validation_grid`, `run_budget_stress_scenarios`, `report` | k=1.0 still lowest validation cost (55,684.92). Stress 0.6x P2 had 3 unproven solves (zero orders those weeks) | `reports/k_factor_validation.csv`, `reports/inventory_stress_scenarios.csv`, `reports/inventory_simulation_report.md` |
| **T24/T25** | `python -m demandguard.cli experiment-v02` (182s, exit 0) | P1 335,100 (-0.8%); P3 399,639 (+18.2%); P4 not executable (12/12 time-limited); P5 422,770 (+25.1%). Forecast metrics unchanged | `reports/v02_experiment.md`, `reports/v02_exploratory_simulation.csv` |
| **T26** | `pytest tests/test_simulation.py` | Lead-time bug fixed; equivalence with the standard step verified | D25 |
| **T28** | `pytest tests/test_monitoring.py` | PSI and KS reported by `monitor` | D25 |
| **T33** | CLI `forecast --artifact-dir artifacts/v02`; API `/forecast` and `/ready` with `DEMANDGUARD_MODEL=v02` | 8 predictions, `model_version` M2_q50, ready; untrusted name rejected | D25 |
| All | `pytest` / `ruff check src tests` | 47 passed / clean | - |

Remaining: T22 online bias correction is unevaluated, because no unbiased bias signal exists inside a fold. The data has no unseen holdout left for an O3/O5 claim (D18).
