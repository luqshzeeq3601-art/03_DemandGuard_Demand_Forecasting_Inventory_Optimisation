"""Tests for reporting and plotting utilities (Task T17)."""

from pathlib import Path

from demandguard.reporting import generate_full_report


def test_generate_full_report():
    """Verify generate_full_report creates markdown reports and PNG plots."""
    res = generate_full_report()
    assert res["status"] == "SUCCESS"

    rep_dir = Path("reports")
    assert (rep_dir / "forecast_comparison_plot.png").exists()
    assert (rep_dir / "inventory_cost_fillrate_plot.png").exists()
    assert (rep_dir / "forecast_comparison.md").exists()
    assert (rep_dir / "inventory_simulation_report.md").exists()
