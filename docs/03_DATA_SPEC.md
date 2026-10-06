# 03. Data specification

## 1. Source decision

Use [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) for product-level history. The official metadata describes a two-year UK transaction dataset, 1,067,371 records, a 43.5 MB workbook and CC BY 4.0 attribution terms. Verify the downloaded file and actual sheet/column names in T02; metadata is not a substitute for inspecting the file.

The spreadsheet suggests data.gov.my / OpenDOSM. [Headline Wholesale & Retail Trade](https://open.dosm.gov.my/data-catalogue/iowrt) is monthly aggregate sales/index data. Our inference is that this inspected series cannot directly supply SKU units or warehouse stock. It may support a separate Malaysian aggregate forecasting extension, but will not be joined to UK product history in the MVP.

## 2. Raw input and provenance

- Preserve the downloaded workbook under `data/raw/online_retail_II.xlsx` without edits.
- Write `data/raw/source_manifest.json`: landing URL, resolved download URL, retrieved_at_utc, SHA-256, byte size, license/attribution, actual sheet names, row counts and column mapping.
- Read all relevant year sheets; check overlapping records at sheet boundaries. Do not assume concatenation is safe.
- Normalise actual header aliases: `Invoice`/`InvoiceNo`, `Price`/`UnitPrice`, `Customer ID`/`CustomerID` where present. Missing required fields are an error.
- Customer ID is unnecessary for SKU forecasting. Drop it from prepared/public data; missing customer IDs alone must not remove otherwise valid sales.

## 3. Canonical transaction schema

| Field | Type | Rule |
| --- | --- | --- |
| invoice_id | string | Required; preserve raw identifier; identify cancellation prefixes case-insensitively |
| sku_id | string | Required; preserve leading zeros and alphanumeric codes |
| description | nullable string | Audit/display only; not a forecast feature |
| quantity | integer | Keep strictly positive sales; cancellations and nonpositive adjustments audited separately |
| transaction_at | timestamp | Parse retailer-local timestamps; do not invent timezone conversions |
| sale_unit_price_gbp | finite number | Keep positive price; never treat selling price as procurement cost |
| country | string | Use United Kingdom transactions for the MVP; normalise whitespace and validate labels |

Dates refer to the source retailer's calendar. Malaysia time is used for planning/session logs, not for shifting historical invoice dates.

## 4. Cleaning rules

1. Validate headers/types and preserve source sheet/row identifiers for audit.
2. Remove cancellation invoices, quantities <=0, nonpositive/nonfinite selling prices and missing essential identifiers/dates from the positive-sales target. Report separate counts and quantities for each exclusion reason.
3. Separate clearly nonmerchandise service/adjustment codes using an explicit, recorded exclusion list. Do not exclude every alphanumeric code or rely on a guessed regular expression.
4. Filter the chosen country. Avoid per-customer filters and outcome-dependent outlier caps.
5. Audit exact duplicate rows. Deduplicate only when evidence establishes repeated ingestion/sheet overlap; identical transaction lines may be legitimate. Record the decided key and totals before/after.
6. Aggregate remaining quantities to a Monday-start, Sunday-end product week. Exclude partial first/last source weeks globally.
7. Zero-fill a missing SKU sale row only within a confirmed covered calendar week. A globally missing source week is a data-quality problem, not evidence of zero demand.

Reconcile raw kept quantities -> cleaned quantities -> weekly quantities exactly. Write `reports/data_quality.md` and a machine-readable exclusion audit.

## 5. Cohort selection without future information

- Use only the **first 60 complete source weeks** for product selection.
- Candidate must have a positive sale in the first eight weeks, positive sales in at least 40 of those 60 weeks, and positive total units.
- Rank by total positive units in that prefix, descending; break ties by sku_id ascending.
- Select at most 30 products. If fewer qualify, retain the qualifying set and report actual count; do not use future sales to rescue the cohort.
- Minimum viable set is 10 products and 100 complete source weeks. If either fails, stop the data gate and document a revised scope/source decision before modelling.
- Freeze `data/processed/cohort.json`. Complete the selected SKU panel across the observed calendar; later zero-sales/discontinued products remain in evaluation.
- Select display descriptions from records available by the relevant cutoff or use sku_id. Descriptions must not influence cohort or model selection.

## 6. Prepared schemas

| Artifact | Required fields / key |
| --- | --- |
| `weekly_sales.parquet` | sku_id, week_start, units_sold; unique (sku_id, week_start), nonnegative integer units |
| `cohort.json` | selection prefix dates, rule, ordered SKU IDs and observed qualification statistics |
| `split_manifest.json` | complete week list, validation origins, test origins, final training cutoff and hashes |
| `features.parquet` | sku_id, origin_week_start, target_week_start, horizon, features, target_units; unique SKU/origin/horizon |

DuckDB SQL performs and verifies weekly aggregation. Export reproducible query text and reconcile it against a small hand-calculated fixture.

## 7. Chronological split contract

Number complete weeks `1..N` after trimming. Require `N >= 100` so the first validation training prefix includes the 60-week cohort window and at least twelve additional weeks of potential training labels after feature warm-up.

- Validation origin indices: `N-28`, `N-24`, `N-20`, `N-16`. Each predicts the next four weeks; these target windows do not overlap.
- Final model-selection training cutoff: `c0 = N-12`.
- Final holdout target weeks: `N-11 .. N`, twelve complete weeks.
- Holdout forecast origins: `N-12`, `N-8`, `N-4`, each predicting four weeks.
- A forecast origin means the end of its fully observed week. `origin_week_start` identifies that closed week; target starts are +7h days for horizon h.
- For fold cutoff c, feature timestamps must be <=c and every training label's target week must be <=c. Horizon rows whose labels occur after c are removed.
- Freeze cohort, candidate choices and scenario settings before final test access. Train the final evaluated model on labels available through c0.
- During the holdout, newly observed prior weeks may update lag features and inventory state. Do not retrain, refit scalers/categories or tune policy/model parameters using holdout outcomes.

All products share the same calendar cutoffs. Store exact ISO dates rather than only integer formulas in the manifest.

## 8. Data unavailable from this source

No observed warehouse on-hand quantities, supplier costs, lead times, capacity or unmet-demand labels are established. These enter a separate labelled scenario configuration. Future promotions/prices and Malaysian economic series are excluded from MVP features.

The download and profiling are future tasks. Exact clean row counts, qualifying product count and final split dates are **not yet known**.
