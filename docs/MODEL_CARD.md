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

## 4. Measured Performance

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
| Model | Holdout WAPE | Holdout MAE |
| --- | --- | --- |
| Trailing 4-Week Mean (B2) | 0.5777 | 250.67 |
| ARIMA (B4) | 0.6423 | 278.68 |
| Last Value (B1) | 0.7090 | 307.64 |
| LightGBM Champion (M1) | 0.7107 | 308.37 |
| Seasonal Naive (B3) | 1.0693 | 463.97 |

### 12-Week Inventory Simulation Outcomes (Synthetic SCU)
| Replenishment Policy | Net Realised Cost (SCU) | Fill Rate | Unmet Units | Breaches |
| --- | --- | --- | --- | --- |
| **P1 (MILP + B2 Forecast)** | **332,830.56** | **70.52%** | **46,054** | **0** |
| P0 (Constrained Heuristic Rule) | 337,964.86 | 69.66% | 47,393 | 0 |
| P2 (MILP + LightGBM Forecast) | 364,193.66 | 65.52% | 53,866 | 0 |

## 5. Ethical & Scientific Considerations
- **No Data Fabrication**: Results represent actual measured performance. When simple trailing mean outperformed ML on the test holdout, it was reported transparently.
- **Physical Feasibility**: The MILP integer formulations enforce pre-demand warehouse capacity and committed-order reservations ($I_0 + A_1 + Q_1 \le C$), guaranteeing 0 delivery overflow occurrences.
