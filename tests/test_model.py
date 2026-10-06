"""Tests for LightGBM model parameterization, feature transformation, training, prediction, and bundle serialization (Task T10)."""

import numpy as np
import pandas as pd
import pytest

from demandguard.model import DemandGuardModel, NUMERIC_FEATURES, CATEGORICAL_FEATURES


def test_model_init_defaults():
    """Verify default parameters and feature sets."""
    model = DemandGuardModel()
    assert model.params["objective"] == "regression"
    assert model.params["learning_rate"] == 0.05
    assert model.params["num_leaves"] == 31
    assert model.params["n_estimators"] == 80
    assert model.feature_names == NUMERIC_FEATURES + CATEGORICAL_FEATURES


def test_model_fit_and_predict(tmp_path):
    """Verify model training, non-negative prediction clipping, and bundle roundtrip."""
    # Create synthetic feature training data
    n_samples = 100
    cohort = ["SKU_01", "SKU_02"]
    
    rows = []
    for i in range(n_samples):
        row = {
            "sku_id": cohort[i % 2],
            "origin_week_start": "2011-01-03",
            "target_week_start": "2011-01-10",
            "horizon": (i % 4) + 1,
            "target_units": float(20 + 5 * (i % 4) + np.random.normal(0, 2)),
        }
        for f in NUMERIC_FEATURES:
            if f not in row:
                row[f] = float(np.random.uniform(10, 50))
        rows.append(row)
        
    train_df = pd.DataFrame(rows)
    
    model = DemandGuardModel(
        params={"objective": "regression", "n_estimators": 20, "learning_rate": 0.1, "verbose": -1},
        sku_categories=cohort,
    )
    
    # Train
    model.fit(train_df)
    assert model.booster is not None
    
    # Predict
    test_df = train_df.drop(columns=["target_units"]).head(10).copy()
    preds = model.predict(test_df)
    assert len(preds) == 10
    assert (preds >= 0.0).all()
    
    # Bundle save and load
    art_dir = tmp_path / "model_bundle"
    metadata = {
        "champion_model_id": "M1_test",
        "selection_validation_wape": 0.55,
        "cohort_skus": cohort,
    }
    model.save_bundle(art_dir, metadata=metadata)
    
    assert (art_dir / "model.txt").exists()
    assert (art_dir / "metadata.json").exists()
    
    loaded_model, loaded_meta = DemandGuardModel.load_bundle(art_dir)
    assert loaded_meta["champion_model_id"] == "M1_test"
    loaded_preds = loaded_model.predict(test_df)
    assert np.allclose(preds, loaded_preds)
