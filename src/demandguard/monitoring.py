"""Data quality, demand scale shift, and delayed forecast performance monitoring."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def monitor_input_data_quality(
    history_df: pd.DataFrame,
    reference_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Audit data quality, schema integrity, gaps, and demand scale shift."""
    report: dict[str, Any] = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_rows": len(history_df),
        "unique_skus": int(history_df["sku_id"].nunique()) if "sku_id" in history_df else 0,
        "anomalies": [],
        "scale_metrics": {},
    }

    # 1. Schema check
    req_cols = {"sku_id", "week_start", "units_sold"}
    missing_cols = list(req_cols - set(history_df.columns))
    if missing_cols:
        report["anomalies"].append(f"Missing required columns: {missing_cols}")
        return report

    # 2. Check negative or nonfinite units
    nonpos = history_df["units_sold"].isna() | (history_df["units_sold"] < 0)
    if nonpos.any():
        report["anomalies"].append(f"Found {int(nonpos.sum())} invalid/negative sales entries.")

    # 3. Check duplicate keys
    dups = history_df.duplicated(subset=["sku_id", "week_start"])
    if dups.any():
        report["anomalies"].append(f"Found {int(dups.sum())} duplicate (sku_id, week_start) rows.")

    # 4. Check temporal gaps per SKU
    df_sorted = history_df.copy()
    df_sorted["week_start"] = pd.to_datetime(df_sorted["week_start"])
    for sku, group in df_sorted.groupby("sku_id"):
        weeks = sorted(group["week_start"])
        if len(weeks) > 1:
            diffs = pd.Series(weeks).diff().dropna()
            irregular = diffs[diffs != pd.Timedelta(days=7)]
            if len(irregular) > 0:
                report["anomalies"].append(f"SKU {sku} has {len(irregular)} irregular weekly gaps.")

    # 5. Demand scale statistics vs reference
    current_mean = float(history_df["units_sold"].mean())
    current_std = float(history_df["units_sold"].std()) if len(history_df) > 1 else 0.0
    report["scale_metrics"]["current_mean_units"] = current_mean
    report["scale_metrics"]["current_std_units"] = current_std

    if reference_df is not None and "units_sold" in reference_df:
        ref_mean = float(reference_df["units_sold"].mean())
        ref_std = float(reference_df["units_sold"].std())
        report["scale_metrics"]["reference_mean_units"] = ref_mean
        report["scale_metrics"]["reference_std_units"] = ref_std
        mean_ratio = current_mean / ref_mean if ref_mean > 0 else 1.0
        report["scale_metrics"]["mean_ratio_to_reference"] = mean_ratio
        if mean_ratio > 2.0 or mean_ratio < 0.5:
            report["anomalies"].append(
                f"Demand scale drift detected: current mean ({current_mean:.1f}) deviates significantly from reference ({ref_mean:.1f})."
            )

    report["status"] = "HEALTHY" if len(report["anomalies"]) == 0 else "WARNING"
    return report


def monitor_delayed_forecast_accuracy(
    prediction_records: list[dict[str, Any]],
    actual_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute delayed error metrics where actual labels have arrived, show UNAVAILABLE otherwise."""
    if not prediction_records:
        return {"status": "NO_PREDICTIONS", "metrics": {}}

    pred_df = pd.DataFrame(prediction_records)
    act_df = pd.DataFrame(actual_records)

    if act_df.empty or "units_sold" not in act_df:
        return {
            "status": "UNAVAILABLE",
            "message": "Ground truth actual labels have not yet arrived for target dates.",
            "metrics": {},
        }

    merged = pd.merge(
        pred_df,
        act_df,
        left_on=["sku_id", "target_week_start"],
        right_on=["sku_id", "week_start"],
        how="inner",
    )

    if len(merged) == 0:
        return {
            "status": "UNAVAILABLE",
            "message": "No overlapping target dates between predictions and available ground truth.",
            "metrics": {},
        }

    actuals = merged["units_sold"].to_numpy(dtype=float)
    preds = merged["predicted_units"].to_numpy(dtype=float)
    abs_err = np.abs(actuals - preds)
    signed_err = preds - actuals
    sum_act = np.sum(actuals)

    wape = float(np.sum(abs_err) / sum_act) if sum_act > 0 else None
    mae = float(np.mean(abs_err))
    bias = float(np.sum(signed_err) / sum_act) if sum_act > 0 else None

    return {
        "status": "AVAILABLE",
        "evaluated_rows": len(merged),
        "delayed_wape": wape,
        "delayed_mae": mae,
        "delayed_bias": bias,
    }


def run_monitoring_pipeline(
    history_path: str,
    output_path: str,
    reference_path: str = "data/processed/weekly_sales.parquet",
) -> dict[str, Any]:
    """Execute complete monitoring report generation."""
    print(f"Monitoring history data: {history_path}")
    df_hist = pd.read_csv(history_path)

    ref_df = None
    ref_p = Path(reference_path)
    if ref_p.exists():
        ref_df = pd.read_parquet(ref_p)

    report = monitor_input_data_quality(df_hist, reference_df=ref_df)

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Monitoring report saved to {out_p} (Status: {report['status']})")
    return report


def calculate_population_stability_index(
    reference: np.ndarray | list[float],
    current: np.ndarray | list[float],
    num_bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """Calculate Population Stability Index (PSI) between reference baseline and incoming current distribution."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)

    if len(ref) == 0 or len(cur) == 0:
        return 0.0

    # Quantile bin edges based on reference distribution
    quantiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(ref, quantiles)
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    ref_counts, _ = np.histogram(ref, bins=bin_edges)
    cur_counts, _ = np.histogram(cur, bins=bin_edges)

    ref_pct = (ref_counts + epsilon) / (len(ref) + epsilon * num_bins)
    cur_pct = (cur_counts + epsilon) / (len(cur) + epsilon * num_bins)

    psi_val = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(max(0.0, psi_val))


def compute_distribution_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    column: str = "units_sold",
) -> dict[str, Any]:
    """Compute PSI drift score and classification between reference and incoming batch."""
    if column not in reference_df or column not in current_df:
        return {"status": "ERROR", "message": f"Column {column} missing in comparison dataframes."}

    ref_vals = reference_df[column].to_numpy(dtype=float)
    cur_vals = current_df[column].to_numpy(dtype=float)

    psi = calculate_population_stability_index(ref_vals, cur_vals)

    if psi < 0.10:
        drift_level = "NO_DRIFT"
    elif psi < 0.25:
        drift_level = "MODERATE_DRIFT"
    else:
        drift_level = "SIGNIFICANT_DRIFT"

    return {
        "metric": "PSI",
        "psi_score": float(round(psi, 4)),
        "drift_level": drift_level,
        "sample_sizes": {"reference": len(ref_vals), "current": len(cur_vals)},
    }

