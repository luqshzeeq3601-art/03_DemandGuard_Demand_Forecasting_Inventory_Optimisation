"""Tests for cohort selection and chronological splitting (Task T04 / Gate G1)."""

import json

import pandas as pd
import yaml

from demandguard.splits import (
    build_cohort_and_splits,
    generate_pre_holdout_validation_origins,
)


def test_cohort_and_split_contract(tmp_path):
    """Verify cohort selection ignores future sales and produces exact disjoint origins."""
    panel_path = tmp_path / "weekly_sales.parquet"
    cohort_path = tmp_path / "cohort.json"
    manifest_path = tmp_path / "split_manifest.json"

    # Create synthetic panel of 105 weeks for 12 SKUs
    # 2009-11-30 is Monday
    start_monday = pd.to_datetime("2009-11-30")
    weeks = [(start_monday + pd.Timedelta(weeks=i)).date() for i in range(105)]

    records = []
    for s in range(12):
        sku = f"SKU_{s:02d}"
        for w_idx, w in enumerate(weeks):
            # In first 60 weeks: SKU_00 to SKU_09 have positive sales in all weeks,
            # SKU_10 has sales only in week 0, SKU_11 has sales in 20 weeks
            if s < 10:
                qty = (s + 1) * 10
            elif s == 10:
                qty = 100 if w_idx == 0 else 0
            else:
                qty = 50 if w_idx < 20 else 0

            # Inject huge future sales in weeks 70..105 for SKU_10 to verify it cannot be rescued
            if w_idx > 70 and s == 10:
                qty = 10000

            records.append({"sku_id": sku, "week_start": w, "units_sold": qty})

    df = pd.DataFrame(records)
    df.to_parquet(panel_path)

    cfg = {
        "data": {
            "weekly_sales_path": str(panel_path),
            "cohort_path": str(cohort_path),
            "split_manifest_path": str(manifest_path),
        },
        "cohort": {
            "prefix_weeks": 60,
            "min_active_prefix_weeks": 40,
            "first_active_window_weeks": 8,
            "max_products": 30,
            "min_products": 10,
            "min_total_weeks": 100,
        },
        "splits": {
            "horizon_weeks": 4,
            "validation_origins_offset": [28, 24, 20, 16],
            "test_origins_offset": [12, 8, 4],
            "final_training_cutoff_offset": 12,
            "holdout_target_weeks": 12,
        },
    }
    cfg_file = tmp_path / "project.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f)

    manifest = build_cohort_and_splits(str(cfg_file))

    # SKU_10 must NOT be in cohort despite huge future sales
    with open(cohort_path, "r", encoding="utf-8") as f:
        cohort_json = json.load(f)
    cohort_skus = [c["sku_id"] for c in cohort_json["cohort"]]
    assert "SKU_10" not in cohort_skus
    assert len(cohort_skus) == 10  # SKU_00 to SKU_09

    # Check split origins
    assert manifest["total_complete_weeks"] == 105
    # Validation origins: 105-28=77, 105-24=81, 105-20=85, 105-16=89
    val_indices = [v["origin_index"] for v in manifest["validation_origins"]]
    assert val_indices == [77, 81, 85, 89]

    # Test origins: 105-12=93, 105-8=97, 105-4=101
    test_indices = [t["origin_index"] for t in manifest["test_origins"]]
    assert test_indices == [93, 97, 101]

    # Holdout target weeks: 105-11 (94) to 105 (12 weeks)
    assert len(manifest["holdout_target_weeks"]) == 12

    # Verify zero-filling in weekly_sales.parquet
    updated_panel = pd.read_parquet(panel_path)
    assert len(updated_panel) == 10 * 105  # 10 SKUs * 105 weeks


def test_pre_holdout_validation_origins_never_touch_holdout():
    """Rolling validation targets must end before the holdout and keep 60 history weeks."""
    import datetime

    import pytest

    weeks = [datetime.date(2009, 12, 7) + datetime.timedelta(weeks=i) for i in range(102)]
    holdout_start_index = 102 - 11  # manifest holdout: N-11 .. N
    folds = generate_pre_holdout_validation_origins(weeks, holdout_start_index)

    assert len(folds) == 4
    assert folds[0]["origin_index"] >= 60
    for fold in folds:
        last_target = datetime.date.fromisoformat(fold["target_week_starts"][-1])
        assert last_target < weeks[holdout_start_index - 1]
    assert folds[-1]["origin_index"] + 4 == holdout_start_index - 1

    with pytest.raises(ValueError):
        generate_pre_holdout_validation_origins(weeks[:63], holdout_start_index=63)
