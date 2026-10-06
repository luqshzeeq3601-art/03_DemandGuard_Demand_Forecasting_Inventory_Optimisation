"""Tests for baseline forecasting methods B1, B2, B3, and B4."""

import numpy as np

from demandguard.baselines import (
    forecast_b1_last_value,
    forecast_b2_trailing_mean,
    forecast_b3_seasonal_naive,
    forecast_b4_arima,
)


def test_baseline_known_predictions():
    """Verify B1, B2, and B3 hand-computed predictions."""
    history = np.array([10, 20, 30, 40, 50], dtype=float)

    # B1: repeat last value (50) for 4 weeks
    b1 = forecast_b1_last_value(history, horizon_weeks=4)
    assert np.allclose(b1, [50, 50, 50, 50])

    # B2: trailing 4 mean of [20, 30, 40, 50] = 35
    b2 = forecast_b2_trailing_mean(history, horizon_weeks=4, window=4)
    assert np.allclose(b2, [35, 35, 35, 35])

    # B3: 60 weeks history with known seasonal indices
    long_history = np.arange(1, 61, dtype=float)
    # c is index 59 (value 60).
    # h=1 -> c+1-52 = 60+1-52 = 9 (value of index 8 is 9)
    # h=2 -> 10, h=3 -> 11, h=4 -> 12
    b3 = forecast_b3_seasonal_naive(long_history, horizon_weeks=4, seasonality=52)
    assert np.allclose(b3, [9, 10, 11, 12])


def test_b4_arima_fallback():
    """Verify ARIMA fallback on invalid / degenerate series."""
    # Degenerate zero-length array should trigger fallback gracefully
    empty_hist = np.array([], dtype=float)
    b4, ok = forecast_b4_arima(empty_hist, horizon_weeks=4)
    assert np.allclose(b4, [0, 0, 0, 0])
