# 05. Forecast experiment plan

## 1. Question and protocol

Can lag-based LightGBM predict four future weekly SKU sales better than simple rules and ARIMA under a fixed chronological protocol?

Use the cohort and exact origins from 03_DATA_SPEC.md. All models see the same history and target weeks. Never use random train/test splits on stacked SKU rows.

## 2. Candidate forecasts

| ID | Forecast | Definition |
| --- | --- | --- |
| B1 | Last observed week | Repeat y(c) for all horizons |
| B2 | Trailing four-week mean | Repeat mean(y(c-3)..y(c)) |
| B3 | Annual seasonal naive | y(c+h-52) for horizon h; available under the 60-week contract |
| B4 | Per-SKU ARIMA | Compare fixed orders (1,1,1) and (1,0,0); choose by validation, not holdout |
| M1 | Pooled LightGBM | One direct regressor with SKU identity and horizon 1..4 as features |

ARIMA fit failures must be logged per SKU/fold. A deterministic trailing-mean fallback is part of the B4 policy; report its failure count and score the complete combined policy. Do not delete difficult products from the comparison.

For later origins under a frozen ARIMA policy, update its filtered state using only newly observed weeks without re-estimating coefficients. Store or reconstruct that state from the saved training cutoff; do not repeatedly relabel the original four-step forecast as a new origin's forecast. Serving requires the update-history bridge defined in the technical contract.

## 3. Direct forecast training rows

For each supported SKU, a training row has observed origin c, horizon h and target y(c+h). All numeric history features use observations through c only.

- Historical lags: offsets 0, 1, 2, 3, 7, 12, 25 and 51 from c.
- Rolling mean/std over the last 4, 13 and 26 observed weeks, including c.
- Fraction of zero-sale weeks in those rolling windows.
- Simple trend: trailing 4-week mean minus preceding 4-week mean.
- Origin calendar and target calendar: week-of-year, month and horizon.
- SKU category from the frozen cohort; persist the category mapping.

Use at least 60 observed weeks before a training/serving origin. Targets and features must be aligned explicitly; a groupby shift alone does not establish a valid calendar.

Do not use future actual quantities, target-week selling price, a full-dataset average, future product popularity or centred rolling statistics. Calendar dates are known ahead; future promotions are not.

## 4. Backtesting and model selection

1. At each of four validation origins, refit candidates using only labels available by that cutoff.
2. Generate the next four weeks without reading those actual target values.
3. Align all predictions on SKU/origin/horizon keys; score common complete coverage.
4. Combine validation errors using total absolute error / total actual units across all validation rows. Also report each fold and horizon separately.
5. Select the lowest pooled validation WAPE among B1-B4 and M1. If within 1% relative WAPE, favour the simpler/faster model; record the comparison and tolerance.
6. Aim for M1 to reduce strongest-baseline WAPE by >=10%. If it does not, report that honestly; the winning baseline may be the champion.

If pooled actual validation units are zero, WAPE and bias are unavailable: rank candidates by MAE under the same 1% simplicity rule. If the strongest baseline's error is zero, relative improvement is unavailable; report absolute error differences and do not divide by zero.

Training labels with target dates after a fold cutoff are excluded separately for every horizon. Fit all transformations using the fold training data. Use a custom grouped calendar splitter; generic row-based TimeSeriesSplit is insufficient for stacked SKU/horizon rows.

## 5. Bounded tuning

- Seed: 42. CPU only.
- LightGBM: squared-error objective; start with conservative tree size and limited estimators.
- Maximum 12 predeclared parameter configurations over learning rate, estimator count, num_leaves and min_child_samples.
- Record the grid before running. Do not expand it merely because holdout performance disappoints.
- A fixed estimator count avoids using the scored fold as an early-stopping set. If early stopping is introduced, create a separate temporal training-internal stopping window and record it.
- One bounded feature ablation: lags/calendar versus lags/calendar/rolling statistics. Count configurations across the total 12-run-config budget.
- Clip negative predictions to zero for every model before comparison and record clipping counts.

## 6. Metrics

| Metric | Definition | Reporting |
| --- | --- | --- |
| WAPE | sum(abs(y-yhat)) / sum(y) | Primary pooled metric; unavailable for zero actual total |
| MAE | mean(abs(y-yhat)) | Overall, per horizon and per SKU |
| Bias | sum(yhat-y) / sum(y) | Signed; unavailable for zero actual total |
| Coverage | rows returned / required rows | Must be 100% for a valid candidate policy |
| Runtime | Wall-clock training/inference seconds | Hardware and model size recorded |

Show both pooled metrics and product distributions so high-volume products do not hide weak low-volume performance. Avoid MAPE on zero-sales weeks. MASE is optional only if its seasonal scaling denominator is computed from training history and is nonzero.

## 7. Final holdout

1. Freeze model type, parameters, features, cohort, fallback, clipping and inventory settings.
2. Fit the evaluated champion through c0=N-12 and save its bundle.
3. Score three nonoverlapping four-week holdout windows. Keep model weights and preprocessing fixed; update lag inputs only from already observed history.
4. Run the weekly inventory simulator over the same final twelve weeks under the separately frozen policy protocol.
5. Report success or failure against targets. Do not choose a new champion or retune from these results.

The final report must state that twelve weeks and one catalogue provide limited evidence. Fold variability is descriptive; do not present it as a broad confidence guarantee.

## 8. Required outputs

- `reports/forecast_validation.csv`: model/fold/horizon/SKU metrics and fit failures.
- `reports/forecast_predictions.parquet`: model, SKU, origin, target, horizon, actual, prediction and split.
- `reports/forecast_comparison.md`: selection reason, feature ablation, runtime and limitations.
- `artifacts/champion/`: bundle defined in the technical design.
- `docs/MODEL_CARD.md`: created during release with actual measured results; not fabricated during planning.

Do not refit on all data while labelling the resulting artifact with holdout scores from a different model. A later full-history refit requires a new version and explicit provenance.

## 9. v0.2 evaluation protocol (D18)

The v0.1 champion under-forecast the 2011-09-12 to 2011-11-28 test window by 27.4%. That window has been viewed, and the dataset ends 2011-11-28, so v0.2 has no unseen holdout.

### A. Temporal protocol

- A 2010 Q4 validation fold is not possible. The 60-week history contract puts the first origin at 2011-01-24, and Q4 2010 also lies inside the cohort-selection prefix.
- Selection uses the four manifest validation origins (2011-05-16, 2011-06-13, 2011-07-11, 2011-08-08). Their last target is the c0 cutoff (2011-09-05); the holdout starts 2011-09-12.
- `generate_pre_holdout_validation_origins` (D20) is the only fold generator for new experiments. It asserts every target precedes the holdout.
- The selection record is written before any test-window scoring. Test-window results are labelled EXPLORATORY and cannot support an O3/O5 claim.

### B. Declared candidates (fixed before running)

| ID | Features | Objective | Notes |
| --- | --- | --- | --- |
| B2 | - | Trailing 4-week mean | Reference |
| M1_v01_fast | v0.1 set | L2 | lr 0.08, 15 leaves, 60 trees, min child 10 |
| M2_l2 | v0.1 set + lag_52, rolling_mean_52, momentum_4_13, Fourier week-of-year | L2 | Same tree settings; recency weights 0.98^weeks |
| M2_tweedie | as M2_l2 | Tweedie, variance power 1.2 | Same tree settings and weights |
| M2_q50 | as M2_l2 | Quantile 0.5 | P10/P90 fitted alongside for the stochastic policy |
| H_blend | - | 0.5 x M2_l2 + 0.5 x B2 | Fixed weight, no bias correction (no unbiased bias signal exists inside a fold) |

Selection: lowest pooled validation WAPE; a simpler candidate within 1% relative WAPE wins. Simplicity order: B2, M1_v01_fast, M2_l2, M2_tweedie, M2_q50, H_blend.

### C. Outputs

- `reports/v02_validation.csv`, `artifacts/v02/selection_record.json`.
- `reports/v02_exploratory_holdout_forecast.csv`, `reports/v02_exploratory_simulation.csv`, `reports/v02_experiment.md`.
- Command: `python -m demandguard.cli experiment-v02`.
