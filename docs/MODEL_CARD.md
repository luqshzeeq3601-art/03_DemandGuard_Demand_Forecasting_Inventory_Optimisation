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
| **O3** | ML forecast superiority | Same-row baseline comparison | At least 10% lower WAPE | Validation gain 5.97%; viewed holdout ML 12.62% worse than B2 | **Missed** | D21 refit limitation remains disclosed; no new untouched test. |
| **O4** | Feasible Orders | Physical & financial constraints strictly respected | 0 breaches, integer orders | 0 capacity breaches, 0 budget violations across all 12 weeks | ✅ **Met** | Pre-demand bounds and committed-order arrival space protection ($I_0 + A_1 + Q_1 \le C$) verified. |
| **O5** | Inventory cost reduction | Total SCU and fill-rate comparison | At least 5% lower cost, non-worse fill | P1 cost +0.67%; fill 68.05% vs P0 69.66%; 2 unproven solves | **Missed** | Source: current main simulation CSV; separate historical stress runs are not pooled. |
| **O6** | Reproducible engineering | Tests, lint, CLI, API, container and CI | Passing required checks | Report regression passes; Docker runtime job prepared | **Runtime proof pending** | Previous CI build passed; candidate runtime job and public serving remain unverified. |
| **O7** | Chat-Independent Docs | Specs, logs, runbooks, and decisions self-contained | Markdown source of truth | Comprehensive specs, logs, and runbooks | ✅ **Met** | Markdown documentation complete and fully self-contained. |

## 5. Current packaged-artifact results

These tables use the saved files identified by [the evidence manifest](../reports/evidence_manifest.json). D21 discloses the v0.1 refit-selection defect: the legacy M1_lgb_deep label represents an artifact with 31 leaves and 80 trees. Earlier decision-log and exploratory-run figures remain historical evidence.

### A. Validation

| Model ID | Validation WAPE | MAE (units) | Bias |
| --- | --- | --- | --- |
| M1_lgb_deep | 0.6320 | 208.99 | +0.0009 |
| M1_lgb_default | 0.6334 | 209.46 | -0.0214 |
| M1_lgb_small | 0.6421 | 212.32 | +0.0366 |
| M1_lgb_fast | 0.6450 | 213.29 | +0.0120 |
| B2 | 0.6722 | 222.27 | +0.0237 |
| B1 | 0.7250 | 239.75 | -0.0564 |
| B4_arima_111 | 0.7344 | 242.85 | +0.1893 |
| B4_arima_100 | 0.8201 | 271.17 | +0.2981 |
| B3 | 1.0687 | 353.40 | +0.4045 |

### B. Previously viewed holdout

| Model ID | Holdout WAPE | MAE (units) | Bias |
| --- | --- | --- | --- |
| B2 | 0.5777 | 250.67 | -0.1523 |
| B4 | 0.6423 | 278.68 | +0.0232 |
| CHAMPION_M1_lgb_deep | 0.6506 | 282.30 | -0.3053 |
| B1 | 0.7090 | 307.64 | -0.0598 |
| B3 | 1.0693 | 463.97 | +0.5044 |

The ML artifact has 12.62% higher WAPE than B2. Its observed bias is -30.53%. This does not establish a causal explanation for the seasonal error, and reproducing the viewed holdout does not create a new untouched test.

### C. Main inventory simulation

| Policy | Total simulated cost (SCU) | Fill rate | Unmet units | Unproven solves |
| --- | --- | --- | --- | --- |
| P0_Rule | 337,964.86 | 69.66% | 47,393 | 0 |
| P1_MILP_Baseline | 340,215.08 | 68.05% | 49,909 | 2 |
| P2_MILP_Champion | 355,391.66 | 66.79% | 51,872 | 0 |

P1 total cost is +0.67% versus P0 and its fill rate is 68.05% versus 69.66%. P2 total cost is +5.16%. O3/O5 improvement targets remain missed. Costs are invented scenario units, not actual financial savings. Separate stress/v0.2 runs must not be mixed into this headline.

## 7. Historical exploratory v0.2 experiment results (decision D18)

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
3. These are separately recorded D23 exploratory-run results; they are not the current main CSV headline. The stochastic optimiser cannot prove a solution within the 10s limit in any week, so under the spec it places no orders. Its earlier 360k figure came from executing unproven solutions. Quantile-spread safety stock (P5) did worse than the k x std rule (P3), because the P50 forecast itself is biased low.
4. The P50 bundle is servable from `artifacts/v02/` (`DEMANDGUARD_MODEL=v02`, or `forecast --artifact-dir artifacts/v02`). The default remains the v0.1 champion.
