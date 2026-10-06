"""Integration tests for FastAPI serving endpoints (Task T14)."""

import pandas as pd
from fastapi.testclient import TestClient

from demandguard.api import app

client = TestClient(app)


def test_api_health():
    """Verify health endpoint."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_ready():
    """Verify ready endpoint."""
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["model_artifact"] == "READY"
    assert data["checks"]["pulp_cbc_solver"] == "READY"


def test_api_forecast_and_reorder():
    """Verify forecast and reorder endpoints with synthetic requests."""
    df_hist = pd.read_csv("tests/fixtures/demo_history.csv")
    history_records = df_hist.to_dict(orient="records")
    as_of = str(df_hist["week_start"].max())

    # 1. POST /forecast
    fc_req = {
        "as_of_week_start": as_of,
        "horizon_weeks": 4,
        "history": history_records,
    }
    resp_fc = client.post("/forecast", json=fc_req)
    assert resp_fc.status_code == 200
    fc_data = resp_fc.json()
    assert fc_data["status"] == "SUCCESS"
    assert len(fc_data["predictions"]) == 8

    # 2. POST /reorder
    reorder_req = {
        "as_of_week_start": as_of,
        "warehouse_capacity_slots": 5000,
        "weekly_budgets_scu": [2000.0, 2000.0, 2000.0, 2000.0],
        "inventory": [
            {"sku_id": "85123A", "on_hand_units": 100, "incoming_week_1_units": 0},
            {"sku_id": "84077", "on_hand_units": 50, "incoming_week_1_units": 0},
        ],
        "history": history_records,
    }
    resp_reord = client.post("/reorder", json=reorder_req)
    assert resp_reord.status_code == 200
    reord_data = resp_reord.json()
    assert reord_data["status"] == "OPTIMAL"
    assert reord_data["validation_status"] == "PASSED"
    assert len(reord_data["worklist"]) == 2


def test_api_errors_and_capacity_conflict():
    """Verify 422 on invalid input and 409 on initial capacity breach."""
    # 422: missing fields or empty history
    resp_empty = client.post(
        "/forecast", json={"as_of_week_start": "2011-01-01", "horizon_weeks": 4, "history": []}
    )
    assert resp_empty.status_code == 422

    # 409: initial stock exceeds capacity
    df_hist = pd.read_csv("tests/fixtures/demo_history.csv")
    history_records = df_hist.to_dict(orient="records")
    as_of = str(df_hist["week_start"].max())

    reorder_over = {
        "as_of_week_start": as_of,
        "warehouse_capacity_slots": 50,
        "weekly_budgets_scu": [100.0, 100.0, 100.0, 100.0],
        "inventory": [
            {"sku_id": "85123A", "on_hand_units": 100, "incoming_week_1_units": 0},
        ],
        "history": history_records,
    }
    resp_over = client.post("/reorder", json=reorder_over)
    assert resp_over.status_code == 409
