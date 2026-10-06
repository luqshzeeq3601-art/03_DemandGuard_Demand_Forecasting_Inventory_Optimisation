"""LightGBM pooled forecasting model training, inference, and bundle serialization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

NUMERIC_FEATURES = [
    "lag_0",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_12",
    "lag_25",
    "lag_51",
    "rolling_mean_4",
    "rolling_std_4",
    "zero_fraction_4",
    "rolling_mean_13",
    "rolling_std_13",
    "zero_fraction_13",
    "rolling_mean_26",
    "rolling_std_26",
    "zero_fraction_26",
    "trend_4_4",
    "origin_week_of_year",
    "origin_month",
    "target_week_of_year",
    "target_month",
    "horizon",
]

CATEGORICAL_FEATURES = ["sku_id"]


class DemandGuardModel:
    """Wrapper for pooled direct-horizon LightGBM model."""

    def __init__(
        self,
        params: dict[str, Any] | None = None,
        sku_categories: list[str] | None = None,
        feature_names: list[str] | None = None,
    ):
        self.params = params or {
            "objective": "regression",
            "metric": "l2",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_child_samples": 10,
            "n_estimators": 80,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        self.sku_categories = sku_categories or []
        self.feature_names = feature_names or (NUMERIC_FEATURES + CATEGORICAL_FEATURES)
        self.booster: lgb.Booster | None = None

    def prepare_x_y(
        self, df: pd.DataFrame, is_training: bool = True
    ) -> tuple[pd.DataFrame, np.ndarray | None]:
        """Format features and categorical variables consistently."""
        df = df.copy()

        # Set categorical type for sku_id according to known category vocabulary
        if self.sku_categories:
            df["sku_id"] = pd.Categorical(df["sku_id"], categories=self.sku_categories)
        else:
            self.sku_categories = sorted(df["sku_id"].unique())
            df["sku_id"] = pd.Categorical(df["sku_id"], categories=self.sku_categories)

        X = df[self.feature_names].copy()
        y = None
        if is_training:
            if "target_units" not in df:
                raise ValueError("Column 'target_units' is required for training.")
            y = df["target_units"].to_numpy(dtype=float)

        return X, y

    def fit(self, train_df: pd.DataFrame) -> DemandGuardModel:
        """Fit LightGBM model on training dataframe."""
        X, y = self.prepare_x_y(train_df, is_training=True)

        dtrain = lgb.Dataset(
            X,
            label=y,
            categorical_feature=CATEGORICAL_FEATURES,
            free_raw_data=False,
        )
        lgb_params = {k: v for k, v in self.params.items() if k != "n_estimators"}
        num_boost_round = self.params.get("n_estimators", 80)

        self.booster = lgb.train(
            params=lgb_params,
            train_set=dtrain,
            num_boost_round=num_boost_round,
        )
        return self

    def predict(self, feature_df: pd.DataFrame, clip_negative: bool = True) -> np.ndarray:
        """Generate point forecasts."""
        if self.booster is None:
            raise RuntimeError("Model has not been fitted or loaded.")

        X, _ = self.prepare_x_y(feature_df, is_training=False)
        preds = self.booster.predict(X)

        if clip_negative:
            preds = np.maximum(0.0, preds)

        return np.asarray(preds, dtype=float)

    def save_bundle(self, artifact_dir: str | Path, metadata: dict[str, Any]) -> Path:
        """Save booster and metadata bundle into artifact directory."""
        art_path = Path(artifact_dir)
        art_path.mkdir(parents=True, exist_ok=True)

        if self.booster is None:
            raise RuntimeError("Cannot save unfitted model.")

        model_file = art_path / "model.txt"
        self.booster.save_model(str(model_file))

        meta_full = {
            "model_type": "LightGBM_Pooled_Direct",
            "model_file": "model.txt",
            "feature_names": self.feature_names,
            "categorical_features": CATEGORICAL_FEATURES,
            "sku_categories": self.sku_categories,
            "params": self.params,
        }
        meta_full.update(metadata)

        meta_file = art_path / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_full, f, indent=2)

        print(f"Model artifact bundle saved to {art_path}")
        return art_path

    @classmethod
    def load_bundle(cls, artifact_dir: str | Path) -> tuple[DemandGuardModel, dict[str, Any]]:
        """Load model bundle and metadata from trusted artifact directory."""
        art_path = Path(artifact_dir)
        meta_file = art_path / "metadata.json"
        model_file = art_path / "model.txt"

        if not meta_file.exists() or not model_file.exists():
            raise FileNotFoundError(f"Missing artifact bundle files in {art_path}")

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        instance = cls(
            params=metadata.get("params"),
            sku_categories=metadata.get("sku_categories"),
            feature_names=metadata.get("feature_names"),
        )
        instance.booster = lgb.Booster(model_file=str(model_file))
        return instance, metadata
