"""Causal direct-horizon feature engineering for pooled forecasting."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

LAG_OFFSETS = [0, 1, 2, 3, 7, 12, 25, 51, 52]
ROLLING_WINDOWS = [4, 13, 26, 52]


def extract_causal_features_for_series(
    sales_array: np.ndarray,
    origin_date: datetime.date,
    horizon: int,
    sku_id: str,
) -> dict[str, Any]:
    """Extract causal historical features from sales_array (indexed 0..c, where -1 is c)."""
    if len(sales_array) < 60:
        raise ValueError(f"History length {len(sales_array)} is less than required 60 weeks.")

    feats: dict[str, Any] = {
        "sku_id": sku_id,
        "origin_week_start": str(origin_date),
        "horizon": int(horizon),
        "target_week_start": str(origin_date + datetime.timedelta(weeks=horizon)),
    }

    # 1. Historical lags relative to origin c (offset 0 is sales_array[-1])
    for off in LAG_OFFSETS:
        idx = -(off + 1)
        if abs(idx) <= len(sales_array):
            feats[f"lag_{off}"] = float(sales_array[idx])
        else:
            feats[f"lag_{off}"] = 0.0

    # 2. Rolling statistics including origin c
    for w in ROLLING_WINDOWS:
        sub = sales_array[-w:]
        feats[f"rolling_mean_{w}"] = float(np.mean(sub))
        feats[f"rolling_std_{w}"] = float(np.std(sub, ddof=1)) if len(sub) > 1 else 0.0
        feats[f"zero_fraction_{w}"] = float(np.mean(sub == 0))

    # 3. Simple trend & momentum ratio
    trail_4 = sales_array[-4:]
    prec_4 = sales_array[-8:-4]
    feats["trend_4_4"] = float(np.mean(trail_4) - np.mean(prec_4))
    m13 = float(feats["rolling_mean_13"])
    feats["momentum_4_13"] = float(feats["rolling_mean_4"] / (m13 + 1e-4))

    # 4. Calendar & Fourier cyclical harmonics
    target_date = origin_date + datetime.timedelta(weeks=horizon)
    orig_woy = origin_date.isocalendar()[1]
    tgt_woy = target_date.isocalendar()[1]
    feats["origin_week_of_year"] = orig_woy
    feats["origin_month"] = origin_date.month
    feats["target_week_of_year"] = tgt_woy
    feats["target_month"] = target_date.month

    # Fourier harmonics (annual cycle)
    feats["sin_woy_orig"] = float(np.sin(2 * np.pi * orig_woy / 52.0))
    feats["cos_woy_orig"] = float(np.cos(2 * np.pi * orig_woy / 52.0))
    feats["sin_woy_tgt"] = float(np.sin(2 * np.pi * tgt_woy / 52.0))
    feats["cos_woy_tgt"] = float(np.cos(2 * np.pi * tgt_woy / 52.0))

    return feats



def build_feature_table(
    panel_df: pd.DataFrame,
    cohort_skus: list[str],
    horizon_weeks: int = 4,
    min_history_weeks: int = 60,
) -> pd.DataFrame:
    """Build full direct-horizon feature table across all valid origins."""
    panel_df = panel_df.copy()
    panel_df["week_start"] = pd.to_datetime(panel_df["week_start"]).dt.date
    all_weeks = sorted(panel_df["week_start"].unique())
    n_weeks = len(all_weeks)

    # Valid origins c index must have at least min_history_weeks (index >= 60 in 1-based, so 0-based idx >= 59)
    # Target week c + h must be <= all_weeks[-1] for training rows with observed targets
    rows = []

    # Create dictionary mapping (sku, week) -> units_sold for fast lookups
    sales_lookup = panel_df.set_index(["sku_id", "week_start"])["units_sold"].to_dict()

    for sku in cohort_skus:
        # Pre-extract full time series for sku
        sku_series = [sales_lookup.get((sku, w), 0) for w in all_weeks]
        sku_arr = np.array(sku_series, dtype=float)

        for orig_idx in range(min_history_weeks - 1, n_weeks):
            orig_date = all_weeks[orig_idx]
            history_prefix = sku_arr[: orig_idx + 1]

            for h in range(1, horizon_weeks + 1):
                tgt_idx = orig_idx + h
                tgt_units = float(sku_arr[tgt_idx]) if tgt_idx < n_weeks else None

                f_dict = extract_causal_features_for_series(
                    sales_array=history_prefix,
                    origin_date=orig_date,
                    horizon=h,
                    sku_id=sku,
                )
                f_dict["target_units"] = tgt_units
                rows.append(f_dict)

    feat_df = pd.DataFrame(rows)
    return feat_df


def generate_and_save_features(config_path: str = "config/project.yaml") -> pd.DataFrame:
    """Generate and save features.parquet from processed weekly sales."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_cfg = cfg["data"]
    cohort_path = Path(data_cfg["cohort_path"])
    panel_path = Path(data_cfg["weekly_sales_path"])
    features_path = Path(data_cfg["features_path"])

    with open(cohort_path, "r", encoding="utf-8") as f:
        cohort_json = json.load(f)
    cohort_skus = [c["sku_id"] for c in cohort_json["cohort"]]

    panel_df = pd.read_parquet(panel_path)
    feat_df = build_feature_table(panel_df, cohort_skus=cohort_skus)

    features_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(feat_df)
    pq.write_table(table, features_path)
    print(
        f"Features table saved to {features_path} ({len(feat_df)} rows, {feat_df['sku_id'].nunique()} SKUs)"
    )
    return feat_df


def compute_recency_weights(
    origin_dates: pd.Series,
    decay_rate: float = 0.98,
) -> np.ndarray:
    """Compute exponential recency sample weights lambda^(T - t) relative to the most recent origin."""
    dates = pd.to_datetime(origin_dates)
    max_date = dates.max()
    weeks_diff = (max_date - dates).dt.days // 7
    weights = np.power(decay_rate, weeks_diff.values)
    # Normalise so mean weight is 1.0
    return weights / (np.mean(weights) + 1e-8)


def build_inference_features(
    history_df: pd.DataFrame,
    as_of_week: datetime.date,
    horizon_weeks: int = 4,
    min_history_weeks: int = 60,
) -> pd.DataFrame:
    """Build forecast feature rows for every SKU in a weekly history ending at `as_of_week`.

    Uses the same causal extractor as training, so any bundle can select its own feature list.
    """
    rows = []
    for sku in sorted(history_df["sku_id"].unique()):
        sub = history_df[history_df["sku_id"] == sku].sort_values("week_start")
        sales = sub["units_sold"].to_numpy(dtype=float)
        if len(sales) < min_history_weeks:
            raise ValueError(
                f"SKU {sku} has {len(sales)} weekly records; at least {min_history_weeks} "
                "consecutive weeks required."
            )
        for h in range(1, horizon_weeks + 1):
            rows.append(extract_causal_features_for_series(sales, as_of_week, h, sku))
    return pd.DataFrame(rows)
