"""Mixed-Integer Linear Programming (MILP) inventory optimizer and validator."""

from __future__ import annotations

import time
from typing import Any

import pulp

from demandguard.contracts import (
    ProductInventoryInput,
    ReorderResponse,
    ReorderWorklistRow,
)

# Relative MIP gap at which CBC may stop and report a proven solution (decision D23).
DEFAULT_RELATIVE_GAP = 0.001


def _solver_status(prob: pulp.LpProblem, status_code: int) -> str:
    """Map PuLP results to a status that separates proven solutions from time-limit stops.

    PuLP reports status ``Optimal`` when CBC stops on the time limit with an incumbent; only
    ``sol_status`` distinguishes that case (decision D22).
    """
    status_str = pulp.LpStatus[status_code]
    if status_str == "Optimal" and prob.sol_status == pulp.LpSolutionIntegerFeasible:
        return "TimeLimitFeasible"
    return status_str


def _value(var: pulp.LpVariable) -> float:
    val = pulp.value(var)
    return float(val) if val is not None else 0.0


def solve_inventory_milp(
    products: list[ProductInventoryInput],
    forecast_matrix: dict[str, list[float]],  # sku -> [d1, d2, d3, d4]
    weekly_budgets_scu: list[float],  # [B1, B2, B3, B4]
    warehouse_capacity_slots: int,
    terminal_value_fraction: float = 0.5,
    solver_time_limit_seconds: int = 10,
    solver_relative_gap: float = DEFAULT_RELATIVE_GAP,
) -> tuple[dict[str, Any], dict[str, list[int]], dict[str, Any]]:
    """Build and solve 4-week MILP inventory optimization problem using PuLP.

    Orders are returned only when CBC proves the solution within ``solver_relative_gap``.
    """
    start_time = time.perf_counter()

    # Initial consistency check: check starting on hand + arrival week 1 <= capacity
    total_init_occupancy = sum(
        (p.on_hand_units + p.incoming_week_1_units) * p.storage_slots_per_unit for p in products
    )
    if total_init_occupancy > warehouse_capacity_slots:
        raise ValueError(
            f"Initial warehouse occupancy {total_init_occupancy:.1f} exceeds capacity {warehouse_capacity_slots}."
        )

    prob = pulp.LpProblem("DemandGuard_Inventory_MILP", pulp.LpMinimize)

    # Decision variables
    # Q(i, t) for t=1..4 (integers)
    # I(i, t) for t=1..4 (continuous >= 0)
    # U(i, t) for t=1..4 (continuous >= 0)
    # Z(i, t) for t=1..4 (continuous >= 0)
    # b(i, t) for t=1..4 (binary)
    Q: dict[tuple[str, int], pulp.LpVariable] = {}
    I: dict[tuple[str, int], pulp.LpVariable] = {}  # noqa: E741
    U: dict[tuple[str, int], pulp.LpVariable] = {}
    Z: dict[tuple[str, int], pulp.LpVariable] = {}
    b: dict[tuple[str, int], pulp.LpVariable] = {}

    sku_map = {p.sku_id: p for p in products}

    for p in products:
        sku = p.sku_id
        for t in range(1, 5):
            # Q4 is constrained to 0 (finite-horizon rule)
            if t == 4:
                Q[(sku, t)] = pulp.LpVariable(
                    f"Q_{sku}_{t}", lowBound=0, upBound=0, cat=pulp.LpInteger
                )
            else:
                Q[(sku, t)] = pulp.LpVariable(f"Q_{sku}_{t}", lowBound=0, cat=pulp.LpInteger)

            I[(sku, t)] = pulp.LpVariable(f"I_{sku}_{t}", lowBound=0, cat=pulp.LpContinuous)
            U[(sku, t)] = pulp.LpVariable(f"U_{sku}_{t}", lowBound=0, cat=pulp.LpContinuous)
            Z[(sku, t)] = pulp.LpVariable(f"Z_{sku}_{t}", lowBound=0, cat=pulp.LpContinuous)
            b[(sku, t)] = pulp.LpVariable(f"b_{sku}_{t}", cat=pulp.LpBinary)

    # Objective function:
    # sum(c*Q + h*I + p*U + g*Z) - terminal_value_fraction * sum(c * I(i, 4))
    obj_terms = []
    for p in products:
        sku = p.sku_id
        c_i = p.unit_purchase_cost_scu
        h_i = p.holding_cost_scu_per_unit_week
        p_i = p.unmet_penalty_scu_per_unit
        g_i = p.safety_deficit_penalty_scu

        for t in range(1, 5):
            obj_terms.append(c_i * Q[(sku, t)])
            obj_terms.append(h_i * I[(sku, t)])
            obj_terms.append(p_i * U[(sku, t)])
            obj_terms.append(g_i * Z[(sku, t)])

        # Terminal value credit on I(i, 4)
        obj_terms.append(-terminal_value_fraction * c_i * I[(sku, 4)])

    prob += pulp.lpSum(obj_terms)

    # Constraints
    # 1. Inventory balance and lost-sales bounds
    for p in products:
        sku = p.sku_id
        fc_list = forecast_matrix.get(sku, [0.0, 0.0, 0.0, 0.0])
        s_i = p.safety_stock_target_units
        v_i = p.storage_slots_per_unit

        for t in range(1, 5):
            d_it = float(fc_list[t - 1])
            # Arrivals A(i, t)
            if t == 1:
                A_it = p.incoming_week_1_units
                I_prev = p.on_hand_units
            else:
                A_it = Q[(sku, t - 1)]
                I_prev = I[(sku, t - 1)]

            # Balance: I(i, t) = I(i, t-1) + A(i, t) - d(i, t) + U(i, t)
            prob += I[(sku, t)] == I_prev + A_it - d_it + U[(sku, t)], f"Balance_{sku}_{t}"

            # Lost sales upper bound
            prob += U[(sku, t)] <= d_it, f"LostSalesUB_{sku}_{t}"

            # Safety deficit: Z(i, t) >= S(i) - I(i, t)
            prob += Z[(sku, t)] >= s_i - I[(sku, t)], f"SafetyDeficit_{sku}_{t}"

            # Physical fulfilment: U(i, t) <= d_it * b(i, t) and I(i, t) <= (C/v_i)*(1 - b(i, t))
            big_M_cap = warehouse_capacity_slots / v_i
            prob += U[(sku, t)] <= d_it * b[(sku, t)], f"StockoutUB_{sku}_{t}"
            prob += I[(sku, t)] <= big_M_cap * (1 - b[(sku, t)]), f"PhysicalStockUB_{sku}_{t}"

    # 2. Budget constraints for each week t=1..4
    for t in range(1, 5):
        budget_t = weekly_budgets_scu[t - 1]
        spend_t = pulp.lpSum(
            sku_map[p.sku_id].unit_purchase_cost_scu * Q[(p.sku_id, t)] for p in products
        )
        prob += spend_t <= budget_t, f"BudgetWeek_{t}"

    # 3. Pre-demand capacity constraints for each week t=1..4
    # sum(v_i * (I(i, t-1) + A(i, t))) <= C
    for t in range(1, 5):
        if t == 1:
            occ_t = sum(
                p.storage_slots_per_unit * (p.on_hand_units + p.incoming_week_1_units)
                for p in products
            )
            prob += occ_t <= warehouse_capacity_slots, "PreDemandCapacity_1"
        else:
            occ_t = pulp.lpSum(
                sku_map[p.sku_id].storage_slots_per_unit
                * (I[(p.sku_id, t - 1)] + Q[(p.sku_id, t - 1)])
                for p in products
            )
            prob += occ_t <= warehouse_capacity_slots, f"PreDemandCapacity_{t}"

    # 4. Committed-order capacity protection:
    # sum(v_i * (I(i, 0) + A(i, 1) + Q(i, 1))) <= C
    committed_protection = pulp.lpSum(
        p.storage_slots_per_unit * (p.on_hand_units + p.incoming_week_1_units + Q[(p.sku_id, 1)])
        for p in products
    )
    prob += committed_protection <= warehouse_capacity_slots, "CommittedOrderCapacityProtection"

    # Solve with time limit
    solver = pulp.PULP_CBC_CMD(
        msg=False, timeLimit=solver_time_limit_seconds, gapRel=solver_relative_gap
    )
    status_code = prob.solve(solver)
    runtime = time.perf_counter() - start_time
    status_str = _solver_status(prob, status_code)
    solver_name = prob.solver.name if prob.solver else "CBC"

    raw_results = {
        "status": status_str,
        "solver_name": solver_name,
        "runtime_seconds": runtime,
        "relative_gap": solver_relative_gap,
        "objective": pulp.value(prob.objective) if status_str == "Optimal" else None,
    }

    # Extract orders
    solved_orders: dict[str, list[int]] = {}
    solved_traces: dict[str, Any] = {"I": {}, "U": {}, "Z": {}, "b": {}}

    if status_str == "Optimal":
        for p in products:
            sku = p.sku_id
            q_list = []
            for t in range(1, 5):
                q_val = int(round(_value(Q[(sku, t)])))
                q_list.append(q_val)
                solved_traces["I"][(sku, t)] = _value(I[(sku, t)])
                solved_traces["U"][(sku, t)] = _value(U[(sku, t)])
                solved_traces["Z"][(sku, t)] = _value(Z[(sku, t)])
                solved_traces["b"][(sku, t)] = _value(b[(sku, t)])
            solved_orders[sku] = q_list

    return raw_results, solved_orders, solved_traces


def validate_milp_solution(
    products: list[ProductInventoryInput],
    forecast_matrix: dict[str, list[float]],
    weekly_budgets_scu: list[float],
    warehouse_capacity_slots: int,
    solved_orders: dict[str, list[int]],
    solved_traces: dict[str, Any],
    tol: float = 1e-5,
) -> tuple[bool, list[str]]:
    """Independently reconstruct algebraic state from solved Q and verify all constraints."""
    violations = []

    # 1. Verify integrality of orders
    for sku, q_list in solved_orders.items():
        for t, q in enumerate(q_list, 1):
            if abs(q - round(q)) > tol or q < 0:
                violations.append(f"Product {sku} Q{t}={q} is not a valid nonnegative integer.")
        if q_list[3] != 0:
            violations.append(f"Product {sku} Q4={q_list[3]} violates Q4=0 boundary condition.")

    # 2. Verify weekly budgets
    sku_map = {p.sku_id: p for p in products}
    for t in range(1, 5):
        spend_t = sum(
            sku_map[p.sku_id].unit_purchase_cost_scu * solved_orders[p.sku_id][t - 1]
            for p in products
        )
        if spend_t > weekly_budgets_scu[t - 1] + tol:
            violations.append(
                f"Week {t} spend {spend_t:.2f} exceeds budget {weekly_budgets_scu[t - 1]:.2f}."
            )

    # 3. Reconstruct physical state simulation and compare to solver variables
    recon_I: dict[tuple[str, int], float] = {}
    for p in products:
        sku = p.sku_id
        current_I = float(p.on_hand_units)
        fc_list = forecast_matrix.get(sku, [0.0, 0.0, 0.0, 0.0])

        for t in range(1, 5):
            d_it = float(fc_list[t - 1])
            arr_it = float(p.incoming_week_1_units if t == 1 else solved_orders[sku][t - 2])
            avail = current_I + arr_it

            # Algebraic physical rules:
            unmet = max(0.0, d_it - avail)
            end_I = max(0.0, avail - d_it)

            # Check solver values match physical reconstruction
            solver_I = solved_traces["I"].get((sku, t), 0.0)
            solver_U = solved_traces["U"].get((sku, t), 0.0)

            if abs(solver_I - end_I) > tol:
                violations.append(
                    f"SKU {sku} Week {t} ending stock mismatch: solver={solver_I}, physical={end_I}"
                )
            if abs(solver_U - unmet) > tol:
                violations.append(
                    f"SKU {sku} Week {t} unmet demand mismatch: solver={solver_U}, physical={unmet}"
                )

            # Advance state for next week
            current_I = end_I
            recon_I[(sku, t)] = end_I

    # 4. Verify capacity constraints
    # Pre-demand capacity for weeks 1..4
    for t in range(1, 5):
        if t == 1:
            occ_t = sum(
                p.storage_slots_per_unit * (p.on_hand_units + p.incoming_week_1_units)
                for p in products
            )
        else:
            occ_t = sum(
                p.storage_slots_per_unit
                * (recon_I[(p.sku_id, t - 1)] + solved_orders[p.sku_id][t - 2])
                for p in products
            )
        if occ_t > warehouse_capacity_slots + tol:
            violations.append(
                f"Week {t} pre-demand occupancy {occ_t:.2f} exceeds capacity {warehouse_capacity_slots}."
            )

    # Committed order protection: sum(v * (I0 + A1 + Q1)) <= C
    committed_occ = sum(
        p.storage_slots_per_unit
        * (p.on_hand_units + p.incoming_week_1_units + solved_orders[p.sku_id][0])
        for p in products
    )
    if committed_occ > warehouse_capacity_slots + tol:
        violations.append(
            f"Committed order reservation occupancy {committed_occ:.2f} exceeds warehouse capacity {warehouse_capacity_slots}."
        )

    is_valid = len(violations) == 0
    return is_valid, violations


def build_reorder_worklist(
    products: list[ProductInventoryInput],
    forecast_matrix: dict[str, list[float]],
    solved_orders: dict[str, list[int]],
    as_of_week_start: str,
    solver_meta: dict[str, Any],
    validation_status: str,
    warnings: list[str],
) -> ReorderResponse:
    """Construct verified ReorderResponse object."""
    worklist = []
    if validation_status == "PASSED" and solved_orders:
        for p in products:
            sku = p.sku_id
            fc = forecast_matrix.get(sku, [0.0, 0.0, 0.0, 0.0])
            q = solved_orders.get(sku, [0, 0, 0, 0])
            spend_q1 = float(q[0] * p.unit_purchase_cost_scu)

            worklist.append(
                ReorderWorklistRow(
                    sku_id=sku,
                    current_on_hand=p.on_hand_units,
                    incoming_week_1=p.incoming_week_1_units,
                    forecast_week_1=fc[0],
                    forecast_week_2=fc[1],
                    forecast_week_3=fc[2],
                    forecast_week_4=fc[3],
                    order_q1=q[0],
                    expected_arrival_week_2=q[0],
                    spend_week_1_scu=spend_q1,
                    provisional_q2=q[1],
                    provisional_q3=q[2],
                    provisional_q4=q[3],
                )
            )

    return ReorderResponse(
        status="OPTIMAL" if validation_status == "PASSED" else "ERROR",
        as_of_week_start=as_of_week_start,
        solver_name=solver_meta.get("solver_name", "CBC"),
        solve_runtime_seconds=solver_meta.get("runtime_seconds", 0.0),
        total_objective_scu=solver_meta.get("objective"),
        validation_status="PASSED" if validation_status == "PASSED" else "FAILED",
        worklist=worklist,
        warnings=warnings,
    )


def solve_stochastic_inventory_milp(
    products: list[ProductInventoryInput],
    forecast_quantiles: dict[str, dict[str, list[float]]],  # sku -> {'p10': [...], 'p50': [...], 'p90': [...]}
    weekly_budgets_scu: list[float],
    warehouse_capacity_slots: int,
    scenario_weights: dict[str, float] | None = None,
    terminal_value_fraction: float = 0.5,
    solver_time_limit_seconds: int = 10,
    solver_relative_gap: float = DEFAULT_RELATIVE_GAP,
) -> tuple[dict[str, Any], dict[str, list[int]], dict[str, Any]]:
    """Build and solve multi-scenario stochastic MILP minimizing expected holding and unmet penalties."""
    start_time = time.perf_counter()
    weights = scenario_weights or {"p10": 0.25, "p50": 0.50, "p90": 0.25}
    scenarios = list(weights.keys())

    prob = pulp.LpProblem("DemandGuard_Stochastic_MILP", pulp.LpMinimize)

    Q: dict[tuple[str, int], pulp.LpVariable] = {}
    I: dict[tuple[str, int, str], pulp.LpVariable] = {}  # (sku, t, s)  # noqa: E741
    U: dict[tuple[str, int, str], pulp.LpVariable] = {}  # (sku, t, s)
    Z: dict[tuple[str, int, str], pulp.LpVariable] = {}  # (sku, t, s)
    b: dict[tuple[str, int, str], pulp.LpVariable] = {}  # (sku, t, s)

    for p in products:
        sku = p.sku_id
        for t in range(1, 5):
            if t == 4:
                Q[(sku, t)] = pulp.LpVariable(f"Q_{sku}_{t}", lowBound=0, upBound=0, cat=pulp.LpInteger)
            else:
                Q[(sku, t)] = pulp.LpVariable(f"Q_{sku}_{t}", lowBound=0, cat=pulp.LpInteger)

            for s in scenarios:
                I[(sku, t, s)] = pulp.LpVariable(f"I_{sku}_{t}_{s}", lowBound=0, cat=pulp.LpContinuous)
                U[(sku, t, s)] = pulp.LpVariable(f"U_{sku}_{t}_{s}", lowBound=0, cat=pulp.LpContinuous)
                Z[(sku, t, s)] = pulp.LpVariable(f"Z_{sku}_{t}_{s}", lowBound=0, cat=pulp.LpContinuous)
                b[(sku, t, s)] = pulp.LpVariable(f"b_{sku}_{t}_{s}", cat=pulp.LpBinary)

    # Objective: procurement cost + expected holding/shortage costs across scenarios
    obj_terms = []
    for p in products:
        sku = p.sku_id
        c_i = p.unit_purchase_cost_scu
        h_i = p.holding_cost_scu_per_unit_week
        p_i = p.unmet_penalty_scu_per_unit
        g_i = p.safety_deficit_penalty_scu

        for t in range(1, 5):
            obj_terms.append(c_i * Q[(sku, t)])

        for s in scenarios:
            w_s = weights[s]
            for t in range(1, 5):
                obj_terms.append(w_s * h_i * I[(sku, t, s)])
                obj_terms.append(w_s * p_i * U[(sku, t, s)])
                obj_terms.append(w_s * g_i * Z[(sku, t, s)])
            # Terminal credit
            obj_terms.append(-w_s * terminal_value_fraction * c_i * I[(sku, 4, s)])

    prob += pulp.lpSum(obj_terms)

    M = 100000.0
    for p in products:
        sku = p.sku_id
        s_i = p.safety_stock_target_units
        sku_fc = forecast_quantiles.get(sku, {})

        for s in scenarios:
            fc_list = sku_fc.get(s, [0.0, 0.0, 0.0, 0.0])
            for t in range(1, 5):
                d_it = float(fc_list[t - 1]) if t - 1 < len(fc_list) else 0.0
                if t == 1:
                    prev_I = p.on_hand_units
                    arr = p.incoming_week_1_units
                else:
                    prev_I = I[(sku, t - 1, s)]
                    arr = Q[(sku, t - 1)]

                # Net balance
                prob += I[(sku, t, s)] - U[(sku, t, s)] == prev_I + arr - d_it
                prob += I[(sku, t, s)] <= M * (1 - b[(sku, t, s)])
                prob += U[(sku, t, s)] <= M * b[(sku, t, s)]
                prob += Z[(sku, t, s)] >= s_i - I[(sku, t, s)]

    # Budget constraints
    for t in range(1, 5):
        B_t = weekly_budgets_scu[t - 1]
        prob += pulp.lpSum(p.unit_purchase_cost_scu * Q[(p.sku_id, t)] for p in products) <= B_t

    # Pre-demand capacity per scenario: stock before demand plus that week's arrival
    for s in scenarios:
        for t in range(1, 5):
            prob += (
                pulp.lpSum(
                    p.storage_slots_per_unit
                    * (
                        (p.on_hand_units + p.incoming_week_1_units)
                        if t == 1
                        else (I[(p.sku_id, t - 1, s)] + Q[(p.sku_id, t - 1)])
                    )
                    for p in products
                )
                <= warehouse_capacity_slots
            )

    # Committed order reservation
    prob += (
        pulp.lpSum(
            p.storage_slots_per_unit * (p.on_hand_units + p.incoming_week_1_units + Q[(p.sku_id, 1)])
            for p in products
        )
        <= warehouse_capacity_slots
    )

    solver = pulp.PULP_CBC_CMD(
        timeLimit=solver_time_limit_seconds, gapRel=solver_relative_gap, msg=False
    )
    status_code = prob.solve(solver)
    runtime = time.perf_counter() - start_time

    status_str = _solver_status(prob, status_code)
    solved_orders: dict[str, list[int]] = {}
    if status_str == "Optimal":
        for p in products:
            sku = p.sku_id
            orders = [int(round(_value(Q[(sku, t)]))) for t in range(1, 5)]
            solved_orders[sku] = orders

    solver_meta = {
        "status": status_str,
        "runtime_seconds": runtime,
        "relative_gap": solver_relative_gap,
        "objective": pulp.value(prob.objective) if status_str == "Optimal" else None,
        "solver_name": "PULP_CBC_CMD",
    }
    return solver_meta, solved_orders, {}

