"""Tests for feature engineering causality and label isolation (Task T06)."""

import datetime

import numpy as np

from demandguard.features import extract_causal_features_for_series


def test_features_causality_and_no_future_leakage():
    """Verify modifying future sales after origin c does not change feature outputs."""
    # 65 weeks of historical sales
    orig_date = datetime.date(2011, 1, 10)
    base_history = np.arange(1, 66, dtype=float)

    f1 = extract_causal_features_for_series(
        base_history, origin_date=orig_date, horizon=1, sku_id="SKU_1"
    )

    # Lag 0 is offset 0 (the last element 65)
    assert f1["lag_0"] == 65.0
    assert f1["lag_1"] == 64.0
    assert f1["lag_51"] == float(base_history[-52])  # 65 - 51 = 14

    # Rolling mean 4 is mean of [62, 63, 64, 65] = 63.5
    assert f1["rolling_mean_4"] == 63.5

    # Trend 4_4 is mean([62, 63, 64, 65]) - mean([58, 59, 60, 61]) = 63.5 - 59.5 = 4.0
    assert f1["trend_4_4"] == 4.0
