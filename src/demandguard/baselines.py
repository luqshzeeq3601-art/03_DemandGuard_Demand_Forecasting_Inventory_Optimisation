"""Baseline forecasting models: Naive rules and per-SKU ARIMA."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

logger = logging.getLogger(__name__)


def forecast_b1_last_value(
    history_series: pd.Series | np.ndarray,
    horizon_weeks: int = 4,
) -> np.ndarray:
    """B1: Last observed week repeated for all horizons."""
    arr = np.asarray(history_series, dtype=float)
    if len(arr) == 0:
        return np.zeros(horizon_weeks, dtype=float)
    last_val = arr[-1]
    return np.full(horizon_weeks, fill_value=max(0.0, float(last_val)), dtype=float)


def forecast_b2_trailing_mean(
    history_series: pd.Series | np.ndarray,
    horizon_weeks: int = 4,
    window: int = 4,
) -> np.ndarray:
    """B2: Trailing 4-week mean repeated for all horizons."""
    arr = np.asarray(history_series, dtype=float)
    if len(arr) == 0:
        return np.zeros(horizon_weeks, dtype=float)
    recent = arr[-min(len(arr), window) :]
    mean_val = float(np.mean(recent))
    return np.full(horizon_weeks, fill_value=max(0.0, mean_val), dtype=float)


def forecast_b3_seasonal_naive(
    history_series: pd.Series | np.ndarray,
    horizon_weeks: int = 4,
    seasonality: int = 52,
) -> np.ndarray:
    """B3: Annual seasonal naive: y(c + h - 52) for horizon h=1..4."""
    arr = np.asarray(history_series, dtype=float)
    preds = []
    for h in range(1, horizon_weeks + 1):
        target_lag_idx = -seasonality + (h - 1)
        if abs(target_lag_idx) <= len(arr):
            val = max(0.0, float(arr[target_lag_idx]))
        else:
            # Fallback to last value if history shorter than 52
            val = max(0.0, float(arr[-1])) if len(arr) > 0 else 0.0
        preds.append(val)
    return np.array(preds, dtype=float)


def forecast_b4_arima(
    history_series: pd.Series | np.ndarray,
    horizon_weeks: int = 4,
    order: tuple[int, int, int] = (1, 0, 0),
) -> tuple[np.ndarray, bool]:
    """B4: Per-SKU ARIMA model with deterministic B2 fallback on fit failure."""
    arr = np.asarray(history_series, dtype=float)
    try:
        # Fit ARIMA
        model = ARIMA(arr, order=order)
        fitted = model.fit()
        fc = fitted.forecast(steps=horizon_weeks)
        preds = np.maximum(0.0, np.asarray(fc, dtype=float))
        return preds, True
    except Exception as e:
        logger.warning(f"ARIMA{order} fit failed: {e}. Using B2 fallback.")
        fallback_preds = forecast_b2_trailing_mean(arr, horizon_weeks=horizon_weeks)
        return fallback_preds, False


def generate_baseline_predictions_for_origin(
    panel_df: pd.DataFrame,
    origin_week_str: str,
    target_week_starts: list[str],
    cohort_skus: list[str],
    arima_order: tuple[int, int, int] = (1, 0, 0),
) -> pd.DataFrame:
    """Generate all baseline forecasts (B1, B2, B3, B4) for all cohort SKUs at a single origin."""
    panel_df = panel_df.copy()
    panel_df["week_start"] = panel_df["week_start"].astype(str)

    # History up to and including origin_week_str
    hist_df = panel_df[panel_df["week_start"] <= origin_week_str].sort_values(
        ["sku_id", "week_start"]
    )

    records = []
    horizon_weeks = len(target_week_starts)

    for sku in cohort_skus:
        sku_hist = hist_df[hist_df["sku_id"] == sku]["units_sold"].values

        b1_preds = forecast_b1_last_value(sku_hist, horizon_weeks=horizon_weeks)
        b2_preds = forecast_b2_trailing_mean(sku_hist, horizon_weeks=horizon_weeks)
        b3_preds = forecast_b3_seasonal_naive(sku_hist, horizon_weeks=horizon_weeks)
        b4_preds, arima_ok = forecast_b4_arima(
            sku_hist, horizon_weeks=horizon_weeks, order=arima_order
        )

        for h_idx, (tgt_week, b1, b2, b3, b4) in enumerate(
            zip(target_week_starts, b1_preds, b2_preds, b3_preds, b4_preds), start=1
        ):
            # Record each model row
            for model_id, pred_val in [
                ("B1", b1),
                ("B2", b2),
                ("B3", b3),
                ("B4", b4),
            ]:
                records.append(
                    {
                        "model_id": model_id,
                        "sku_id": sku,
                        "origin_week_start": origin_week_str,
                        "target_week_start": tgt_week,
                        "horizon": h_idx,
                        "predicted_units": float(pred_val),
                        "arima_fit_success": arima_ok if model_id == "B4" else True,
                    }
                )

    return pd.DataFrame(records)
