"""v0.2 experiment: pre-holdout selection of declared candidates, then exploratory test scoring.

Protocol: docs/05_FORECAST_EXPERIMENT_PLAN.md section 9 and decision D18. Every number produced
on the test window is EXPLORATORY because that window was already viewed in v0.1.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml

from demandguard.contracts import ProductInventoryInput
from demandguard.evaluation import calculate_forecast_metrics
from demandguard.features import (
    build_feature_table,
    compute_recency_weights,
    extract_causal_features_for_series,
)
from demandguard.inventory import solve_inventory_milp, solve_stochastic_inventory_milp
from demandguard.model import NUMERIC_FEATURES, DemandGuardModel, DemandGuardProbabilisticModel
from demandguard.policies import (
    compute_p0_order_quantities,
    compute_quantile_spread_safety_stock,
)
from demandguard.simulation import (
    ProductInventoryState,
    compute_simulation_summary,
    step_product_inventory,
)

V02_ONLY_FEATURES = [
    "lag_52",
    "rolling_mean_52",
    "momentum_4_13",
    "sin_woy_orig",
    "cos_woy_orig",
    "sin_woy_tgt",
    "cos_woy_tgt",
]
V01_FEATURES = [f for f in NUMERIC_FEATURES if f not in V02_ONLY_FEATURES] + ["sku_id"]
V02_FEATURES = NUMERIC_FEATURES + ["sku_id"]

TREE_PARAMS = {
    "learning_rate": 0.08,
    "num_leaves": 15,
    "n_estimators": 60,
    "min_child_samples": 10,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}
RECENCY_DECAY = 0.98
BLEND_ML_WEIGHT = 0.5
QUANTILE_WEIGHTS = {"p10": 0.25, "p50": 0.50, "p90": 0.25}

# Simplest first; a candidate within the tolerance of the best wins if it appears earlier.
SIMPLICITY_ORDER = ["B2", "M1_v01_fast", "M2_l2", "M2_tweedie", "M2_q50", "H_blend"]

EXPLORATORY_LABEL = "EXPLORATORY: test window was viewed in v0.1 (decision D18)"


def _code_revision() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout.strip()
        return out.stdout.strip() + ("+uncommitted" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _fit_point_models(train_df: pd.DataFrame, cohort_skus: list[str]) -> dict[str, Any]:
    """Fit every declared model candidate on one training prefix."""
    weights = compute_recency_weights(train_df["origin_week_start"], decay_rate=RECENCY_DECAY)
    l2 = {"objective": "regression", "metric": "l2", **TREE_PARAMS}
    tweedie = {"objective": "tweedie", "tweedie_variance_power": 1.2, **TREE_PARAMS}

    models: dict[str, Any] = {
        "M1_v01_fast": DemandGuardModel(
            params=l2, sku_categories=cohort_skus, feature_names=V01_FEATURES
        ).fit(train_df),
        "M2_l2": DemandGuardModel(
            params=l2, sku_categories=cohort_skus, feature_names=V02_FEATURES
        ).fit(train_df, sample_weight=weights),
        "M2_tweedie": DemandGuardModel(
            params=tweedie, sku_categories=cohort_skus, feature_names=V02_FEATURES
        ).fit(train_df, sample_weight=weights),
    }
    quantile = DemandGuardProbabilisticModel(base_params=dict(TREE_PARAMS))
    for q in quantile.quantiles:
        params = {**TREE_PARAMS, "objective": "quantile", "alpha": q}
        quantile.models[f"p{int(q * 100)}"] = DemandGuardModel(
            params=params, sku_categories=cohort_skus, feature_names=V02_FEATURES
        ).fit(train_df, sample_weight=weights)
    models["M2_quantile"] = quantile
    return models


def _predict_candidates(
    models: dict[str, Any], feat_df: pd.DataFrame, b2: np.ndarray
) -> dict[str, np.ndarray]:
    preds = {
        "B2": b2,
        "M1_v01_fast": models["M1_v01_fast"].predict(feat_df),
        "M2_l2": models["M2_l2"].predict(feat_df),
        "M2_tweedie": models["M2_tweedie"].predict(feat_df),
        "M2_q50": models["M2_quantile"].predict_quantiles(feat_df)["p50"],
    }
    preds["H_blend"] = np.maximum(
        0.0, BLEND_ML_WEIGHT * preds["M2_l2"] + (1.0 - BLEND_ML_WEIGHT) * b2
    )
    return preds


def _b2_for_rows(feat_df: pd.DataFrame) -> np.ndarray:
    """B2 repeats the trailing four-week mean at the origin for every horizon."""
    return feat_df["rolling_mean_4"].to_numpy(dtype=float)


def _score_origins(
    feat_df: pd.DataFrame,
    origins: list[dict[str, Any]],
    train_cutoff_for: Callable[[dict[str, Any]], str],
    cohort_skus: list[str],
    split: str,
) -> pd.DataFrame:
    rows = []
    fitted_cache: dict[str, dict[str, Any]] = {}
    for fold_idx, origin in enumerate(origins, start=1):
        cutoff = train_cutoff_for(origin)
        if cutoff not in fitted_cache:
            train_df = feat_df[
                (feat_df["target_week_start"] <= cutoff) & feat_df["target_units"].notna()
            ]
            if train_df.empty:
                raise RuntimeError(f"Empty training set for cutoff {cutoff}.")
            fitted_cache[cutoff] = _fit_point_models(train_df, cohort_skus)
        test_df = feat_df[feat_df["origin_week_start"] == origin["origin_week_start"]].copy()
        test_df = test_df.reset_index(drop=True)
        preds = _predict_candidates(fitted_cache[cutoff], test_df, _b2_for_rows(test_df))
        for model_id, values in preds.items():
            for i, r in test_df.iterrows():
                rows.append(
                    {
                        "split": split,
                        "fold": fold_idx,
                        "model_id": model_id,
                        "sku_id": r["sku_id"],
                        "origin_week_start": r["origin_week_start"],
                        "target_week_start": r["target_week_start"],
                        "horizon": int(r["horizon"]),
                        "actual": float(r["target_units"]),
                        "predicted": float(values[i]),
                    }
                )
    return pd.DataFrame(rows)


def _metrics_table(preds_df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for model_id, group in preds_df.groupby("model_id"):
        m = calculate_forecast_metrics(group)
        out.append({"model_id": model_id, **{k: m[k] for k in ("wape", "mae", "bias", "count")}})
    return pd.DataFrame(out).sort_values("wape").reset_index(drop=True)


def select_v02_champion(val_metrics: pd.DataFrame, tolerance: float) -> tuple[str, str]:
    """Lowest WAPE; the simplest candidate within `tolerance` relative WAPE of it wins."""
    best = val_metrics.iloc[0]
    limit = float(best["wape"]) * (1.0 + tolerance)
    eligible = set(val_metrics.loc[val_metrics["wape"] <= limit, "model_id"])
    champion = next(m for m in SIMPLICITY_ORDER if m in eligible)
    if champion == best["model_id"]:
        reason = f"Lowest pooled validation WAPE ({best['wape']:.4f})."
    else:
        reason = (
            f"Simplicity rule: {champion} is within {tolerance:.0%} of best "
            f"{best['model_id']} ({best['wape']:.4f})."
        )
    return champion, reason


def _run_exploratory_simulation(
    panel_df: pd.DataFrame,
    cohort_skus: list[str],
    holdout_weeks: list[str],
    scen: dict[str, Any],
    champion_id: str,
    models: dict[str, Any],
    k_val: float,
) -> pd.DataFrame:
    """12-week continuous simulation: P0 rule, P1 B2+MILP, P3 champion+MILP, P4 stochastic."""
    panel_dict = panel_df.set_index(["sku_id", "week_start"])["units_sold"].to_dict()
    all_weeks = sorted(panel_df["week_start"].unique())
    holdout_start = pd.to_datetime(holdout_weeks[0]).date()
    warmup_13 = [w for w in all_weeks if w < holdout_start][-13:]

    means_13 = {
        s: float(np.mean([panel_dict.get((s, w), 0) for w in warmup_13])) for s in cohort_skus
    }
    stds_13 = {
        s: float(np.std([panel_dict.get((s, w), 0) for w in warmup_13], ddof=1))
        for s in cohort_skus
    }
    unit_cost = scen.get("purchase_cost_scu", 1.0)
    weekly_budget = float(np.ceil(sum(means_13.values()) * unit_cost))
    capacity = int(
        max(sum(np.ceil(2.0 * m) for m in means_13.values()), np.ceil(3.0 * sum(means_13.values())))
    )
    safety = {s: float(np.ceil(k_val * stds_13[s])) for s in cohort_skus}

    def init_states() -> dict[str, ProductInventoryState]:
        return {
            s: ProductInventoryState(
                sku_id=s,
                on_hand_units=int(np.ceil(2.0 * means_13[s])),
                incoming_week_1_units=0,
                unit_purchase_cost_scu=unit_cost,
                holding_cost_scu_per_unit_week=scen.get("holding_cost_scu_per_unit_week", 0.02),
                unmet_penalty_scu_per_unit=scen.get("unmet_penalty_scu_per_unit", 5.0),
                storage_slots_per_unit=scen.get("storage_slots_per_unit", 1.0),
            )
            for s in cohort_skus
        }

    p5 = "P5_MILP_q50_QuantileSafety"
    policies = [
        "P0_Rule",
        "P1_MILP_B2",
        f"P3_MILP_{champion_id}",
        "P4_Stochastic_Quantile",
        p5,
    ]
    states = {p: init_states() for p in policies}
    steps: dict[str, list[Any]] = {p: [] for p in policies}
    solver_failures = {p: 0 for p in policies}
    # Solves stopped by the time limit are not executable and place zero orders (D22/D23).
    time_limited = {p: 0 for p in policies}
    series = {
        s: np.array([panel_dict.get((s, w), 0) for w in all_weeks], dtype=float)
        for s in cohort_skus
    }

    for week_str in holdout_weeks:
        week = pd.to_datetime(week_str).date()
        prior = week - datetime.timedelta(weeks=1)
        n_hist = sum(1 for w in all_weeks if w <= prior)

        feat_rows = [
            extract_causal_features_for_series(series[s][:n_hist], prior, h, s)
            for s in cohort_skus
            for h in range(1, 5)
        ]
        feat_df = pd.DataFrame(feat_rows)
        b2 = _b2_for_rows(feat_df)
        point = _predict_candidates(models, feat_df, b2)
        quant = models["M2_quantile"].predict_quantiles(feat_df)

        def matrix(values: np.ndarray) -> dict[str, list[float]]:
            out: dict[str, list[float]] = {s: [] for s in cohort_skus}
            for i, s in enumerate(feat_df["sku_id"]):
                out[s].append(float(values[i]))
            return out

        trailing_4 = {s: float(np.mean(series[s][:n_hist][-4:])) for s in cohort_skus}

        # P5: safety stock from the week-1 P10-P90 spread, z equal to k (decision D24).
        q_safety = {
            s: compute_quantile_spread_safety_stock(
                float(quant["p10"][i]), float(quant["p90"][i]), service_level_z=k_val
            )
            for i, s in enumerate(feat_df["sku_id"])
            if int(feat_df["horizon"].iloc[i]) == 1
        }

        def products_for(
            policy: str, safety_units: dict[str, float] | None = None
        ) -> list[ProductInventoryInput]:
            safety_units = safety_units or safety
            return [
                ProductInventoryInput(
                    sku_id=s,
                    on_hand_units=states[policy][s].on_hand_units,
                    incoming_week_1_units=states[policy][s].incoming_week_1_units,
                    safety_stock_target_units=safety_units[s],
                )
                for s in cohort_skus
            ]

        orders: dict[str, dict[str, int]] = {}
        orders["P0_Rule"] = compute_p0_order_quantities(
            current_states={
                s: {
                    "on_hand_units": states["P0_Rule"][s].on_hand_units,
                    "incoming_week_1_units": states["P0_Rule"][s].incoming_week_1_units,
                }
                for s in cohort_skus
            },
            trailing_4_means=trailing_4,
            safety_stocks=safety,
            weekly_budget_scu=weekly_budget,
            warehouse_capacity_slots=capacity,
        )
        for policy, fc, safety_units in (
            ("P1_MILP_B2", b2, safety),
            (f"P3_MILP_{champion_id}", point[champion_id], safety),
            (p5, quant["p50"], q_safety),
        ):
            meta, solved, _ = solve_inventory_milp(
                products=products_for(policy, safety_units),
                forecast_matrix=matrix(fc),
                weekly_budgets_scu=[weekly_budget] * 4,
                warehouse_capacity_slots=capacity,
            )
            if meta.get("status") != "Optimal" or not solved:
                solver_failures[policy] += 1
            if meta.get("status") == "TimeLimitFeasible":
                time_limited[policy] += 1
            orders[policy] = {s: solved.get(s, [0])[0] for s in cohort_skus}

        q_fc = {s: {q: [] for q in QUANTILE_WEIGHTS} for s in cohort_skus}
        for q in QUANTILE_WEIGHTS:
            for s, vals in matrix(quant[q]).items():
                q_fc[s][q] = vals
        meta, solved, _ = solve_stochastic_inventory_milp(
            products=products_for("P4_Stochastic_Quantile"),
            forecast_quantiles=q_fc,
            weekly_budgets_scu=[weekly_budget] * 4,
            warehouse_capacity_slots=capacity,
            scenario_weights=QUANTILE_WEIGHTS,
        )
        if meta.get("status") != "Optimal" or not solved:
            solver_failures["P4_Stochastic_Quantile"] += 1
        if meta.get("status") == "TimeLimitFeasible":
            time_limited["P4_Stochastic_Quantile"] += 1
        orders["P4_Stochastic_Quantile"] = {s: solved.get(s, [0])[0] for s in cohort_skus}

        for policy in policies:
            for s in cohort_skus:
                new_state, result = step_product_inventory(
                    state=states[policy][s],
                    placed_order_q1=int(orders[policy][s]),
                    realized_demand=int(panel_dict.get((s, week), 0)),
                    week_start=week_str,
                    warehouse_capacity_slots=capacity,
                )
                states[policy][s] = new_state
                steps[policy].append(result)

    rows = []
    for policy in policies:
        summary = compute_simulation_summary(
            step_results=steps[policy], final_states=states[policy]
        )
        rows.append(
            {
                "policy": policy,
                **summary,
                "solver_failures": solver_failures[policy],
                "time_limited_solves": time_limited[policy],
            }
        )
    df = pd.DataFrame(rows)
    p0_cost = float(df.loc[df["policy"] == "P0_Rule", "net_realized_cost_scu"].iloc[0])
    df["cost_change_vs_p0"] = (df["net_realized_cost_scu"] - p0_cost) / p0_cost
    df["weekly_budget_scu"] = weekly_budget
    df["capacity_slots"] = capacity
    return df


def run_v02_experiment(
    config_path: str = "config/project.yaml",
    scenario_path: str = "config/scenario.yaml",
    artifact_dir: str = "artifacts/v02",
    report_dir: str = "reports",
) -> dict[str, Any]:
    """Run the D18 protocol end to end and write reports."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(scenario_path, "r", encoding="utf-8") as f:
        scen = yaml.safe_load(f)["scenario"]
    with open(cfg["data"]["split_manifest_path"], "r", encoding="utf-8") as f:
        manifest = json.load(f)

    cohort_skus = manifest["cohort_skus"]
    holdout_weeks = manifest["holdout_target_weeks"]
    cutoff = manifest["final_training_cutoff"]["cutoff_date"]
    for origin in manifest["validation_origins"]:
        if max(origin["target_week_starts"]) >= holdout_weeks[0]:
            raise RuntimeError("Validation origin targets overlap the holdout window.")

    panel_df = pd.read_parquet(cfg["data"]["weekly_sales_path"])
    panel_df["week_start"] = pd.to_datetime(panel_df["week_start"]).dt.date
    print("Building v0.2 feature table...")
    feat_df = build_feature_table(panel_df, cohort_skus=cohort_skus)

    # 1. Validation on pre-holdout origins only.
    print("Validating declared candidates on pre-holdout origins...")
    val_preds = _score_origins(
        feat_df,
        manifest["validation_origins"],
        lambda o: o["training_label_cutoff"],
        cohort_skus,
        split="validation",
    )
    val_metrics = _metrics_table(val_preds)
    tolerance = float(cfg["forecast"].get("simplicity_tolerance", 0.01))
    champion_id, reason = select_v02_champion(val_metrics, tolerance)
    b2_val_wape = float(val_metrics.loc[val_metrics["model_id"] == "B2", "wape"].iloc[0])
    champ_val_wape = float(val_metrics.loc[val_metrics["model_id"] == champion_id, "wape"].iloc[0])

    rep = Path(report_dir)
    rep.mkdir(parents=True, exist_ok=True)
    val_metrics.to_csv(rep / "v02_validation.csv", index=False)

    # 2. Freeze selection before any test-window scoring.
    art = Path(artifact_dir)
    art.mkdir(parents=True, exist_ok=True)
    k_val = float(scen.get("default_safety_stock_k", 1.0))
    record = {
        "protocol": "D18",
        "candidates": SIMPLICITY_ORDER,
        "champion_model_id": champion_id,
        "selection_reason": reason,
        "validation_wape": champ_val_wape,
        "b2_validation_wape": b2_val_wape,
        "relative_wape_reduction_vs_b2": (b2_val_wape - champ_val_wape) / b2_val_wape,
        "simplicity_tolerance": tolerance,
        "tree_params": TREE_PARAMS,
        "recency_decay": RECENCY_DECAY,
        "blend_ml_weight": BLEND_ML_WEIGHT,
        "safety_stock_k": k_val,
        "final_training_cutoff_date": cutoff,
        "code_revision": _code_revision(),
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(art / "selection_record.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"[*] Frozen v0.2 champion: {champion_id} ({reason})")

    # 3. Fit frozen candidates through c0 and save the champion bundle when it is a model.
    train_c0 = feat_df[(feat_df["target_week_start"] <= cutoff) & feat_df["target_units"].notna()]
    c0_models = _fit_point_models(train_c0, cohort_skus)
    # Servable point model: H_blend serves its ML part; M2_q50 serves the P50 quantile model.
    bundles = {
        "M1_v01_fast": c0_models["M1_v01_fast"],
        "M2_l2": c0_models["M2_l2"],
        "M2_tweedie": c0_models["M2_tweedie"],
        "M2_q50": c0_models["M2_quantile"].models["p50"],
        "H_blend": c0_models["M2_l2"],
    }
    if champion_id in bundles:
        bundles[champion_id].save_bundle(art, metadata={**record, "served_component": champion_id})

    # 4. EXPLORATORY test-window forecast scoring.
    print("Scoring test window (EXPLORATORY)...")
    test_preds = _score_origins(
        feat_df, manifest["test_origins"], lambda o: cutoff, cohort_skus, split="test"
    )
    test_metrics = _metrics_table(test_preds)
    test_metrics.insert(0, "label", EXPLORATORY_LABEL)
    test_metrics.to_csv(rep / "v02_exploratory_holdout_forecast.csv", index=False)

    # 5. EXPLORATORY 12-week inventory simulation.
    print("Running 12-week inventory simulation (EXPLORATORY)...")
    sim = _run_exploratory_simulation(
        panel_df, cohort_skus, holdout_weeks, scen, champion_id, c0_models, k_val
    )
    sim.insert(0, "label", EXPLORATORY_LABEL)
    sim.to_csv(rep / "v02_exploratory_simulation.csv", index=False)

    _write_markdown(rep / "v02_experiment.md", record, val_metrics, test_metrics, sim)
    print(val_metrics.to_string(index=False))
    print(test_metrics.drop(columns="label").to_string(index=False))
    print(sim.drop(columns="label").to_string(index=False))
    return {"selection": record, "validation": val_metrics, "test": test_metrics, "sim": sim}


def _write_markdown(
    path: Path,
    record: dict[str, Any],
    val: pd.DataFrame,
    test: pd.DataFrame,
    sim: pd.DataFrame,
) -> None:
    def table(df: pd.DataFrame, cols: list[str]) -> str:
        lines = ["| " + " | ".join(cols) + " |", "|" + " --- |" * len(cols)]
        for _, r in df.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                cells.append(f"{v:.4f}" if isinstance(v, float) else str(v))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    sim_cols = [
        "policy",
        "net_realized_cost_scu",
        "cost_change_vs_p0",
        "fill_rate",
        "total_unmet_units",
        "capacity_breaches",
        "solver_failures",
        "time_limited_solves",
    ]
    text = f"""# v0.2 experiment (protocol D18)

Code revision: `{record["code_revision"]}`. Generated by `python -m demandguard.cli experiment-v02`.

## 1. Pre-holdout validation (selection evidence)

Four origins 2011-05-16 to 2011-08-08; last target 2011-09-05 (c0). Selection frozen in
`artifacts/v02/selection_record.json` before any test-window scoring.

{table(val, ["model_id", "wape", "mae", "bias", "count"])}

- Champion: **{record["champion_model_id"]}**. {record["selection_reason"]}
- Relative validation WAPE reduction vs B2: {record["relative_wape_reduction_vs_b2"]:.2%} (O3 target 10%).

## 2. Test-window forecasts — EXPLORATORY

The window 2011-09-12 to 2011-11-28 was viewed in v0.1. These numbers cannot support an O3 claim.

{table(test, ["model_id", "wape", "mae", "bias", "count"])}

## 3. 12-week inventory simulation — EXPLORATORY

Same initial state, budget, capacity and k={record["safety_stock_k"]} as v0.1. Costs in SCU.

{table(sim, sim_cols)}

MILP solves stop at a proven 0.1% relative gap (D23); a solve that reaches the time limit first is
counted in `time_limited_solves`, places zero orders that week and is also a solver failure.

O5 requires at least 5% lower cost than P0, fill rate at least P0's and zero breaches; any result
here is exploratory.
"""
    path.write_text(text, encoding="utf-8")
