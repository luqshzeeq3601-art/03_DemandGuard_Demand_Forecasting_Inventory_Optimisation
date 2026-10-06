# Forecast Model Comparison Report

## 1. Candidate Overview & Validation Results
- **Validation Protocol**: 4 chronological non-overlapping folds (Origins: 2011-05-16, 2011-06-13, 2011-07-11, 2011-08-08).
- **Candidates**: Naive baselines (B1 Last Value, B2 Trailing Mean, B3 Seasonal Naive), Statistical (B4 ARIMA(1,0,0) and (1,1,1)), and Direct Pooled LightGBM Regressors.

### Validation Metrics Table
| Model ID | Pooled WAPE | MAE | Signed Bias | Total Actual Units | Abs Error Units |
| --- | --- | --- | --- | --- | --- |
| `M1_lgb_deep` | 0.6320 | 208.99 | +0.0009 | 158,724 | 100,313.0 |
| `M1_lgb_default` | 0.6334 | 209.46 | -0.0214 | 158,724 | 100,539.0 |
| `M1_lgb_small` | 0.6421 | 212.32 | +0.0366 | 158,724 | 101,912.5 |
| `M1_lgb_fast` | 0.6450 | 213.29 | +0.0120 | 158,724 | 102,380.3 |
| `B2` | 0.6722 | 222.27 | +0.0237 | 158,724 | 106,687.5 |
| `B1` | 0.7250 | 239.75 | -0.0564 | 158,724 | 115,082.0 |
| `B4_arima_111` | 0.7344 | 242.85 | +0.1893 | 158,724 | 116,569.9 |
| `B4_arima_100` | 0.8201 | 271.17 | +0.2981 | 158,724 | 130,163.8 |
| `B3` | 1.0687 | 353.40 | +0.4045 | 158,724 | 169,634.0 |

## 2. Champion Selection
- **Selected Champion**: `M1_lgb_deep`
- **Rationale**: Lowest pooled validation WAPE (0.6320).
- **Validation WAPE**: `0.6320`
- **Chosen Safety Stock Factor ($k$)**: `1.0`
- **Selection provenance**: This table uses the current saved selection record and CSVs. D16 describes an earlier comparison; D21 records that the v0.1 artifact was refit with default parameters. Consult artifact metadata for the actual fitted parameters, not the legacy model label.

## 3. Final Test Holdout Evaluation (12 Weeks Out-of-Sample)
| Model ID | Holdout WAPE | Holdout MAE | Signed Bias | Actual Units | Total Error | Status vs ML |
| --- | --- | --- | --- | --- | --- | --- |
| `B2` | 0.5777 | 250.67 | -0.1523 | 156,206 | 90,241.5 | 11.2% lower error than ML |
| `B4` | 0.6423 | 278.68 | +0.0232 | 156,206 | 100,326.4 | 1.3% lower error than ML |
| `CHAMPION_M1_lgb_deep` | 0.6506 | 282.30 | -0.3053 | 156,206 | 101,627.5 | ML bias -30.53% |
| `B1` | 0.7090 | 307.64 | -0.0598 | 156,206 | 110,750.0 | 9.0% higher error than ML |
| `B3` | 1.0693 | 463.97 | +0.5044 | 156,206 | 167,029.0 | 64.4% higher error than ML |

## 4. Feature Ablation Study (Validation Folds)
| Configuration | Feature Count | Validation WAPE | Validation MAE | Validation Bias |
| --- | --- | --- | --- | --- |
| `A_Lags_Calendar_Only` | 14 | 0.6502 | 215.01 | -0.0165 |
| `B_Lags_Calendar_Rolling (Full)` | 24 | 0.6219 | 205.63 | -0.0139 |

## 5. Latency & Runtime Benchmarks
- **Platform**: CPU (Local Host)

| SKU Scale | Training (Median / Slowest) | Inference (Median / Slowest) | MILP Solve (Median / Slowest) |
| --- | --- | --- | --- |
| **1 SKUS** | 0.018s / 0.046s | 3.6ms / 4.0ms | 26.2ms / 29.3ms |
| **10 SKUS** | 0.103s / 0.123s | 3.9ms / 4.8ms | 43.1ms / 57.8ms |
| **30 SKUS** | 0.117s / 0.157s | 3.1ms / 4.1ms | 58.9ms / 119.8ms |

## 6. Scientific Observations & Root Cause Analysis
1. **Validation Performance**: The saved champion WAPE is 0.6320 versus B2 0.6722, a 5.97% relative reduction. The 10% target is missed.
2. **Holdout Comparison**: B2 WAPE is 0.5777 and the saved ML artifact WAPE is 0.6506. Comparisons above are computed from these same saved rows.
3. **Observed Bias**: The ML artifact's holdout bias is -30.53%. Seasonal transfer is a hypothesis consistent with the Q4 evaluation period, not a measured causal explanation.
4. **Evaluation Boundary**: Historical lags use closed prefixes. D21 discloses the refit-selection defect. Reproduction of this already viewed holdout is not a new untouched evaluation.
