"""Tests for MILP inventory optimisation, constraints, and independent validation (Task T09 / Gate G3)."""

import pytest

from demandguard.contracts import ProductInventoryInput
from demandguard.inventory import solve_inventory_milp, validate_milp_solution


def test_milp_tiny_exhaustive_optimum():
    """Verify MILP matches exact manual enumeration on a 1-product 2-week scenario."""
    # Product: cost=1.0, holding=0.1, unmet=10.0, storage=1.0, terminal=0.5
    # Initial stock=0, incoming=0
    # Forecasts: d1 = 5.0, d2 = 5.0, d3 = 0.0, d4 = 0.0
    # Budgets: B1 = 10, B2 = 10, B3 = 10, B4 = 10
    # Capacity: C = 20
    #
    # Timing:
    # Week 1: on_hand=0, arrival=0 -> demand=5 -> unmet=5, ending=0. Order Q1 arrives in W2.
    # Cost W1: purchase Q1 * 1 + unmet 5 * 10 = Q1 + 50
    # Week 2: arrival = Q1. Demand = 5.
    # If Q1=5: arrival 5 -> demand 5 -> unmet=0, ending=0. Order Q2 arrives W3.
    # Total cost for Q1=5, Q2=0: (5 + 50) + 0 - 0 = 55.0.
    # If Q1=0: unmet in W2 is 5 -> cost = 50 + 50 = 100.
    # The optimal integer decision is Q1=5, Q2=0, Q3=0, Q4=0 with objective = 55.0.
    prod = ProductInventoryInput(
        sku_id="SKU_MINI",
        on_hand_units=0,
        incoming_week_1_units=0,
        unit_purchase_cost_scu=1.0,
        holding_cost_scu_per_unit_week=0.1,
        unmet_penalty_scu_per_unit=10.0,
        safety_deficit_penalty_scu=0.0,
        storage_slots_per_unit=1.0,
        safety_stock_target_units=0.0,
    )
    fc_matrix = {"SKU_MINI": [5.0, 5.0, 0.0, 0.0]}
    budgets = [10.0, 10.0, 10.0, 10.0]

    raw_res, solved_orders, traces = solve_inventory_milp(
        products=[prod],
        forecast_matrix=fc_matrix,
        weekly_budgets_scu=budgets,
        warehouse_capacity_slots=20,
    )

    assert raw_res["status"] == "Optimal"
    assert solved_orders["SKU_MINI"] == [5, 0, 0, 0]
    assert abs(raw_res["objective"] - 55.0) < 1e-5

    # Run independent validation
    is_valid, violations = validate_milp_solution(
        products=[prod],
        forecast_matrix=fc_matrix,
        weekly_budgets_scu=budgets,
        warehouse_capacity_slots=20,
        solved_orders=solved_orders,
        solved_traces=traces,
    )
    assert is_valid
    assert len(violations) == 0


def test_milp_zero_budget_and_capacity_violations():
    """Verify solver handles zero budget and rejects invalid initial capacity."""
    prod = ProductInventoryInput(
        sku_id="SKU_ZERO",
        on_hand_units=0,
        incoming_week_1_units=0,
    )
    fc_matrix = {"SKU_ZERO": [10.0, 10.0, 10.0, 10.0]}
    zero_budgets = [0.0, 0.0, 0.0, 0.0]

    raw_res, solved_orders, traces = solve_inventory_milp(
        products=[prod],
        forecast_matrix=fc_matrix,
        weekly_budgets_scu=zero_budgets,
        warehouse_capacity_slots=50,
    )
    assert raw_res["status"] == "Optimal"
    assert solved_orders["SKU_ZERO"] == [0, 0, 0, 0]

    # Initial occupancy exceeding capacity must raise ValueError
    over_prod = ProductInventoryInput(
        sku_id="SKU_OVER",
        on_hand_units=60,
        incoming_week_1_units=0,
    )
    with pytest.raises(ValueError, match="exceeds capacity"):
        solve_inventory_milp(
            products=[over_prod],
            forecast_matrix={"SKU_OVER": [1.0, 1.0, 1.0, 1.0]},
            weekly_budgets_scu=[10.0, 10.0, 10.0, 10.0],
            warehouse_capacity_slots=50,
        )


def test_stochastic_inventory_milp():
    """Verify stochastic MILP solver across multiple quantile scenarios."""
    from demandguard.inventory import solve_stochastic_inventory_milp

    prod = ProductInventoryInput(
        sku_id="SKU_STOCH",
        on_hand_units=0,
        incoming_week_1_units=0,
        unit_purchase_cost_scu=1.0,
        holding_cost_scu_per_unit_week=0.1,
        unmet_penalty_scu_per_unit=10.0,
        storage_slots_per_unit=1.0,
        safety_stock_target_units=0.0,
    )
    quantiles = {
        "SKU_STOCH": {
            "p10": [2.0, 2.0, 0.0, 0.0],
            "p50": [5.0, 5.0, 0.0, 0.0],
            "p90": [10.0, 10.0, 0.0, 0.0],
        }
    }
    budgets = [20.0, 20.0, 20.0, 20.0]

    raw_res, solved_orders, _ = solve_stochastic_inventory_milp(
        products=[prod],
        forecast_quantiles=quantiles,
        weekly_budgets_scu=budgets,
        warehouse_capacity_slots=50,
    )

    assert raw_res["status"] in ("Optimal", "Feasible")
    assert "SKU_STOCH" in solved_orders
    assert solved_orders["SKU_STOCH"][0] > 0

