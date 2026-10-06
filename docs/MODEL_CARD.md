# DemandGuard Model Card

## 1. Model Details
- **Model Name**: DemandGuard Pooled Direct Regressor
- **Architecture**: Gradient Boosted Decision Trees (LightGBM)
- **Model Version**: v0.1.0 (`M1_lgb_deep`)
- **Training Algorithm**: Direct-horizon pooled regression with categorical SKU embeddings and causal historical lags.
- **Developer**: DemandGuard Project Team (Google Antigravity Session)
- **License**: CC BY 4.0 / MIT

## 2. Intended Use & Scope
- **Primary Use Case**: Multi-horizon (4-week) product sales forecasting to drive weekly integer replenishment optimization in warehouse environments.
- **Target Population**: Established catalog items with at least 60 weeks of continuous sales history.
- **Out of Scope**: Real-time intraday trading, cold-start product introductions (<60 weeks history), automated purchase execution without human inventory manager review.

## 3. Training & Evaluation Protocol
- **Dataset**: UCI Online Retail II (UK retail transactions).
- **Cohort Window**: First 60 complete weeks (2009-12-07 to 2011-01-24) to select 30 established products without future target leakage.
- **Total Complete Weeks**: 102 weeks (2009-12-07 to 2011-11-28).
- **Validation Protocol**: 4 chronological non-overlapping folds (Origins: 2011-05-16, 2011-06-13, 2011-07-11, 2011-08-08).
- **Final Holdout Split**: 12 complete calendar weeks (2011-09-12 to 2011-11-28) evaluated strictly out-of-sample after model selection freeze.

## 4. Objectives & Status Audit Matrix

| ID | Objective | Description | Target | Achieved Result | Status | Plain Explanation |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **O1** | Trustworthy Weekly Data | Reconciled, leak-free panel from raw transactions | 100+ weeks, $\ge 10$ SKUs | 102 complete weeks, 30 SKUs, 9,013,090 panel units | ⚠️ **Mostly Met** | Panel is 100% verified. Gap of 358,320 units from clean data (9,371,410) is due to dropping partial boundary weeks (Dec 1–6, 2009 & Dec 5–9, 2011). |
| **O2** | 4-Week Forecasts | Nonnegative, finite multi-step predictions | 100% coverage, breakdown reporting | 480 val + 360 holdout predictions | ⚠️ **Mostly Met** | Predictions exist and are valid; granular breakdowns by horizon and SKU provided in reports. |
| **O3** | ML Forecast Superiority | LightGBM outperforms best simple baseline | $\ge 10\%$ WAPE reduction | Val: +7.76% (0.6200 vs 0.6722)<br>Holdout: -23.0% (0.7107 vs 0.5777)<br>v0.2 M2_q50: val +12.1%; test (exploratory) -9.3% | ❌ **Missed (Stretch)** | **Missed**: LightGBM failed to beat the trailing 4-week mean on the 12-week test holdout. |
| **O4** | Feasible Orders | Physical & financial constraints strictly respected | 0 breaches, integer orders | 0 capacity breaches, 0 budget violations across all 12 weeks | ✅ **Met** | Pre-demand bounds and committed-order arrival space protection ($I_0 + A_1 + Q_1 \le C$) verified. |
| **O5** | Inventory Cost Reduction | Optimised replenishment reduces total supply chain cost | $\ge 5\%$ cost reduction, $\ge$ fill rate | P1: -0.85% (335.1k vs 338.0k SCU), fill 70.16% vs 69.66%<br>P2: +7.61% cost | ❌ **Missed (Stretch)** | **Missed**: re-measured with the reproducible solver (D23). The published 1.52% figure came from time-limited solves (D22). The ML-driven P2 increased cost. |
| **O6** | Reproducible Engineering | Test suite, linting, CLI, API, container & CI | Passing tests, clean lint, verified contracts | 47 passing tests, clean Ruff lint, API & container verified | ⚠️ **Mostly Met** | Unit/integration tests pass. Local git initialized; live remote CI requires external runner. |
| **O7** | Chat-Independent Docs | Specs, logs, runbooks, and decisions self-contained | Markdown source of truth | Comprehensive specs, logs, and runbooks | ✅ **Met** | Markdown documentation complete and fully self-contained. |

## 5. Measured Performance

### Validation Backtesting (Pooled WAPE, 480 predictions)
| Candidate Model | WAPE | MAE (Units) | Bias |
| --- | --- | --- | --- |
| **LightGBM Deep (Champion)** | **0.6200** | **205.02** | **-0.0253** |
| LightGBM Fast | 0.6206 | 205.20 | -0.0236 |
| LightGBM Default | 0.6246 | 206.56 | -0.0436 |
| Trailing 4-Week Mean (B2) | 0.6722 | 222.27 | +0.0237 |
| Last Observed Value (B1) | 0.7250 | 239.75 | -0.0564 |
| ARIMA (1,1,1) (B4) | 0.7344 | 242.85 | +0.1893 |
| Seasonal Naive (B3) | 1.0687 | 353.40 | +0.4045 |

### Final 12-Week Test Holdout (360 predictions)
| Model | Holdout WAPE | Holdout MAE | Signed Bias | Status vs ML |
| --- | --- | --- | --- | --- |
| **Trailing 4-Week Mean (B2)** | **0.5777** | **250.67** | **-0.1523** | **Beat ML by 18.7% lower error** |
| ARIMA (B4) | 0.6423 | 278.68 | +0.0232 | Beat ML |
| Last Value (B1) | 0.7090 | 307.64 | -0.0598 | Beat ML |
| **LightGBM Champion (M1)** | **0.7107** | **308.37** | **-0.2736** | **Lost on test holdout (-27.4% bias)** |
| Seasonal Naive (B3) | 1.0693 | 463.97 | +0.5044 | Baseline |

### 12-Week Inventory Simulation Outcomes (Synthetic SCU)
| Replenishment Policy | Net Realised Cost (SCU) | Fill Rate | Unmet Units | Breaches | Cost Reduction vs P0 |
| --- | --- | --- | --- | --- | --- |
| **P1 (MILP + B2 Forecast)** | **335,099.70** | **70.16%** | **46,617** | **0** | **-0.85% (2,865.16 SCU saved)** |
| P0 (Constrained Heuristic Rule) | 337,964.86 | 69.66% | 47,393 | 0 | Baseline |
| P2 (MILP + LightGBM Forecast) | 363,667.40 | 65.60% | 53,730 | 0 | +7.61% (Cost Increased) |

## 6. Scientific Findings & Root Cause Analysis

1. **Validation vs Holdout Divergence (Seasonal Distribution Shift)**:
   - The 4 validation folds (Origins 74, 78, 82, 86) spanned May to August 2011 (summer sales with steady patterns), where LightGBM outperformed B2 by 7.76% (0.6200 vs 0.6722).
   - The test holdout spanned September to November 2011 (the Q4 UK Christmas pre-holiday surge). LightGBM exhibited severe negative bias (-27.36%), under-forecasting the rapid demand surge. In contrast, the trailing 4-week mean (B2) adapted faster to the rising trend.
2. **Inventory Budget Constraint Effect**:
   - Across all policies, unit fill rates hover around 65%–70% because the synthetic weekly budget is tight relative to peak Q4 demand.
   - Unmet demand penalties ($p=5.0$ SCU) account for ~70% of total supply chain costs, heavily penalizing under-forecasting.
3. **Selection Rule Compliance**:
   - `M1_lgb_deep` (0.6200) and `M1_lgb_fast` (0.6206) were within 0.09% WAPE. `M1_lgb_deep` was selected for minimal absolute error, though `M1_lgb_fast` is the canonical simpler model under the 1% simplicity rule (documented in Decision D16). The frozen artifact was actually refit with default parameters (lr 0.05, 31 leaves, 80 trees), not the `M1_lgb_deep` settings (D21); the published holdout numbers describe that refit model.
4. **Hardware & Latency**:
   - Model inference latency: <0.05s for 30 SKUs.
   - PuLP CBC integer solve runtime: up to 7s per 30-SKU holdout solve at the 0.1% gap (D23). Without a gap, most solves hit the 10s limit (D22).

## 7. v0.2 experiment results (decision D18)

Command: `python -m demandguard.cli experiment-v02`. Evidence: [reports/v02_experiment.md](../reports/v02_experiment.md).

**Pre-holdout validation (selection evidence, 480 predictions):**

| Candidate | WAPE | Bias |
| --- | --- | --- |
| **M2_q50** (quantile median, v0.2 features) | **0.5910** | -0.167 |
| M2_tweedie | 0.6149 | -0.041 |
| M1_v01_fast | 0.6206 | -0.024 |
| M2_l2 | 0.6302 | -0.010 |
| H_blend (0.5 M2_l2 + 0.5 B2) | 0.6350 | +0.007 |
| B2 | 0.6722 | +0.024 |

M2_q50 was frozen as champion. It is 12.1% better than B2 on validation, which meets the O3 target **on validation only**.

**Test window, EXPLORATORY (already viewed in v0.1; cannot support an O3/O5 claim):**

| Candidate | WAPE | Bias |
| --- | --- | --- |
| B2 | **0.5777** | -0.152 |
| H_blend | 0.5797 | -0.237 |
| M2_q50 (champion) | 0.6316 | -0.421 |
| M2_l2 | 0.6407 | -0.323 |
| M2_tweedie | 0.6458 | -0.319 |
| M1_v01_fast | 0.6866 | -0.268 |

| Policy (12 weeks, EXPLORATORY) | Cost (SCU) | vs P0 | Fill rate | Unproven solves |
| --- | --- | --- | --- | --- |
| P0 rule | 337,965 | - | 69.7% | - |
| P1 MILP + B2 | 335,100 | -0.8% | 70.2% | 0 of 12 |
| P3 MILP + M2_q50 | 399,639 | +18.2% | 59.4% | 1 of 12 |
| P4 stochastic MILP (P10/P50/P90) | 685,616 | +102.9% | 12.3% | 12 of 12 (time limit; no orders placed) |
| P5 MILP + M2_q50 + quantile-spread safety stock | 422,770 | +25.1% | 55.4% | 1 of 12 |

**Findings:**

1. The v0.2 features improved validation error but did not fix the peak-season under-forecast. Every ML candidate still under-forecasts the test window by 27-42%. The quantile median is the worst: it targets the median, and demand is right-skewed.
2. Only the B2 blend comes close to B2 on the test window. No candidate beats it.
3. Policy results are now reproducible (D23). The stochastic optimiser cannot prove a solution within the 10s limit in any week, so under the spec it places no orders. Its earlier 360k figure came from executing unproven solutions. Quantile-spread safety stock (P5) did worse than the k x std rule (P3), because the P50 forecast itself is biased low.
4. The P50 bundle is servable from `artifacts/v02/` (`DEMANDGUARD_MODEL=v02`, or `forecast --artifact-dir artifacts/v02`). The default remains the v0.1 champion.
