"""Tests for forecast evaluation metrics."""

import pandas as pd

from demandguard.evaluation import calculate_forecast_metrics


def test_calculate_forecast_metrics_known_answers():
    """Verify WAPE, MAE, and Bias on hand-calculated fixtures."""
    df = pd.DataFrame(
        {
            "actual": [10.0, 20.0, 30.0, 0.0],
            "predicted": [12.0, 18.0, 35.0, 5.0],
        }
    )
    # sum(actual) = 60
    # errors: |10-12|=2, |20-18|=2, |30-35|=5, |0-5|=5 -> sum_abs = 14, MAE = 14/4 = 3.5
    # signed errors: +2, -2, +5, +5 -> sum_signed = 10
    # WAPE = 14 / 60 = 0.23333333...
    # Bias = 10 / 60 = 0.16666666...
    res = calculate_forecast_metrics(df)
    assert abs(res["mae"] - 3.5) < 1e-6
    assert abs(res["wape"] - (14.0 / 60.0)) < 1e-6
    assert abs(res["bias"] - (10.0 / 60.0)) < 1e-6
    assert res["count"] == 4


def test_calculate_forecast_metrics_zero_actual():
    """Verify zero actual total returns None for WAPE/Bias without dividing by zero."""
    df = pd.DataFrame(
        {
            "actual": [0.0, 0.0, 0.0],
            "predicted": [2.0, 3.0, 1.0],
        }
    )
    res = calculate_forecast_metrics(df)
    assert res["wape"] is None
    assert res["bias"] is None
    assert abs(res["mae"] - 2.0) < 1e-6
