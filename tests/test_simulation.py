"""Tests for inventory simulation timing, no double receipts, and lost sales."""

from demandguard.simulation import (
    ProductInventoryState,
    step_product_inventory,
)


def test_simulation_step_timing_and_lost_sales():
    """Verify receipt before demand, lost sales not backlogged, and cost accounting."""
    state = ProductInventoryState(
        sku_id="SKU_TEST",
        on_hand_units=10,
        incoming_week_1_units=5,  # Arrives week 1 -> total available = 15
        unit_purchase_cost_scu=1.0,
        holding_cost_scu_per_unit_week=0.02,
        unmet_penalty_scu_per_unit=5.0,
    )

    # Week 1: demand is 20 -> available 15 -> sales 15, unmet 5, ending stock 0
    # Placed order Q1 = 8 -> arrives week 2
    new_state, res = step_product_inventory(
        state=state,
        placed_order_q1=8,
        realized_demand=20,
        week_start="2011-01-03",
    )

    assert res.received_shipment == 5
    assert res.on_hand_after_receipt == 15
    assert res.realized_sales == 15
    assert res.unmet_demand == 5
    assert res.ending_on_hand == 0
    assert res.ending_incoming == 8

    # Costs: purchase = 8 * 1 = 8.0, holding = 0 * 0.02 = 0, unmet penalty = 5 * 5 = 25.0 -> total 33.0
    assert res.purchase_spend_scu == 8.0
    assert res.holding_cost_scu == 0.0
    assert res.unmet_penalty_scu == 25.0
    assert res.total_week_cost_scu == 33.0

    # Week 2: starting on hand = 0, received = 8 -> available 8. Demand = 4 -> sales 4, unmet 0, ending 4.
    new_state_2, res_2 = step_product_inventory(
        state=new_state,
        placed_order_q1=0,
        realized_demand=4,
        week_start="2011-01-10",
    )

    assert res_2.on_hand_after_receipt == 8
    assert res_2.realized_sales == 4
    assert res_2.unmet_demand == 0
    assert res_2.ending_on_hand == 4
    assert res_2.ending_incoming == 0
    # Costs: purchase = 0, holding = 4 * 0.02 = 0.08, unmet = 0 -> total 0.08
    assert abs(res_2.holding_cost_scu - 0.08) < 1e-6
