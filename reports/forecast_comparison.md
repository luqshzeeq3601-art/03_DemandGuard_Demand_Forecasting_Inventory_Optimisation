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

## 3. Final Test Holdout Evaluation (12 Weeks Out-of-Sample)
| Model ID | Holdout WAPE | Holdout MAE | Signed Bias | Actual Units | Total Error |
| --- | --- | --- | --- | --- | --- |
| `B2` | 0.5777 | 250.67 | -0.1523 | 156,206 | 90,241.5 |
| `B4` | 0.6423 | 278.68 | +0.0232 | 156,206 | 100,326.4 |
| `B1` | 0.7090 | 307.64 | -0.0598 | 156,206 | 110,750.0 |
| `CHAMPION_M1_lgb_deep` | 0.7107 | 308.37 | -0.2736 | 156,206 | 111,012.6 |
| `B3` | 1.0693 | 463.97 | +0.5044 | 156,206 | 167,029.0 |

## 4. Scientific Observations & Key Findings
1. **Validation Performance**: Direct pooled LightGBM achieved the lowest WAPE (0.6200), outperforming the strongest baseline B2 (0.6722) by 7.76%.
2. **Holdout Generalisation**: On the final 12-week test holdout, the trailing 4-week mean baseline B2 achieved WAPE = 0.5777, outperforming LightGBM (0.7107) due to high variance and changing trend dynamics in the retail holdout period.
3. **No Target Leakage**: All models were frozen before holdout evaluation. Historical lag updates used only closed historical prefixes.
