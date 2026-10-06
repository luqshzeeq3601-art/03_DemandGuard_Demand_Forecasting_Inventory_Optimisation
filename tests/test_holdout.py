"""Tests for test holdout evaluation, frozen artifact access protection, and simulation integrity (Task T12)."""

from pathlib import Path

import pytest

from demandguard.evaluation import run_holdout_evaluation


def test_holdout_access_requires_selection_record(tmp_path, monkeypatch):
    """Verify holdout evaluation fails if no frozen selection record exists."""
    non_existent = tmp_path / "non_existent_selection.json"

    # Temporarily monkeypatch the path check
    monkeypatch.setattr(
        "demandguard.evaluation.Path",
        lambda p: non_existent if "selection_record.json" in str(p) else Path(p),
    )

    with pytest.raises(RuntimeError, match="Selection record not found"):
        run_holdout_evaluation(
            config_path="config/project.yaml",
            scenario_path="config/scenario.yaml",
        )


@pytest.mark.skipif(
    not Path("data/processed/weekly_sales.parquet").exists(),
    reason="Needs the locally prepared panel (gitignored); run acquire/prepare/split first.",
)
def test_holdout_evaluation_structure():
    """Verify run_holdout_evaluation returns valid metrics structure on frozen artifacts."""
    res = run_holdout_evaluation(
        config_path="config/project.yaml",
        scenario_path="config/scenario.yaml",
    )
    assert "holdout_metrics" in res
    metrics = res["holdout_metrics"]
    assert len(metrics) > 0
    # Must contain B2 and CHAMPION
    model_ids = [m["model_id"] for m in metrics]
    assert any("B2" in m for m in model_ids)
    assert any("CHAMPION" in m for m in model_ids)
