"""Cohort selection and chronological temporal splits contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


def build_cohort_and_splits(config_path: str = "config/project.yaml") -> dict[str, Any]:
    """Select 60-week prefix cohort, build zero-filled panel, and generate chronological split manifest."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_cfg = cfg["data"]
    cohort_cfg = cfg["cohort"]
    splits_cfg = cfg["splits"]

    weekly_sales_path = Path(data_cfg["weekly_sales_path"])
    cohort_path = Path(data_cfg["cohort_path"])
    split_manifest_path = Path(data_cfg["split_manifest_path"])

    if not weekly_sales_path.exists():
        raise FileNotFoundError(
            f"Weekly sales panel {weekly_sales_path} not found. Run prepare first."
        )

    weekly_df = pd.read_parquet(weekly_sales_path)
    weekly_df["week_start"] = pd.to_datetime(weekly_df["week_start"]).dt.date

    # 1. Identify all complete unique calendar weeks in order
    all_weeks = sorted(weekly_df["week_start"].unique())
    n_weeks = len(all_weeks)
    print(
        f"Total complete calendar weeks in dataset: {n_weeks} (from {all_weeks[0]} to {all_weeks[-1]})"
    )

    min_total_weeks = cohort_cfg.get("min_total_weeks", 100)
    if n_weeks < min_total_weeks:
        raise ValueError(
            f"Gate G1 failure: Dataset has {n_weeks} complete weeks, but required minimum is {min_total_weeks}."
        )

    # 2. Select cohort using ONLY the first 60 complete weeks
    prefix_weeks_count = cohort_cfg.get("prefix_weeks", 60)
    prefix_weeks = all_weeks[:prefix_weeks_count]
    first_8_weeks = set(prefix_weeks[: cohort_cfg.get("first_active_window_weeks", 8)])
    prefix_set = set(prefix_weeks)

    prefix_df = weekly_df[weekly_df["week_start"].isin(prefix_set)].copy()

    # Per SKU statistics in prefix
    sku_stats = []
    for sku, group in prefix_df.groupby("sku_id"):
        sales_weeks = set(group[group["units_sold"] > 0]["week_start"])
        has_first_8 = len(sales_weeks.intersection(first_8_weeks)) > 0
        active_weeks_count = len(sales_weeks)
        total_units = int(group["units_sold"].sum())

        if (
            has_first_8
            and active_weeks_count >= cohort_cfg.get("min_active_prefix_weeks", 40)
            and total_units > 0
        ):
            sku_stats.append(
                {
                    "sku_id": str(sku),
                    "total_prefix_units": total_units,
                    "active_prefix_weeks": active_weeks_count,
                    "has_sale_in_first_8_weeks": True,
                }
            )

    # Sort descending by total_prefix_units, tie-break by sku_id ascending
    sku_stats.sort(key=lambda x: (-x["total_prefix_units"], x["sku_id"]))

    max_products = cohort_cfg.get("max_products", 30)
    min_products = cohort_cfg.get("min_products", 10)
    selected_cohort = sku_stats[:max_products]
    selected_sku_ids = [s["sku_id"] for s in selected_cohort]

    print(
        f"Qualified cohort products in first 60 weeks: {len(sku_stats)}. Selected top {len(selected_sku_ids)} SKUs."
    )
    if len(selected_sku_ids) < min_products:
        raise ValueError(
            f"Gate G1 failure: Qualified cohort size {len(selected_sku_ids)} is below minimum viable {min_products}."
        )

    # Save cohort.json
    cohort_data = {
        "prefix_start_date": str(prefix_weeks[0]),
        "prefix_end_date": str(prefix_weeks[-1]),
        "prefix_weeks_count": len(prefix_weeks),
        "selection_rule": (
            "Positive sale in first 8 weeks, >=40 active sales weeks in first 60 weeks, "
            "ranked by total prefix units descending (tie-break sku_id asc), max 30 SKUs."
        ),
        "selected_skus_count": len(selected_sku_ids),
        "cohort": selected_cohort,
    }
    cohort_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cohort_path, "w", encoding="utf-8") as f:
        json.dump(cohort_data, f, indent=2)

    # 3. Create zero-filled panel for the selected cohort over all N weeks
    full_index = (
        pd.MultiIndex.from_product(
            [selected_sku_ids, all_weeks],
            names=["sku_id", "week_start"],
        )
        .to_frame()
        .reset_index(drop=True)
    )

    panel_merged = pd.merge(
        full_index,
        weekly_df[["sku_id", "week_start", "units_sold"]],
        on=["sku_id", "week_start"],
        how="left",
    )
    panel_merged["units_sold"] = panel_merged["units_sold"].fillna(0).astype(int)
    panel_merged = panel_merged.sort_values(by=["sku_id", "week_start"]).reset_index(drop=True)

    # Overwrite processed weekly_sales.parquet with full zero-filled cohort panel
    table = pa.Table.from_pandas(panel_merged)
    pq.write_table(table, weekly_sales_path)
    print(f"Updated {weekly_sales_path} with zero-filled cohort panel ({len(panel_merged)} rows)")

    # 4. Construct chronological split manifest
    # 1-indexed complete weeks: index 1 is all_weeks[0], index N is all_weeks[N-1]
    # Week index helper: 1..N -> all_weeks[idx - 1]
    val_origin_offsets = splits_cfg.get("validation_origins_offset", [28, 24, 20, 16])
    val_origins = [n_weeks - off for off in val_origin_offsets]

    test_origin_offsets = splits_cfg.get("test_origins_offset", [12, 8, 4])
    test_origins = [n_weeks - off for off in test_origin_offsets]

    final_training_cutoff_idx = n_weeks - splits_cfg.get("final_training_cutoff_offset", 12)
    final_training_cutoff_date = str(all_weeks[final_training_cutoff_idx - 1])

    # Holdout target weeks: N-11 .. N
    holdout_start_idx = n_weeks - 11
    holdout_target_weeks = [str(all_weeks[i - 1]) for i in range(holdout_start_idx, n_weeks + 1)]

    horizon_weeks = splits_cfg.get("horizon_weeks", 4)

    def get_origin_info(orig_idx: int) -> dict[str, Any]:
        orig_date = all_weeks[orig_idx - 1]
        target_dates = [str(all_weeks[orig_idx - 1 + h]) for h in range(1, horizon_weeks + 1)]
        return {
            "origin_index": orig_idx,
            "origin_week_start": str(orig_date),
            "training_label_cutoff": str(orig_date),
            "target_week_starts": target_dates,
            "horizon_weeks": horizon_weeks,
        }

    validation_folds = [get_origin_info(idx) for idx in val_origins]
    test_folds = [get_origin_info(idx) for idx in test_origins]

    manifest = {
        "total_complete_weeks": n_weeks,
        "first_week_start": str(all_weeks[0]),
        "last_week_start": str(all_weeks[-1]),
        "cohort_skus_count": len(selected_sku_ids),
        "cohort_skus": selected_sku_ids,
        "validation_origins": validation_folds,
        "final_training_cutoff": {
            "cutoff_index": final_training_cutoff_idx,
            "cutoff_date": final_training_cutoff_date,
        },
        "holdout_target_weeks": holdout_target_weeks,
        "test_origins": test_folds,
    }

    split_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(split_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Chronological split manifest written to {split_manifest_path}")
    return manifest
