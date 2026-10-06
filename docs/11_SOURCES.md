# 11. Sources and evidence

## 1. Portfolio workbook

- File: `../Classical_ML_Portfolio_Plan_Malaysia.xlsx` relative to the project root (two parent levels from this docs file).
- Inspected: 6 October 2026, Malaysia time; read-only.
- SHA-256 at inspection: `DEA7706770BFFAF9980015F15225121AF2AF18744871109EE0412D7B3B781900`.

| Location | Observed content | Use |
| --- | --- | --- |
| Project Tracker!A6:B6 | Priority 3; demand forecasting + inventory optimisation | Identifies the next project |
| Project Tracker!C6 | Mattel, DKSH, GAR, PetBacker | Workbook employer relevance, not live vacancy verification |
| Project Tracker!D6 | Lag features + LightGBM vs Prophet/ARIMA, backtesting | Forecasting comparison plan; choose ARIMA for MVP |
| Project Tracker!E6 | PuLP LP for reorder quantities | Constrained reorder component; integers require MILP |
| Project Tracker!F6 | data.gov.my / OpenDOSM | Investigated source suitability and documented retail alternative |
| Project Tracker!G4:G6 | Not started | Stale tracker values; user reports projects 1 and 2 completed |
| Engineer Checklist!A4:A11 | Clean source/tests, metrics, tracking, API, Docker, cloud, monitoring, impact | Engineering deliverables; cloud deferred until local proof |
| Job Postings!A1 | Source dated 5 October 2026 | Workbook snapshot date; no current-job guarantee |

## 2. Official external references

Checked on 6 October 2026. Record updated versions at implementation time where libraries have changed.

| Source | Verified fact or supported decision | Link |
| --- | --- | --- |
| UCI Online Retail II | Transaction benchmark, source metadata, cancellation conventions, license and download entry | [Dataset](https://archive.ics.uci.edu/dataset/502/online+retail+ii) |
| Dataset citation | Chen, D. (2012), Online Retail II; preserve attribution when using the data | [DOI](https://doi.org/10.24432/C5CG6D) |
| OpenDOSM retail series | Monthly aggregate sales and volume indices; no SKU/inventory fields in this inspected series | [Metadata](https://open.dosm.gov.my/data-catalogue/iowrt) |
| scikit-learn | Temporal evaluation and gap concepts; grouped forecasting still needs explicit calendar/label checks | [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) |
| LightGBM | Regression configuration and reproducibility parameters; pin installed release | [Parameters](https://lightgbm.readthedocs.io/en/stable/Parameters.html) |
| statsmodels | Official ARIMA implementation and order/exogenous-input interface | [ARIMA](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html) |
| COIN-OR PuLP | LP/MILP modelling and version-dependent solver setup; verify release rather than assuming older bundled CBC APIs | [Official repository](https://github.com/coin-or/pulp) |
| COIN-OR CBC | Open-source integer solver implementation | [Official repository](https://github.com/coin-or/Cbc) |

The single-store, weekly-horizon, cohort, cost, budget and target choices are project design assumptions. They are not attributed to these sources as observed business facts.

## 3. Dataset-granularity conclusion

The workbook's Malaysian source suggestion is useful for aggregate forecasting. The inspected retail series does not supply the product-level quantities needed by this MVP. A separate retail benchmark makes forecast-to-reorder evaluation possible, provided the synthetic inventory inputs and geographic limitation remain explicit.

Do not join unrelated contemporary Malaysian macro indicators onto historical UK SKU rows just to make a local relevance claim. A Malaysian extension needs a compatible local dataset and a revised, separately evaluated data contract.

## 4. Verification boundary

This planning session verified source descriptions and current technical documentation. It did not download the retail workbook, profile its actual sheets, install dependencies, audit the claimed completion of prior projects or check live job postings. Those statements must remain distinct in future reports.
