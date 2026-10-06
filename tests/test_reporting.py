"""Tests for reporting and plotting utilities (Task T17)."""

import json
from pathlib import Path

import pandas as pd

from demandguard.reporting import generate_full_report


def test_generate_full_report(tmp_path, monkeypatch):
    """Verify generate_full_report creates markdown reports and PNG plots."""
    monkeypatch.chdir(tmp_path)
    rep_dir = Path("reports")
    rep_dir.mkdir()
    rows = [
        {
            "model_id": "M1_lgb_deep",
            "wape": 0.3,
            "mae": 7.5,
            "bias": 0.1,
            "total_actual": 100,
            "total_abs_error": 30,
            "count": 4,
        },
        {
            "model_id": "B2",
            "wape": 0.5,
            "mae": 12.5,
            "bias": 0.0,
            "total_actual": 100,
            "total_abs_error": 50,
            "count": 4,
        },
    ]
    pd.DataFrame(rows).to_csv(rep_dir / "forecast_validation.csv", index=False)
    rows[0].update(
        model_id="CHAMPION_M1_lgb_deep", wape=0.4, mae=10, bias=-0.125, total_abs_error=40
    )
    rows[1].update(wape=0.2, mae=5, total_abs_error=20)
    pd.DataFrame(rows).to_csv(rep_dir / "holdout_forecast_metrics.csv", index=False)
    policies = []
    for name, cost, fill in [
        ("P0_Rule", 100, 0.5),
        ("P1_MILP_Baseline", 95, 0.4),
        ("P2_MILP_Champion", 110, 0.5),
    ]:
        policies.append(
            {
                "policy": name,
                "net_realized_cost_scu": cost,
                "fill_rate": fill,
                "total_demand": 100,
                "total_sales": int(fill * 100),
                "total_unmet_units": 100 - int(fill * 100),
                "total_purchase_spend_scu": 20,
                "total_holding_cost_scu": 10,
                "total_unmet_penalty_scu": 75,
                "capacity_breaches": 0,
                "solver_failures": 0,
            }
        )
    pd.DataFrame(policies).to_csv(rep_dir / "holdout_simulation_metrics.csv", index=False)
    artifact_dir = Path("artifacts/champion")
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "selection_record.json").write_text(
        json.dumps(
            {
                "champion_model_id": "M1_lgb_deep",
                "selection_reason": "Synthetic validation choice",
                "selection_validation_wape": 0.3,
                "chosen_safety_stock_k": 1.0,
            }
        )
    )
    res = generate_full_report()
    assert res["status"] == "SUCCESS"

    rep_dir = Path("reports")
    assert (rep_dir / "forecast_comparison_plot.png").exists()
    assert (rep_dir / "inventory_cost_fillrate_plot.png").exists()
    assert (rep_dir / "forecast_comparison.md").exists()
    assert (rep_dir / "inventory_simulation_report.md").exists()
    narrative = (rep_dir / "forecast_comparison.md").read_text()
    assert "0.6200" not in narrative and "0.7107" not in narrative
    assert "50.0% lower error" in narrative
    assert "-12.50%" in narrative
    inventory = (rep_dir / "inventory_simulation_report.md").read_text()
    assert "O5 stretch target is **missed**" in inventory  # cost alone is insufficient
