"""Shared deterministic inventory state transition and historical simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ProductInventoryState:
    sku_id: str
    on_hand_units: int
    incoming_week_1_units: int
    unit_purchase_cost_scu: float = 1.0
    holding_cost_scu_per_unit_week: float = 0.02
    unmet_penalty_scu_per_unit: float = 5.0
    storage_slots_per_unit: float = 1.0


@dataclass
class WeeklyStepResult:
    week_start: str
    sku_id: str
    starting_on_hand: int
    received_shipment: int
    on_hand_after_receipt: int
    placed_order_q1: int
    realized_demand: int
    realized_sales: int
    unmet_demand: int
    ending_on_hand: int
    ending_incoming: int
    purchase_spend_scu: float
    holding_cost_scu: float
    unmet_penalty_scu: float
    total_week_cost_scu: float
    capacity_breached: bool


def step_product_inventory(
    state: ProductInventoryState,
    placed_order_q1: int,
    realized_demand: int,
    week_start: str,
    warehouse_capacity_slots: int | None = None,
) -> tuple[ProductInventoryState, WeeklyStepResult]:
    """Execute single-product deterministic state transition for one week."""
    starting_on_hand = int(state.on_hand_units)
    received = int(state.incoming_week_1_units)
    available_stock = starting_on_hand + received

    # Check capacity breach after receipt before demand
    capacity_breached = False
    if warehouse_capacity_slots is not None:
        occupancy = available_stock * state.storage_slots_per_unit
        if occupancy > warehouse_capacity_slots:
            capacity_breached = True

    # Realise demand and lost sales
    demand = int(max(0, realized_demand))
    sales = min(available_stock, demand)
    unmet = max(0, demand - available_stock)
    ending_on_hand = available_stock - sales

    # Costs
    order_q1 = int(max(0, placed_order_q1))
    purchase_spend = order_q1 * state.unit_purchase_cost_scu
    holding_cost = ending_on_hand * state.holding_cost_scu_per_unit_week
    unmet_penalty = unmet * state.unmet_penalty_scu_per_unit
    total_week_cost = purchase_spend + holding_cost + unmet_penalty

    # New state for next week
    new_state = ProductInventoryState(
        sku_id=state.sku_id,
        on_hand_units=ending_on_hand,
        incoming_week_1_units=order_q1,  # Arrives at beginning of next week
        unit_purchase_cost_scu=state.unit_purchase_cost_scu,
        holding_cost_scu_per_unit_week=state.holding_cost_scu_per_unit_week,
        unmet_penalty_scu_per_unit=state.unmet_penalty_scu_per_unit,
        storage_slots_per_unit=state.storage_slots_per_unit,
    )

    result = WeeklyStepResult(
        week_start=week_start,
        sku_id=state.sku_id,
        starting_on_hand=starting_on_hand,
        received_shipment=received,
        on_hand_after_receipt=available_stock,
        placed_order_q1=order_q1,
        realized_demand=demand,
        realized_sales=sales,
        unmet_demand=unmet,
        ending_on_hand=ending_on_hand,
        ending_incoming=order_q1,
        purchase_spend_scu=purchase_spend,
        holding_cost_scu=holding_cost,
        unmet_penalty_scu=unmet_penalty,
        total_week_cost_scu=total_week_cost,
        capacity_breached=capacity_breached,
    )

    return new_state, result


def compute_simulation_summary(
    step_results: list[WeeklyStepResult],
    final_states: dict[str, ProductInventoryState],
    terminal_value_fraction: float = 0.5,
) -> dict[str, Any]:
    """Compute overall realised business metrics, fill rate, and terminal value adjustment."""
    if not step_results:
        return {}

    df = pd.DataFrame([r.__dict__ for r in step_results])

    total_demand = int(df["realized_demand"].sum())
    total_sales = int(df["realized_sales"].sum())
    total_unmet = int(df["unmet_demand"].sum())
    total_purchase_spend = float(df["purchase_spend_scu"].sum())
    total_holding_cost = float(df["holding_cost_scu"].sum())
    total_unmet_penalty = float(df["unmet_penalty_scu"].sum())

    # Terminal value of ending on-hand + prepaid pipeline
    terminal_value = 0.0
    final_on_hand_units = 0
    final_pipeline_units = 0
    for sku, st in final_states.items():
        val = (st.on_hand_units + st.incoming_week_1_units) * st.unit_purchase_cost_scu
        terminal_value += val * terminal_value_fraction
        final_on_hand_units += st.on_hand_units
        final_pipeline_units += st.incoming_week_1_units

    net_realized_cost = (
        total_purchase_spend + total_holding_cost + total_unmet_penalty - terminal_value
    )
    fill_rate = (total_sales / total_demand) if total_demand > 0 else 1.0

    # Count weeks with unmet units
    weekly_unmet = df.groupby("week_start")["unmet_demand"].sum()
    weeks_with_unmet = int((weekly_unmet > 0).sum())
    total_weeks = len(weekly_unmet)

    capacity_breaches = int(df["capacity_breached"].sum())

    return {
        "total_weeks": total_weeks,
        "total_demand": total_demand,
        "total_sales": total_sales,
        "total_unmet_units": total_unmet,
        "fill_rate": fill_rate,
        "weeks_with_unmet": weeks_with_unmet,
        "total_purchase_spend_scu": total_purchase_spend,
        "total_holding_cost_scu": total_holding_cost,
        "total_unmet_penalty_scu": total_unmet_penalty,
        "terminal_value_scu": terminal_value,
        "net_realized_cost_scu": net_realized_cost,
        "final_on_hand_units": final_on_hand_units,
        "final_pipeline_units": final_pipeline_units,
        "capacity_breaches": capacity_breaches,
    }
