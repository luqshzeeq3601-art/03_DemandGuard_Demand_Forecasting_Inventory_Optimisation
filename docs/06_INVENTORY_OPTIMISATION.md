# 06. Inventory optimisation and simulation

## 1. Decision being made

At the beginning of each week, choose whole-unit orders for supported products. An order placed now arrives at the beginning of the following week. The forecast covers four weeks; only the first order is executed. Recompute next week using the new state.

The workbook asks for PuLP linear programming. Whole-unit purchase decisions make this a **mixed-integer linear program (MILP)**. Keep the objective and constraints linear, and use integer order variables directly.

## 2. Timing convention

At a decision origin, sales are observed through the previous closed week.

1. Receive previously committed deliveries due at the beginning of the current week.
2. Validate pre-demand warehouse occupancy.
3. Place this week's order using the observed history and current state. It arrives next week, not immediately.
4. Realise this week's proxy demand; fulfil at most available stock. Unfilled units are lost sales and do not become backlog.
5. Charge holding cost on ending stock, record unmet units and advance the calendar.

Optimiser inputs represent **on-hand before receipt** plus separate incoming-week-1 quantities. Forecasting uses the prior closed week. Never receive the incoming shipment twice.

Capture this input snapshot before mutating the simulation state. The simulator receives it once; the optimiser accounts for the same receipt algebraically. Tests must establish that these two views describe the same available stock.

## 3. Four-week model

For product i and relative week t=1..4:

| Symbol | Meaning |
| --- | --- |
| d(i,t) | Nonnegative point forecast; real-valued units |
| Q(i,t) | Nonnegative integer purchase order |
| A(i,t) | Arrivals: committed incoming units for t=1, and Q(i,t-1) for t=2..4 |
| I(i,t) | Nonnegative projected ending stock, continuous |
| U(i,t) | Unmet forecast units, continuous, bounded by 0..d(i,t) |
| Z(i,t) | Safety-stock deficit, nonnegative continuous |
| b(i,t) | Binary stockout flag used to prevent simultaneous ending stock and unmet units |
| S(i) | Safety-stock heuristic in units |
| c(i), h(i), p(i), g(i) | Purchase, weekly holding, unmet-unit and safety-deficit costs |
| v(i), B(t), C | Storage slots per unit, weekly purchase budget and warehouse slots |
| I(i,0) | Starting on-hand before the week-1 receipt |

Minimise:

`sum(c*Q + h*I + p*U + g*Z) - 0.5*sum(c*I(i,4))`

The final term credits half the assumed purchase value of ending stock. It is a declared terminal-value assumption, not a measured resale value. Only Q1-Q3 can arrive within this planning window; constrain Q4=0. Future orders remain provisional.

Subject to:

1. Inventory balance: `I(i,t) = I(i,t-1) + A(i,t) - d(i,t) + U(i,t)`.
2. Lost-sales bounds: `0 <= U(i,t) <= d(i,t)`.
3. Weekly purchase budget: `sum(c(i)*Q(i,t)) <= B(t)`.
4. **Pre-demand capacity:** `sum(v(i)*(I(i,t-1)+A(i,t))) <= C`. Checking only ending stock would miss arrival overflow.
5. **Committed-order capacity protection:** `sum(v(i)*(I(i,0)+A(i,1)+Q(i,1))) <= C`. Reserve room for the first executed order without assuming any current-week sales. Since actual sales cannot increase inventory, this protects next week's arrival even if demand is zero.
6. Safety deficit: `Z(i,t) >= S(i)-I(i,t)`.
7. Physical fulfilment: `U(i,t) <= d(i,t)*b(i,t)` and `I(i,t) <= (C/v(i))*(1-b(i,t))`. The finite stock bound follows from warehouse capacity. These constraints prevent reporting a shortage while keeping available stock for that same product/week.
8. Domain constraints: Q integers; b binary; I, U, Z nonnegative; all coefficients finite and valid.

Test physical fulfilment even when safety or terminal-value incentives are strong. The stockout flag enforces the rule rather than relying on cost coefficients to make it happen. Safety is soft so scarce budgets can produce an explained service trade-off rather than a fabricated feasible service guarantee.

If initial on-hand plus committed receipts already exceeds capacity, reject that inconsistent input. Do not hide it by assuming disposal, lost deliveries or an invented overflow warehouse.

## 4. Scenario defaults

All inputs below are synthetic. Compute scale from the historical prefix available at each simulation's starting origin, then freeze budget/capacity/initialisation for that simulation segment.

| Parameter | Default |
| --- | --- |
| Purchase cost | 1 SCU per unit for every product |
| Holding cost | 0.02 SCU per ending unit per week |
| Unmet-unit penalty | 5 SCU per unit |
| Safety-deficit penalty | 0.5 SCU per deficit unit; planner objective only |
| Space | 1 storage slot per unit |
| Lead time / review interval | 1 week / 1 week |
| Starting stock | ceil(2 * trailing-13-week mean) per product |
| Initial incoming shipment | 0 units |
| Weekly base budget | ceil(sum(trailing-13-week mean * purchase cost)) |
| Capacity | max(sum(initial stock), ceil(3 * sum(trailing-13-week mean))) slots |
| Terminal value fraction | 0.5 of purchase value |
| Safety stock | ceil(k * trailing-13-week sample std), recomputed from observed history |

Choose a single k from {0, 1, 1.645} using validation simulations; freeze it before holdout. This is a heuristic, not proof of a 95% service level. Use identical k for all compared policies in the primary comparison; record how it was selected.

Stress scenarios change the weekly budget multiplier to 0.6, 1.0 and 1.4. Costs, demand and initial state are identical across policies within each scenario. Do not calibrate scenario costs from target-week sales or reinterpret GBP selling prices as costs.

## 5. Comparison policies

| ID | Policy | Purpose |
| --- | --- | --- |
| P0 | Constrained order-up-to rule using trailing-four-week mean | Simple operational reference |
| P1 | MILP with strongest validation baseline forecasts | Isolates optimisation from ML forecast effects |
| P2 | MILP with selected champion forecasts | Full proposed system |

P0 target is `ceil(2 * trailing-four-week mean + S)`. Desired Q is max(0, target - inventory_position), where position includes on-hand and pending receipts.

Allocate P0 whole-unit purchases in descending relative shortfall `desired / max(target,1)`, tie by sku_id. Reduce quantities to fit budget and conservative next-arrival space: reserve current on-hand plus committed incoming plus new orders within C, without assuming unknown sales free space. Record this conservative allocation rule, since it differs from MILP's predicted inventory path.

For every policy, the shared simulator independently checks actual arrival capacity. Both the MILP first-order reservation and P0's reservation protect the next committed delivery against zero realised sales. Future MILP orders are provisional and must be solved again before commitment. Any actual capacity breach is a failed implementation/contract check; do not discard overflow or silently reroute deliveries.

If the champion is also the strongest baseline, P1 and P2 are identical; disclose this instead of implying an ML contribution.

## 6. Fair historical simulation

- Use recorded positive sales as requested proxy demand. Do not substitute each model's own forecast for realised demand.
- For each validation fold, start all policies from the same prefix-derived state and run four realised weeks. Forecasts may update from newly observed prior weeks; fold model weights stay fixed.
- Choose k by aggregate P1 validation cost among candidates that yield no actual capacity breach; ties favour smaller k. If no candidate yields valid P1 runs, stop the policy gate and revise capacity protection before holdout.
- Final test: one continuous twelve-week run, same initial state per policy, frozen model/policy/settings and weekly decisions.
- Advance pipeline shipments correctly; pay purchase cost at placement, holding at week end and unmet penalty after demand.
- Never reset inventory every forecast horizon or policy week. That would create free stock.

## 7. Outcome metrics

Primary realised simulation cost:

`total_purchase_spend + total_holding_cost + total_unmet_penalty - 0.5*purchase_value(ending_on_hand + prepaid_pipeline)`.

Include prepaid outstanding orders in terminal value so the last week's replenishment is not unfairly penalised. Safety-deficit penalties belong to planner objectives and are reported separately, not inserted into the realised business-cost comparison.

Also report unit fill rate, unmet units, weeks with unmet units, mean ending inventory, final inventory/pipeline value, purchasing spend, capacity breaches and solver failures.

Relative cost reduction is `(P0_cost - proposed_cost)/P0_cost` only when P0_cost>0; otherwise report absolute SCU difference. A useful-improvement claim requires >=5% lower cost, fill rate at least P0's, zero constraint breaches and no hidden failed weeks. Always publish actual results.

## 8. Solver and output rules

- Verify installed PuLP API and available CBC executable; pin both in reproducibility records.
- Time limit: 10 seconds for a 30-product/four-week request.
- v0.1 accepts only an optimal solver status, finite values, integer Q within 1e-6, balanced inventories and budget/capacity residuals within 1e-6.
- "Optimal" means proven within a 0.1% relative MIP gap (`gapRel=0.001`, decision D23). A CBC stop on the time limit is reported as `TimeLimitFeasible` and is not executable: that week places zero orders and counts as a solver failure.
- Independent validation reconstructs the constraints from inputs and Q; it must not trust a solver status alone.
- Reconstruct fulfilment as min(available stock, forecast demand), shortage as max(0, forecast demand-available stock) and ending stock as max(0, available stock-forecast demand). Compare this trace to the solver values.
- On failure, return diagnostics and no actionable orders. A fallback may be introduced later only with explicit status, validation and separate evaluation.

## 9. Limits of the decision model

Known costs, deterministic lead time, fractional forecast demand, single location and a fixed catalogue simplify the real problem. Current committed orders have a conservative capacity reservation; later quantities depend on the forecast and must be replanned. The reservation may leave otherwise usable future space idle. There are no actual warehouse or shortage labels in the selected benchmark.

## 10. v0.2 exploratory policies (D18)

Run over the same 12-week window, initial state, budget, capacity and k=1.0 as v0.1. All results are EXPLORATORY because the window was viewed in v0.1.

| Policy | Forecast | Optimiser |
| --- | --- | --- |
| P0 | Trailing 4-week mean | Constrained rule |
| P1 | B2 | Deterministic MILP |
| P3 | Frozen v0.2 champion | Deterministic MILP (if the champion is B2, P3 equals P1 and is disclosed) |
| P4 | M2_q50 P10/P50/P90 | Stochastic expected-cost MILP, weights 0.25/0.50/0.25 |
| P5 | M2_q50 P50 | Deterministic MILP; safety stock z x (P90-P10)/2.563 from week-1 quantiles, z = k (D24) |

The stochastic MILP keeps the budget, committed-order reservation and per-scenario pre-demand capacity constraints. A failed or non-optimal solve places zero orders that week and is counted as a solver failure. Under D23, P4 did not prove a solution within 10s in any of the 12 weeks, so it is not executable at this time limit.
