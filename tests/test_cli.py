"""Tests for DemandGuard CLI interface and demo workflows (Task T13)."""

import pandas as pd

from demandguard.cli import run_forecast_command, run_reorder_command


def test_cli_forecast_and_reorder_synthetic_demo(tmp_path):
    """Verify forecast and reorder CLI entry points run end to end on synthetic fixtures."""
    history_file = "tests/fixtures/demo_history.csv"
    scenario_file = "tests/fixtures/demo_scenario.yaml"
    fc_out = tmp_path / "forecast.csv"
    reorder_out = tmp_path / "reorder.csv"

    # 1. Forecast CLI
    ret_fc = run_forecast_command(history_file, str(fc_out))
    assert ret_fc == 0
    assert fc_out.exists()

    df_fc = pd.read_csv(fc_out)
    assert len(df_fc) == 8  # 2 products * 4 weeks
    assert "predicted_units" in df_fc.columns
    assert (df_fc["predicted_units"] >= 0).all()

    # 2. Reorder CLI
    ret_reord = run_reorder_command(history_file, scenario_file, str(reorder_out))
    assert ret_reord == 0
    assert reorder_out.exists()

    df_reord = pd.read_csv(reorder_out)
    assert len(df_reord) == 2
    assert "order_q1" in df_reord.columns
    assert (df_reord["order_q1"] >= 0).all()
    # Check spend
    assert (df_reord["spend_week_1_scu"] >= 0).all()
