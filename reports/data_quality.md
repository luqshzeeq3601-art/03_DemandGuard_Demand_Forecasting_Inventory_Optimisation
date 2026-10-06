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
- Complete Monday-to-Sunday Calendar Weeks: 102 (2009-12-07 to 2011-11-28)

## 4. Quantity Reconciliation (358,320-Unit Boundary Gap Explained)
The difference between **Clean Transaction Units (9,371,410)** and **Weekly Panel Units (9,013,090)** is **358,320 units**. This gap is entirely accounted for by the strict chronological protocol excluding incomplete boundary weeks:
1. **Partial Incomplete Start Week (2009-12-01 Tuesday to 2009-12-06 Sunday, 6 days)**:
   - Transactions occurred before the first complete Monday-start week (2009-12-07).
   - Excluded units: **140,542 units** (12,968 transactions).
2. **Partial Incomplete End Week (2011-12-05 Monday to 2011-12-09 Friday, 5 days)**:
   - Transactions occurred after the 102nd complete week ending Sunday 2011-12-04 (dataset terminates mid-week on Friday).
   - Excluded units: **217,778 units** (17,453 transactions).
3. **Exact Mathematical Balance**:
   $$\text{Clean Units } (9,371,410) - \text{Incomplete Start } (140,542) - \text{Incomplete End } (217,778) = \text{Panel Units } (9,013,090)$$
   This reconciliation confirms zero unexplained data loss.
