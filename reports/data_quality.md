# Data Quality and Cleaning Report

## 1. Raw Source Summary
- Raw Rows: 1,067,371
- Raw Units: 10,608,492

## 2. Exclusions Breakdown
| Exclusion Reason | Rows Excluded | Units Excluded |
| --- | --- | --- |
| Missing Identifiers/Dates | 0 | 0 |
| Cancellations | 19,494 | -490,992 |
| Nonpositive Quantity (<=0) | 3,457 | -573,085 |
| Nonpositive/NaN Price | 2,750 | 252,264 |
| Nonmerchandise Codes | 4,307 | 17,247 |
| Non-UK Transactions | 81,239 | 2,031,648 |

## 3. Clean Transactions and Aggregation
- Final Clean Transaction Rows: 956,124
- Final Clean Units: 9,371,410
- Prepared Panel Nonzero Rows: 188,676
- Prepared Panel Total Units: 9,013,090
- Unique Clean SKUs: 4,857
