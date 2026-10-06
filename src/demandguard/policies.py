"""Inventory ordering policies: P0 rule-based baseline and allocation logic."""

from __future__ import annotations

import math
from typing import Any


def compute_p0_order_quantities(
    current_states: dict[str, dict[str, Any]],
    trailing_4_means: dict[str, float],
    safety_stocks: dict[str, float],
    weekly_budget_scu: float,
    warehouse_capacity_slots: int,
) -> dict[str, int]:
    """Compute P0 constrained order-up-to integer orders with conservative arrival protection."""
    # 1. Calculate desired quantities and relative shortfall
    items = []
    current_occupancy = 0.0

    for sku, st in current_states.items():
        on_hand = st["on_hand_units"]
        incoming = st["incoming_week_1_units"]
        pos = on_hand + incoming
        unit_cost = st.get("unit_purchase_cost_scu", 1.0)
        unit_space = st.get("storage_slots_per_unit", 1.0)

        mean_4 = trailing_4_means.get(sku, 0.0)
        s_i = safety_stocks.get(sku, 0.0)

        target = math.ceil(2.0 * mean_4 + s_i)
        desired = max(0, target - pos)
        rel_shortfall = desired / max(target, 1)

        current_occupancy += (on_hand + incoming) * unit_space

        items.append(
            {
                "sku_id": sku,
                "target": target,
                "desired": desired,
                "rel_shortfall": rel_shortfall,
                "unit_cost": unit_cost,
                "unit_space": unit_space,
                "on_hand": on_hand,
                "incoming": incoming,
            }
        )

    # Sort descending by relative shortfall, tie-break by sku_id ascending
    items.sort(key=lambda x: (-x["rel_shortfall"], x["sku_id"]))

    remaining_budget = float(weekly_budget_scu)
    remaining_space = float(warehouse_capacity_slots - current_occupancy)

    allocated_orders: dict[str, int] = {item["sku_id"]: 0 for item in items}

    # Allocate whole units greedy within available budget and conservative arrival space
    # First pass: allocate desired up to individual limits
    for item in items:
        sku = item["sku_id"]
        desired = item["desired"]
        unit_cost = item["unit_cost"]
        unit_space = item["unit_space"]

        if desired <= 0 or remaining_budget < unit_cost or remaining_space < unit_space:
            allocated_orders[sku] = 0
            continue

        max_by_budget = int(remaining_budget // unit_cost)
        max_by_space = int(remaining_space // unit_space)
        alloc = min(desired, max_by_budget, max_by_space)

        allocated_orders[sku] = alloc
        remaining_budget -= alloc * unit_cost
        remaining_space -= alloc * unit_space

    return allocated_orders


def compute_quantile_spread_safety_stock(
    p10_forecast: float,
    p90_forecast: float,
    service_level_z: float = 1.65,
    lead_time_weeks: float = 1.0,
) -> float:
    """Compute uncertainty-aware safety stock derived directly from predicted quantile spread.

    Estimated sigma ~ (P90 - P10) / 2.56 under approximate normality.
    Safety Stock = z * sigma * sqrt(L).
    """
    spread = max(0.0, float(p90_forecast) - float(p10_forecast))
    implied_sigma = spread / 2.5631  # 2 * 1.28155
    ss = service_level_z * implied_sigma * math.sqrt(lead_time_weeks)
    return max(0.0, float(round(ss, 2)))

