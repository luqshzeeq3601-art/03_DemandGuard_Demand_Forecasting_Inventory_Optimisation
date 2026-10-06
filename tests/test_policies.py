"""Tests for P0 rule-based baseline policy (Task T08 / Gate G2)."""

from demandguard.policies import compute_p0_order_quantities


def test_p0_budget_and_arrival_capacity_limits():
    """Verify P0 prioritises relative shortfall and respects both budget and space."""
    # Two products competing:
    # SKU_A: pos=0, mean=10, safety=0 -> target=20, desired=20, rel_shortfall=1.0
    # SKU_B: pos=15, mean=10, safety=0 -> target=20, desired=5, rel_shortfall=5/20=0.25
    states = {
        "SKU_A": {
            "on_hand_units": 0,
            "incoming_week_1_units": 0,
            "unit_purchase_cost_scu": 1.0,
            "storage_slots_per_unit": 1.0,
        },
        "SKU_B": {
            "on_hand_units": 15,
            "incoming_week_1_units": 0,
            "unit_purchase_cost_scu": 1.0,
            "storage_slots_per_unit": 1.0,
        },
    }
    means = {"SKU_A": 10.0, "SKU_B": 10.0}
    safeties = {"SKU_A": 0.0, "SKU_B": 0.0}

    # Case 1: Budget = 12, Capacity = 100
    # SKU_A desired=20 -> takes 12, budget exhausted -> SKU_B gets 0
    orders = compute_p0_order_quantities(
        current_states=states,
        trailing_4_means=means,
        safety_stocks=safeties,
        weekly_budget_scu=12.0,
        warehouse_capacity_slots=100,
    )
    assert orders["SKU_A"] == 12
    assert orders["SKU_B"] == 0

    # Case 2: Budget = 100, Capacity = 25
    # Current occupancy = 0 + 15 = 15. Remaining space = 25 - 15 = 10.
    # SKU_A desired=20, space allows only 10 -> takes 10 -> space exhausted -> SKU_B gets 0
    orders_cap = compute_p0_order_quantities(
        current_states=states,
        trailing_4_means=means,
        safety_stocks=safeties,
        weekly_budget_scu=100.0,
        warehouse_capacity_slots=25,
    )
    assert orders_cap["SKU_A"] == 10
    assert orders_cap["SKU_B"] == 0


def test_quantile_spread_safety_stock():
    """Verify dynamic safety stock scales with quantile spread."""
    from demandguard.policies import compute_quantile_spread_safety_stock

    # Tighter spread -> lower safety stock
    ss_low = compute_quantile_spread_safety_stock(p10_forecast=90.0, p90_forecast=110.0)
    # Wider spread -> higher safety stock
    ss_high = compute_quantile_spread_safety_stock(p10_forecast=50.0, p90_forecast=150.0)

    assert ss_low > 0
    assert ss_high > ss_low

