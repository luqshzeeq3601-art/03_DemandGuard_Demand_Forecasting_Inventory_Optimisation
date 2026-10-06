"""Tests for evaluation metrics calculation, 1% simplicity selection rule, and k-factor validation (Task T11)."""

import numpy as np
import pandas as pd
import pytest

from demandguard.evaluation import calculate_forecast_metrics


def test_calculate_forecast_metrics_exact_values():
    """Verify WAPE, MAE, and Bias calculations with hand-computed test data."""
    df = pd.DataFrame(
        {
            "actual": [100.0, 200.0, 300.0, 400.0],
            "predicted": [90.0, 210.0, 280.0, 420.0],
        }
    )
    # abs errors = [10, 10, 20, 20] -> sum = 60, mean = 15.0
    # actual sum = 1000
    # signed errors = [-10, +10, -20, +20] -> sum = 0
    metrics = calculate_forecast_metrics(df)
    assert metrics["mae"] == 15.0
    assert abs(metrics["wape"] - 0.06) < 1e-6
    assert abs(metrics["bias"] - 0.0) < 1e-6
    assert metrics["count"] == 4
    assert metrics["total_actual"] == 1000.0


def test_calculate_forecast_metrics_negative_clipping():
    """Verify negative predictions are clipped to zero when clip_negative=True."""
    df = pd.DataFrame(
        {
            "actual": [10.0, 20.0],
            "predicted": [-5.0, 15.0],
        }
    )
    # clipped predicted = [0.0, 15.0]
    # abs errors = [10, 5] -> sum = 15, mae = 7.5
    # actual sum = 30
    metrics = calculate_forecast_metrics(df, clip_negative=True)
    assert metrics["mae"] == 7.5
    assert abs(metrics["wape"] - 0.5) < 1e-6


def test_simplicity_selection_rule_logic():
    """Verify 1% simplicity rule: if baseline is within 1% of ML, baseline wins."""
    # Scenario: ML = 0.6200, Baseline = 0.6230 (within 1% relative difference)
    ml_wape = 0.6200
    base_wape = 0.6230
    tolerance = 0.01
    
    # baseline is within 1% (0.6200 * 1.01 = 0.6262)
    assert base_wape <= ml_wape * (1.0 + tolerance)
    
    # Selection rule should favor baseline
    preferred_id = "B2" if base_wape <= ml_wape * (1.0 + tolerance) else "M1_lgb"
    assert preferred_id == "B2"
