"""Pydantic schemas and shared data contracts for DemandGuard."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WeeklyHistoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku_id: str
    week_start: str
    units_sold: int = Field(ge=0)


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of_week_start: str
    horizon_weeks: int = Field(default=4, ge=1, le=4)
    history: list[WeeklyHistoryRow]


class ForecastPredictionRow(BaseModel):
    sku_id: str
    origin_week_start: str
    target_week_start: str
    horizon: int
    predicted_units: float = Field(ge=0.0)
    model_version: str
    data_version: str
    run_id: str


class ForecastResponse(BaseModel):
    status: Literal["SUCCESS", "ERROR"]
    as_of_week_start: str
    model_version: str
    predictions: list[ForecastPredictionRow]
    warnings: list[str] = Field(default_factory=list)


class ProductInventoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku_id: str
    on_hand_units: int = Field(ge=0)
    incoming_week_1_units: int = Field(ge=0)
    unit_purchase_cost_scu: float = Field(default=1.0, gt=0)
    holding_cost_scu_per_unit_week: float = Field(default=0.02, gt=0)
    unmet_penalty_scu_per_unit: float = Field(default=5.0, gt=0)
    safety_deficit_penalty_scu: float = Field(default=0.5, ge=0)
    storage_slots_per_unit: float = Field(default=1.0, gt=0)
    safety_stock_target_units: float = Field(default=0.0, ge=0)


class ReorderScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of_week_start: str
    warehouse_capacity_slots: int = Field(gt=0)
    weekly_budgets_scu: list[float]  # 4 weeks
    inventory: list[ProductInventoryInput]
    history: list[WeeklyHistoryRow] | None = None
    precomputed_forecasts: list[ForecastPredictionRow] | None = None


class ReorderWorklistRow(BaseModel):
    sku_id: str
    current_on_hand: int
    incoming_week_1: int
    forecast_week_1: float
    forecast_week_2: float
    forecast_week_3: float
    forecast_week_4: float
    order_q1: int
    expected_arrival_week_2: int
    spend_week_1_scu: float
    provisional_q2: int
    provisional_q3: int
    provisional_q4: int = 0


class ReorderResponse(BaseModel):
    status: Literal["OPTIMAL", "INFEASIBLE", "ERROR"]
    as_of_week_start: str
    solver_name: str
    solve_runtime_seconds: float
    total_objective_scu: float | None = None
    validation_status: Literal["PASSED", "FAILED"]
    worklist: list[ReorderWorklistRow]
    warnings: list[str] = Field(default_factory=list)
