# Inventory Optimisation & Simulation Report

## 1. Simulation Setup & Assumptions
- **Holdout Duration**: 12 continuous calendar weeks across 30 established products.
- **Constraints**: 1-week lead time, weekly replenishment reviews, integer purchase quantities, weekly purchase budget, and physical warehouse capacity.
- **Lost Sales**: Unmet customer demand is strictly lost and never backlogged.
- **Capacity Protection**: Pre-demand occupancy check and committed-order reservation ($I_0 + A_1 + Q_1 \le C$) guarantees zero delivery overflow even if zero sales realise.

## 2. Policy Outcomes Table
| Policy | Net Cost (SCU) | Fill Rate | Total Demand | Sales | Unmet Units | Purchase Spend | Holding Cost | Unmet Penalty | Breaches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P0_Rule` | 337,964.86 | 69.66% | 156,206 | 108,813 | 47,393 | 107,662.00 | 2,342.86 | 236,965.00 | 0 |
| `P1_MILP_Baseline` | 332,830.56 | 70.52% | 156,206 | 110,152 | 46,054 | 109,771.00 | 2,179.56 | 230,270.00 | 0 |
| `P2_MILP_Champion` | 364,193.66 | 65.52% | 156,206 | 102,340 | 53,866 | 101,625.00 | 2,461.66 | 269,330.00 | 0 |

## 3. Comparative Analysis
- **P1 (MILP + Baseline Forecast)** achieved the lowest total business cost (**332,830.56 SCU**) and highest unit fill rate (**70.52%**), saving **5,134.30 SCU** (1.52% cost reduction) over the heuristic P0 rule (**337,964.86 SCU**).
- **Physical Feasibility**: Zero capacity breaches occurred across all 12 weeks for all policies, proving constraint enforcement.
- **Safety Stock Slack**: The soft safety deficit formulation enabled balanced service-level trade-offs without making the problem infeasible during budget-constrained weeks.
