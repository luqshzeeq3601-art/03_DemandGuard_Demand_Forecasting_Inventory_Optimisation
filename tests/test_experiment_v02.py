"""Selection-rule tests for the v0.2 experiment (decision D18)."""

import pandas as pd

from demandguard.experiment_v02 import V01_FEATURES, V02_FEATURES, select_v02_champion


def _metrics(rows):
    return pd.DataFrame(rows, columns=["model_id", "wape"]).sort_values("wape")


def test_lowest_wape_wins_outside_tolerance():
    df = _metrics([("M2_q50", 0.59), ("M2_l2", 0.62), ("B2", 0.67)])
    champion, reason = select_v02_champion(df, tolerance=0.01)
    assert champion == "M2_q50"
    assert "Lowest" in reason


def test_simpler_candidate_within_tolerance_wins():
    df = _metrics([("H_blend", 0.6000), ("M2_l2", 0.6040), ("B2", 0.6055)])
    champion, reason = select_v02_champion(df, tolerance=0.01)
    assert champion == "B2"
    assert "Simplicity rule" in reason


def test_v01_feature_set_excludes_v02_additions():
    assert "lag_52" not in V01_FEATURES
    assert "sin_woy_tgt" not in V01_FEATURES
    assert set(V01_FEATURES) < set(V02_FEATURES)
