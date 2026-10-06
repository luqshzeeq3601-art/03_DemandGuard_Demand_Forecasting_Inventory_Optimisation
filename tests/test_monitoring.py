"""Tests for monitoring anomalies and delayed forecast metrics (Task T16 / Gate G6)."""

import pandas as pd

from demandguard.monitoring import (
    monitor_delayed_forecast_accuracy,
    monitor_input_data_quality,
)


def test_monitor_healthy_and_shifted_inputs():
    """Verify healthy data passes and anomalies are detected."""
    # Healthy dataset
    df_healthy = pd.DataFrame(
        [
            {"sku_id": "SKU_1", "week_start": "2011-01-03", "units_sold": 50},
            {"sku_id": "SKU_1", "week_start": "2011-01-10", "units_sold": 55},
            {"sku_id": "SKU_1", "week_start": "2011-01-17", "units_sold": 48},
        ]
    )
    rep_healthy = monitor_input_data_quality(df_healthy)
    assert rep_healthy["status"] == "HEALTHY"
    assert len(rep_healthy["anomalies"]) == 0

    # Anomalous dataset with duplicate, negative value, and gap
    df_bad = pd.DataFrame(
        [
            {"sku_id": "SKU_1", "week_start": "2011-01-03", "units_sold": -10},  # negative
            {"sku_id": "SKU_1", "week_start": "2011-01-03", "units_sold": 50},  # duplicate key
            {
                "sku_id": "SKU_1",
                "week_start": "2011-01-24",
                "units_sold": 50,
            },  # irregular gap (jumped 21 days)
        ]
    )
    rep_bad = monitor_input_data_quality(df_bad)
    assert rep_bad["status"] == "WARNING"
    assert len(rep_bad["anomalies"]) >= 2


def test_monitor_delayed_forecast_metrics():
    """Verify delayed error calculation when ground truth arrives and UNAVAILABLE when absent."""
    preds = [
        {"sku_id": "SKU_1", "target_week_start": "2011-02-07", "predicted_units": 60.0},
        {"sku_id": "SKU_1", "target_week_start": "2011-02-14", "predicted_units": 40.0},
    ]

    # When ground truth is absent
    res_absent = monitor_delayed_forecast_accuracy(preds, [])
    assert res_absent["status"] == "UNAVAILABLE"

    # When ground truth arrives
    actuals = [
        {"sku_id": "SKU_1", "week_start": "2011-02-07", "units_sold": 50.0},
        {"sku_id": "SKU_1", "week_start": "2011-02-14", "units_sold": 50.0},
    ]
    res_avail = monitor_delayed_forecast_accuracy(preds, actuals)
    assert res_avail["status"] == "AVAILABLE"
    assert res_avail["evaluated_rows"] == 2
    # Errors: |50-60|=10, |50-40|=10 -> sum_abs=20 / sum_act=100 -> WAPE = 0.2
    assert abs(res_avail["delayed_wape"] - 0.2) < 1e-6
    assert abs(res_avail["delayed_mae"] - 10.0) < 1e-6


def test_psi_drift_detection():
    """Verify PSI calculation for identical and drifted distributions."""
    import numpy as np

    from demandguard.monitoring import (
        calculate_population_stability_index,
        compute_distribution_drift,
    )

    np.random.seed(42)
    ref = np.random.normal(50, 10, 500)
    cur_stable = np.random.normal(50, 10, 500)
    cur_drifted = np.random.normal(120, 20, 500)

    psi_stable = calculate_population_stability_index(ref, cur_stable)
    psi_drifted = calculate_population_stability_index(ref, cur_drifted)

    assert psi_stable < 0.10
    assert psi_drifted > 0.25

    df_ref = pd.DataFrame({"units_sold": ref})
    df_drift = pd.DataFrame({"units_sold": cur_drifted})
    drift_rep = compute_distribution_drift(df_ref, df_drift)
    assert drift_rep["drift_level"] == "SIGNIFICANT_DRIFT"


def test_monitoring_pipeline_reports_distribution_drift(tmp_path):
    """`monitor` must include PSI and KS drift for SKUs shared with the reference."""
    import json

    import numpy as np

    from demandguard.monitoring import run_monitoring_pipeline

    weeks = pd.date_range("2020-01-06", periods=20, freq="7D")
    rng = np.random.default_rng(0)
    ref = pd.DataFrame(
        {"sku_id": "A", "week_start": weeks.date, "units_sold": rng.poisson(100, 20)}
    )
    ref_path = tmp_path / "ref.parquet"
    ref.to_parquet(ref_path)

    shifted = ref.assign(units_sold=ref["units_sold"] * 5)
    hist_path = tmp_path / "hist.csv"
    shifted.to_csv(hist_path, index=False)
    out_path = tmp_path / "mon.json"

    report = run_monitoring_pipeline(str(hist_path), str(out_path), str(ref_path))

    drift = report["distribution_drift"]
    assert drift["shared_skus"] == 1
    assert drift["drift_level"] == "SIGNIFICANT_DRIFT"
    assert drift["ks_p_value"] < 0.01
    assert report["status"] == "WARNING"
    assert json.loads(out_path.read_text())["distribution_drift"]["metric"] == "PSI+KS"
