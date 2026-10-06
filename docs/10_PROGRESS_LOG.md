# 10. Progress log

## 1. Current state

- Phase: **v0.1 Local Release Complete**.
- Planning files: verified and updated.
- Implementation tasks completed: **18 of 18 (100%)**.
- Next task: None. Local v0.1 milestone verified and closed.
- Dataset acquired and verified: Yes (`data/raw/online_retail_II.xlsx`, SHA-256: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`).
- Forecast trained/evaluated: Yes (Validation WAPE: 0.6200 for LightGBM vs 0.6722 for B2; Holdout WAPE: 0.5777 for B2 vs 0.7107 for LightGBM).
- Inventory simulation measured: Yes (12-week holdout continuous simulation: P1 MILP baseline achieved lowest cost 332,830.56 SCU, 70.52% fill rate, 0 breaches).
- API/Docker/deployment verified: Yes (FastAPI tested with 4/4 passing tests; Dockerfile & CI workflows configured).

## 2. Session: 6 October 2026, Malaysia time (Implementation Execution)

**Starting state:** Planning handoff complete (0/18 tasks completed).
**Completed tasks:** T01 through T18.

### Key Milestones & Verification Evidence:
1. **T01 (Environment & Solver)**: Isolated Python 3.11 environment established with `pyproject.toml`, `requirements.lock.txt`, and CBC solver verified on a known test problem. Gate G0 PASSED.
2. **T02-T04 (Data Acquisition & Chronological Splits)**: UCI Online Retail II dataset downloaded (1,067,371 raw records), cleaned to 956,124 valid transactions, and aggregated via DuckDB into 102 complete calendar weeks (2009-12-07 to 2011-11-28). 30-product cohort selected from the first 60 weeks. Gate G1 PASSED.
3. **T05-T08 (Baselines, Causal Features, & Simulation)**: Naive rules B1-B3, ARIMA B4, and direct-horizon feature builder implemented. State transition simulator and P0 order-up-to rule verified with unit tests. Gate G2 PASSED.
4. **T09-T12 (MILP Solver, Validation Backtests, & Holdout Evaluation)**:
   - PuLP MILP formulation with pre-demand occupancy bounds, committed-order arrival space reservation ($I_0 + A_1 + Q_1 \le C$), and soft safety stock penalty validated against tiny exhaustive optimum. Gate G3 PASSED.
   - 4-fold chronological backtest ran across 480 predictions: LightGBM won with 0.6200 WAPE. Champion frozen in `artifacts/champion/selection_record.json`. Gate G4 PASSED.
   - Final 12-week holdout evaluation: B2 trailing mean baseline achieved 0.5777 WAPE; 12-week continuous inventory simulation proved P1 MILP saved 5,134.30 SCU (1.52% cost reduction) over P0 with 70.52% fill rate and 0 capacity breaches. Gate G5 PASSED.
5. **T13-T16 (CLI, FastAPI, CI, & Monitoring)**: CLI commands (`forecast`, `reorder`, `monitor`, `report`), FastAPI endpoints (`/health`, `/ready`, `/forecast`, `/reorder`), Dockerfile, GitHub Actions CI workflow, and anomaly monitoring verified. Gate G6 PASSED.
6. **T17-T18 (Model Card, Portfolio Report, & Release Reproduction)**: `docs/MODEL_CARD.md`, `README.md`, and Matplotlib visual comparison plots generated. 25 unit/integration tests and Ruff linting pass cleanly. Gate G7 PASSED.
