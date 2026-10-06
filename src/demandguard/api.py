"""FastAPI application serving DemandGuard forecast and reorder contracts."""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any

import pandas as pd
import pulp
from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from demandguard.contracts import (
    ForecastPredictionRow,
    ForecastRequest,
    ForecastResponse,
    ReorderResponse,
    ReorderScenarioRequest,
)
from demandguard.features import build_inference_features
from demandguard.inventory import (
    build_reorder_worklist,
    solve_inventory_milp,
    validate_milp_solution,
)
from demandguard.model import DemandGuardModel

app = FastAPI(
    title="DemandGuard API",
    description="Production API for Demand Forecasting and MILP Inventory Replenishment",
    version="0.1.0",
)

# Only trusted local bundles are served; the env var selects one by name, never by path.
TRUSTED_ARTIFACT_DIRS = {"champion": Path("artifacts/champion"), "v02": Path("artifacts/v02")}
_model_name = os.environ.get("DEMANDGUARD_MODEL", "champion")
if _model_name not in TRUSTED_ARTIFACT_DIRS:
    raise RuntimeError(
        f"DEMANDGUARD_MODEL must be one of {sorted(TRUSTED_ARTIFACT_DIRS)}, got {_model_name!r}."
    )
ARTIFACT_DIR = TRUSTED_ARTIFACT_DIRS[_model_name]


def get_champion_model() -> tuple[DemandGuardModel, dict[str, Any]]:
    """Helper to load champion model or raise 503."""
    if not (ARTIFACT_DIR / "metadata.json").exists() or not (ARTIFACT_DIR / "model.txt").exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Champion model artifact not available. Please run model selection and freezing first.",
        )
    return DemandGuardModel.load_bundle(ARTIFACT_DIR)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Process liveness endpoint."""
    return {"status": "ok", "service": "DemandGuard API", "version": "0.1.0"}


@app.get("/ready", tags=["System"])
def readiness_check() -> dict[str, Any]:
    """Prerequisite readiness check for model artifact and PuLP CBC solver."""
    checks = {}

    # 1. Model check
    art_ok = (ARTIFACT_DIR / "metadata.json").exists() and (ARTIFACT_DIR / "model.txt").exists()
    checks["model_artifact"] = "READY" if art_ok else "UNAVAILABLE"

    # 2. Solver check
    try:
        prob = pulp.LpProblem("ReadyTest", pulp.LpMinimize)
        x = pulp.LpVariable("x", lowBound=0, cat=pulp.LpInteger)
        prob += x >= 1
        solver = pulp.PULP_CBC_CMD(msg=False)
        sol_status = prob.solve(solver)
        solver_ok = pulp.LpStatus[sol_status] == "Optimal"
        checks["pulp_cbc_solver"] = "READY" if solver_ok else "UNAVAILABLE"
    except Exception as e:
        checks["pulp_cbc_solver"] = f"ERROR: {e}"
        solver_ok = False

    if not (art_ok and solver_ok):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Service prerequisites not ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.post("/forecast", response_model=ForecastResponse, tags=["Forecasting"])
def create_forecast(req: ForecastRequest) -> ForecastResponse:
    """Generate 4-week forecasts from weekly history."""
    model, metadata = get_champion_model()

    if not req.history:
        raise HTTPException(status_code=422, detail="History cannot be empty.")

    hist_data = [r.model_dump() for r in req.history]
    df_hist = pd.DataFrame(hist_data)
    df_hist["week_start"] = pd.to_datetime(df_hist["week_start"]).dt.date

    as_of_date = pd.to_datetime(req.as_of_week_start).date()

    try:
        feat_df = build_inference_features(df_hist, as_of_date, horizon_weeks=req.horizon_weeks)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    raw_preds = model.predict(feat_df)

    predictions = []
    for idx, r in feat_df.iterrows():
        predictions.append(
            ForecastPredictionRow(
                sku_id=r["sku_id"],
                origin_week_start=str(r["origin_week_start"]),
                target_week_start=str(r["target_week_start"]),
                horizon=int(r["horizon"]),
                predicted_units=float(raw_preds[idx]),
                model_version=metadata.get("champion_model_id", "v0.1.0"),
                data_version="OnlineRetailII_UK",
                run_id=metadata.get("created_at_utc", "local_run"),
            )
        )

    return ForecastResponse(
        status="SUCCESS",
        as_of_week_start=req.as_of_week_start,
        model_version=metadata.get("champion_model_id", "v0.1.0"),
        predictions=predictions,
    )


@app.post("/reorder", response_model=ReorderResponse, tags=["Inventory Optimization"])
def create_reorder_plan(req: ReorderScenarioRequest) -> ReorderResponse:
    """Generate optimal and validated 4-week reorder worklist."""
    if len(req.weekly_budgets_scu) != 4:
        raise HTTPException(
            status_code=422, detail="weekly_budgets_scu must contain exactly 4 values."
        )

    # 1. Obtain forecast matrix
    fc_matrix: dict[str, list[float]] = {}
    if req.precomputed_forecasts:
        for f in req.precomputed_forecasts:
            if f.sku_id not in fc_matrix:
                fc_matrix[f.sku_id] = []
            fc_matrix[f.sku_id].append(f.predicted_units)
    elif req.history:
        fc_resp = create_forecast(
            ForecastRequest(
                as_of_week_start=req.as_of_week_start, horizon_weeks=4, history=req.history
            )
        )
        for f in fc_resp.predictions:
            if f.sku_id not in fc_matrix:
                fc_matrix[f.sku_id] = []
            fc_matrix[f.sku_id].append(f.predicted_units)
    else:
        raise HTTPException(
            status_code=422, detail="Either history or precomputed_forecasts must be provided."
        )

    # 2. Check initial capacity bounds
    total_init_occ = sum(
        (p.on_hand_units + p.incoming_week_1_units) * p.storage_slots_per_unit
        for p in req.inventory
    )
    if total_init_occ > req.warehouse_capacity_slots:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Initial warehouse occupancy {total_init_occ:.1f} exceeds capacity {req.warehouse_capacity_slots}.",
        )

    # 3. Solve MILP
    try:
        raw_res, solved_orders, traces = solve_inventory_milp(
            products=req.inventory,
            forecast_matrix=fc_matrix,
            weekly_budgets_scu=req.weekly_budgets_scu,
            warehouse_capacity_slots=req.warehouse_capacity_slots,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Solver failed: {e}")

    # 4. Validate
    is_valid, violations = validate_milp_solution(
        products=req.inventory,
        forecast_matrix=fc_matrix,
        weekly_budgets_scu=req.weekly_budgets_scu,
        warehouse_capacity_slots=req.warehouse_capacity_slots,
        solved_orders=solved_orders,
        solved_traces=traces,
    )

    response = build_reorder_worklist(
        products=req.inventory,
        forecast_matrix=fc_matrix,
        solved_orders=solved_orders,
        as_of_week_start=req.as_of_week_start,
        solver_meta=raw_res,
        validation_status="PASSED" if is_valid else "FAILED",
        warnings=violations,
    )
    return response


# Asynchronous background job registry
BACKGROUND_JOBS: dict[str, dict[str, Any]] = {}


def _execute_async_reorder_job(job_id: str, req: ReorderScenarioRequest) -> None:
    """Worker task to execute optimization job asynchronously."""
    try:
        BACKGROUND_JOBS[job_id]["status"] = "RUNNING"
        res = create_reorder_plan(req)
        BACKGROUND_JOBS[job_id]["status"] = "COMPLETED"
        BACKGROUND_JOBS[job_id]["result"] = res.model_dump()
    except Exception as e:
        BACKGROUND_JOBS[job_id]["status"] = "FAILED"
        BACKGROUND_JOBS[job_id]["error"] = str(e)



@app.post("/reorder/async", tags=["Optimization"])
def create_async_reorder_job(
    req: ReorderScenarioRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Submit asynchronous long-horizon MILP inventory optimization job."""
    import uuid

    job_id = f"job-{uuid.uuid4().hex[:8]}"
    BACKGROUND_JOBS[job_id] = {
        "job_id": job_id,
        "status": "QUEUED",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }
    background_tasks.add_task(_execute_async_reorder_job, job_id, req)
    return {"job_id": job_id, "status": "QUEUED"}


@app.get("/jobs/{job_id}", tags=["Optimization"])
def get_job_status(job_id: str) -> dict[str, Any]:
    """Poll status and retrieve result of an asynchronous optimization job."""
    if job_id not in BACKGROUND_JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return BACKGROUND_JOBS[job_id]

