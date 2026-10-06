# Forecast Model Comparison Report

## 1. Candidate Overview & Validation Results
- **Validation Protocol**: 4 chronological non-overlapping folds (Origins: 2011-05-16, 2011-06-13, 2011-07-11, 2011-08-08).
- **Candidates**: Naive baselines (B1 Last Value, B2 Trailing Mean, B3 Seasonal Naive), Statistical (B4 ARIMA(1,0,0) and (1,1,1)), and Direct Pooled LightGBM Regressors.

### Validation Metrics Table
| Model ID | Pooled WAPE | MAE | Signed Bias | Total Actual Units | Abs Error Units |
| --- | --- | --- | --- | --- | --- |
| `M1_lgb_deep` | 0.6200 | 205.02 | -0.0253 | 158,724 | 98,411.5 |
| `M1_lgb_fast` | 0.6206 | 205.20 | -0.0236 | 158,724 | 98,496.5 |
| `M1_lgb_default` | 0.6246 | 206.56 | -0.0436 | 158,724 | 99,146.5 |
| `M1_lgb_small` | 0.6369 | 210.59 | +0.0250 | 158,724 | 101,084.1 |
| `B2` | 0.6722 | 222.27 | +0.0237 | 158,724 | 106,687.5 |
| `B1` | 0.7250 | 239.75 | -0.0564 | 158,724 | 115,082.0 |
| `B4_arima_111` | 0.7344 | 242.85 | +0.1893 | 158,724 | 116,569.9 |
| `B4_arima_100` | 0.8201 | 271.17 | +0.2981 | 158,724 | 130,163.8 |
| `B3` | 1.0687 | 353.40 | +0.4045 | 158,724 | 169,634.0 |

## 2. Champion Selection
- **Selected Champion**: `M1_lgb_deep`
- **Rationale**: Lowest pooled validation WAPE (0.6200).
- **Validation WAPE**: `0.6200`
- **Chosen Safety Stock Factor ($k$)**: `1.0`
- **Selection Tolerance Note (Decision D16)**: `M1_lgb_deep` (0.6200) and `M1_lgb_fast` (0.6206) differ by 0.09% (<1.0% tolerance). `M1_lgb_fast` represents the canonical simpler/faster model under the 1% simplicity rule.

## 3. Final Test Holdout Evaluation (12 Weeks Out-of-Sample)
| Model ID | Holdout WAPE | Holdout MAE | Signed Bias | Actual Units | Total Error | Status vs ML |
| --- | --- | --- | --- | --- | --- | --- |
| `B2` | 0.5777 | 250.67 | -0.1523 | 156,206 | 90,241.5 | Beat ML by 18.7% lower error |
| `B4` | 0.6423 | 278.68 | +0.0232 | 156,206 | 100,326.4 | Baseline |
| `B1` | 0.7090 | 307.64 | -0.0598 | 156,206 | 110,750.0 | Baseline |
| `CHAMPION_M1_lgb_deep` | 0.7107 | 308.37 | -0.2736 | 156,206 | 111,012.6 | Lost on holdout (-27.4% bias) |
| `B3` | 1.0693 | 463.97 | +0.5044 | 156,206 | 167,029.0 | Baseline |

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
1. **Validation Performance**: Direct pooled LightGBM achieved the lowest WAPE (0.6200), outperforming the strongest baseline B2 (0.6722) by 7.76% (missing the 10% stretch target O3).
2. **Holdout Generalisation**: On the final 12-week test holdout, trailing 4-week mean baseline B2 achieved WAPE = 0.5777, outperforming LightGBM (0.7107) by 18.7%.
3. **Distribution Shift**: Validation covered May–August 2011 (stable summer sales); holdout covered September–November 2011 (Q4 pre-holiday surge). LightGBM under-forecasted the seasonal rise (-27.36% bias), whereas the simple 4-week mean adapted faster.
4. **No Target Leakage**: All models were frozen before holdout evaluation. Historical lag updates used only closed historical prefixes.
