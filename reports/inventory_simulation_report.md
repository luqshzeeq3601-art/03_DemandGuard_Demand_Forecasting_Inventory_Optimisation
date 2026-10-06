# Inventory Optimisation & Simulation Report

## 1. Simulation Setup & Assumptions
- **Holdout Duration**: 12 continuous calendar weeks across 30 established products.
- **Constraints**: 1-week lead time, weekly replenishment reviews, integer purchase quantities, weekly purchase budget, and physical warehouse capacity.
- **Lost Sales**: Unmet customer demand is strictly lost and never backlogged.
- **Capacity Protection**: Pre-demand occupancy check and committed-order reservation ($I_0 + A_1 + Q_1 \le C$) guarantees zero delivery overflow even if zero sales realise.

## 2. Policy Outcomes Table (12-Week Holdout)
| Policy | Net Cost (SCU) | Fill Rate | Total Demand | Sales | Unmet Units | Purchase Spend | Holding Cost | Unmet Penalty | Breaches | Cost vs P0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P0_Rule` | 337,964.86 | 69.66% | 156,206 | 108,813 | 47,393 | 107,662.00 | 2,342.86 | 236,965.00 | 0 | Baseline |
| `P1_MILP_Baseline` | 340,215.08 | 68.05% | 156,206 | 106,297 | 49,909 | 90,145.00 | 2,029.58 | 249,545.00 | 0 | +0.67% (+2,250.22 SCU) |
| `P2_MILP_Champion` | 355,391.66 | 66.79% | 156,206 | 104,334 | 51,872 | 102,621.00 | 2,134.66 | 259,360.00 | 0 | +5.16% (+17,426.80 SCU) |

## 3. Safety Stock Factor ($k$) Validation Search
| Safety Factor ($k$) | Mean Validation Cost (SCU) | Mean Fill Rate | Capacity Breaches | Status |
| --- | --- | --- | --- | --- |
| $k = 0.0$ | 66,003.20 | 75.49% | 0 | Candidate |
| $k = 1.0$ | 55,684.92 | 84.81% | 0 | **Selected Champion ($k=1.0$)** |
| $k = 1.645$ | 57,025.80 | 84.69% | 0 | Candidate |

## 4. Budget Stress Scenarios ($0.6\times, 1.0\times, 1.4\times$)
| Budget Multiplier | Policy | Weekly Budget (SCU) | Net Cost (SCU) | Fill Rate | Unmet Units | Breaches | Unproven Solves |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **0.6x** | `P0_Rule` | 5,744 | 463,629.72 | 48.94% | 79,760 | 0 | 0 |
| **0.6x** | `P1_MILP_Baseline` | 5,744 | 467,257.34 | 48.42% | 80,578 | 0 | 0 |
| **0.6x** | `P2_MILP_Champion` | 5,744 | 525,288.00 | 38.89% | 95,455 | 0 | 3 |
| **1.0x** | `P0_Rule` | 9,573 | 337,964.86 | 69.66% | 47,393 | 0 | 0 |
| **1.0x** | `P1_MILP_Baseline` | 9,573 | 335,099.70 | 70.16% | 46,617 | 0 | 0 |
| **1.0x** | `P2_MILP_Champion` | 9,573 | 363,667.40 | 65.60% | 53,730 | 0 | 0 |
| **1.4x** | `P0_Rule` | 13,403 | 327,014.34 | 71.45% | 44,603 | 0 | 0 |
| **1.4x** | `P1_MILP_Baseline` | 13,403 | 330,127.66 | 71.19% | 45,004 | 0 | 0 |
| **1.4x** | `P2_MILP_Champion` | 13,403 | 363,080.60 | 65.71% | 53,559 | 0 | 0 |

## 5. Comparative Analysis & Key Findings
1. **Cost & Service Trade-off**:
   - **P1 (MILP + B2 forecast)**: 340,215.08 SCU, fill rate 68.05%; +0.67% vs P0 (337,964.86 SCU). The 5% O5 stretch target is **missed**.
   - **P2 (MILP + ML forecast)**: 355,391.66 SCU, fill rate 66.79%. The champion under-forecast the Q4 ramp, raising unmet-demand penalties.
2. **Unmet-demand penalties dominate**: on average 72% of net cost across policies, because the scenario budget is tight during the holiday ramp-up.
3. **Solver status**: MILP solves stop at a proven 0.1% relative gap (decision D23); unproven solves place no orders. Unproven solves in this run: 2.
4. **Physical feasibility**: capacity breaches across policies: 0.
