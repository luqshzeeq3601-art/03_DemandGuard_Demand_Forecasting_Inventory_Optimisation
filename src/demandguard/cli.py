"""DemandGuard command-line interface."""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from demandguard.contracts import ProductInventoryInput
from demandguard.inventory import (
    build_reorder_worklist,
    solve_inventory_milp,
    validate_milp_solution,
)
from demandguard.model import DemandGuardModel


def run_doctor() -> int:
    """Run environment and prerequisite checks (Gate G0)."""
    print("=== DemandGuard System Doctor ===")
    status = {"python": sys.version, "platform": sys.platform, "checks": {}}

    py_ok = sys.version_info >= (3, 10) and sys.version_info < (3, 14)
    status["checks"]["python_version"] = "PASS" if py_ok else "FAIL"
    print(f"[*] Python version: {sys.version.split()[0]} -> {'PASS' if py_ok else 'FAIL'}")

    packages = [
        "pandas",
        "openpyxl",
        "duckdb",
        "pyarrow",
        "numpy",
        "sklearn",
        "lightgbm",
        "statsmodels",
        "pulp",
        "fastapi",
        "pydantic",
        "uvicorn",
        "yaml",
        "matplotlib",
    ]
    pkg_status = {}
    for pkg in packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            pkg_status[pkg] = ver
            print(f"[*] Package {pkg}: {ver}")
        except ImportError as e:
            pkg_status[pkg] = f"MISSING: {e}"
            print(f"[!] Package {pkg}: MISSING")
    status["checks"]["packages"] = pkg_status

    try:
        import pulp

        prob = pulp.LpProblem("TinySolverTest", pulp.LpMinimize)
        x = pulp.LpVariable("x", lowBound=0, cat=pulp.LpInteger)
        y = pulp.LpVariable("y", lowBound=0, cat=pulp.LpInteger)
        prob += 2 * x + 3 * y
        prob += x + y >= 4

        solver = pulp.PULP_CBC_CMD(msg=False)
        solve_status = prob.solve(solver)
        solver_name = prob.solver.name if prob.solver else "CBC"
        status_str = pulp.LpStatus[solve_status]

        x_val = pulp.value(x)
        y_val = pulp.value(y)
        obj_val = pulp.value(prob.objective)

        solver_ok = (
            status_str == "Optimal"
            and abs(x_val - 4.0) < 1e-5
            and abs(y_val - 0.0) < 1e-5
            and abs(obj_val - 8.0) < 1e-5
        )
        status["checks"]["solver"] = {
            "status": "PASS" if solver_ok else "FAIL",
            "solver_name": solver_name,
            "solution_status": status_str,
            "objective": obj_val,
            "x": x_val,
            "y": y_val,
        }
        print(
            f"[*] PuLP CBC Solver: {status_str} (obj={obj_val}, x={x_val}, y={y_val}) -> "
            f"{'PASS' if solver_ok else 'FAIL'}"
        )
    except Exception as e:
        status["checks"]["solver"] = {"status": "FAIL", "error": str(e)}
        print(f"[!] PuLP CBC Solver: FAIL ({e})")
        solver_ok = False

    dirs_to_check = ["data/raw", "data/processed", "artifacts/champion", "reports"]
    dir_ok = True
    for d in dirs_to_check:
        p = Path(d)
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_test"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
        except Exception as e:
            dir_ok = False
            print(f"[!] Directory {d} not writable: {e}")
    status["checks"]["writable_directories"] = "PASS" if dir_ok else "FAIL"
    print(f"[*] Output directories writable: {'PASS' if dir_ok else 'FAIL'}")

    all_passed = (
        py_ok and all("MISSING" not in v for v in pkg_status.values()) and solver_ok and dir_ok
    )
    print(f"=== Doctor Result: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'} ===")
    return 0 if all_passed else 1


def generate_forecasts_from_history(
    history_path: str,
    artifact_dir: str = "artifacts/champion",
) -> pd.DataFrame:
    """Generate 4-week forecasts from a history CSV file using champion model."""
    df_hist = pd.read_csv(history_path)
    df_hist["week_start"] = pd.to_datetime(df_hist["week_start"]).dt.date

    # Validate input
    skus = sorted(df_hist["sku_id"].unique())
    all_weeks = sorted(df_hist["week_start"].unique())
    as_of_week = all_weeks[-1]

    if len(all_weeks) < 60:
        raise ValueError(
            f"History file contains {len(all_weeks)} weeks; at least 60 consecutive weeks required."
        )

    # Load champion model bundle
    model, metadata = DemandGuardModel.load_bundle(artifact_dir)

    target_weeks = [as_of_week + datetime.timedelta(weeks=h) for h in range(1, 5)]

    feat_rows = []
    for sku in skus:
        sku_sub = df_hist[df_hist["sku_id"] == sku].sort_values("week_start")
        sales_arr = sku_sub["units_sold"].values
        if len(sales_arr) < 60:
            raise ValueError(f"SKU {sku} has only {len(sales_arr)} history records; >=60 required.")

        for h in range(1, 5):
            f_dict = {
                "sku_id": sku,
                "origin_week_start": str(as_of_week),
                "horizon": h,
                "target_week_start": str(target_weeks[h - 1]),
            }
            # Lags relative to as_of_week (sales_arr[-1])
            for off in [0, 1, 2, 3, 7, 12, 25, 51]:
                idx = -(off + 1)
                f_dict[f"lag_{off}"] = float(sales_arr[idx]) if abs(idx) <= len(sales_arr) else 0.0
            for rw in [4, 13, 26]:
                r_sub = sales_arr[-rw:]
                f_dict[f"rolling_mean_{rw}"] = float(np.mean(r_sub))
                f_dict[f"rolling_std_{rw}"] = (
                    float(np.std(r_sub, ddof=1)) if len(r_sub) > 1 else 0.0
                )
                f_dict[f"zero_fraction_{rw}"] = float(np.mean(r_sub == 0))
            f_dict["trend_4_4"] = (
                float(np.mean(sales_arr[-4:]) - np.mean(sales_arr[-8:-4]))
                if len(sales_arr) >= 8
                else 0.0
            )
            tgt_d = target_weeks[h - 1]
            f_dict["origin_week_of_year"] = as_of_week.isocalendar()[1]
            f_dict["origin_month"] = as_of_week.month
            f_dict["target_week_of_year"] = tgt_d.isocalendar()[1]
            f_dict["target_month"] = tgt_d.month
            feat_rows.append(f_dict)

    feat_df = pd.DataFrame(feat_rows)
    raw_preds = model.predict(feat_df)

    out_rows = []
    for idx, r in feat_df.iterrows():
        out_rows.append(
            {
                "sku_id": r["sku_id"],
                "origin_week_start": str(r["origin_week_start"]),
                "target_week_start": str(r["target_week_start"]),
                "horizon": int(r["horizon"]),
                "predicted_units": float(raw_preds[idx]),
                "model_version": metadata.get("champion_model_id", "v0.1.0"),
                "data_version": "OnlineRetailII_UK",
                "run_id": metadata.get("created_at_utc", "local_run"),
            }
        )

    return pd.DataFrame(out_rows)


def run_forecast_command(
    history_path: str, output_path: str, artifact_dir: str = "artifacts/champion"
) -> int:
    """Execute forecast CLI command."""
    print(f"Generating forecasts for history: {history_path}")
    preds_df = generate_forecasts_from_history(history_path, artifact_dir=artifact_dir)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    preds_df.to_csv(out_p, index=False)
    print(f"Forecasts written to {out_p} ({len(preds_df)} rows)")
    return 0


def run_reorder_command(
    history_path: str,
    scenario_path: str,
    output_path: str,
    artifact_dir: str = "artifacts/champion",
) -> int:
    """Execute reorder CLI command."""
    print(
        f"Generating reorder recommendations for history: {history_path}, scenario: {scenario_path}"
    )
    preds_df = generate_forecasts_from_history(history_path, artifact_dir=artifact_dir)

    with open(scenario_path, "r", encoding="utf-8") as f:
        scen_cfg = yaml.safe_load(f)["scenario"]

    df_hist = pd.read_csv(history_path)
    skus = sorted(df_hist["sku_id"].unique())
    as_of_week = str(df_hist["week_start"].max())

    # Build forecast matrix
    fc_matrix = {sku: [] for sku in skus}
    for _, row in preds_df.iterrows():
        fc_matrix[row["sku_id"]].append(float(row["predicted_units"]))

    # Derive baseline on-hand and safety from recent history
    products = []
    for sku in skus:
        sku_hist = df_hist[df_hist["sku_id"] == sku]["units_sold"].values
        mean_13 = float(np.mean(sku_hist[-13:]))
        std_13 = float(np.std(sku_hist[-13:], ddof=1)) if len(sku_hist) > 1 else 0.0

        p = ProductInventoryInput(
            sku_id=sku,
            on_hand_units=int(np.ceil(2.0 * mean_13)),
            incoming_week_1_units=0,
            unit_purchase_cost_scu=scen_cfg.get("purchase_cost_scu", 1.0),
            holding_cost_scu_per_unit_week=scen_cfg.get("holding_cost_scu_per_unit_week", 0.02),
            unmet_penalty_scu_per_unit=scen_cfg.get("unmet_penalty_scu_per_unit", 5.0),
            safety_deficit_penalty_scu=scen_cfg.get("safety_deficit_penalty_scu_per_unit", 0.5),
            storage_slots_per_unit=scen_cfg.get("storage_slots_per_unit", 1.0),
            safety_stock_target_units=float(np.ceil(std_13)),
        )
        products.append(p)

    weekly_budgets = scen_cfg.get("weekly_budgets_scu", [2000.0, 2000.0, 2000.0, 2000.0])
    warehouse_capacity = scen_cfg.get("warehouse_capacity_slots", 5000)

    # Solve MILP
    raw_res, solved_orders, traces = solve_inventory_milp(
        products=products,
        forecast_matrix=fc_matrix,
        weekly_budgets_scu=weekly_budgets,
        warehouse_capacity_slots=warehouse_capacity,
    )

    # Independent validation
    is_valid, violations = validate_milp_solution(
        products=products,
        forecast_matrix=fc_matrix,
        weekly_budgets_scu=weekly_budgets,
        warehouse_capacity_slots=warehouse_capacity,
        solved_orders=solved_orders,
        solved_traces=traces,
    )

    response = build_reorder_worklist(
        products=products,
        forecast_matrix=fc_matrix,
        solved_orders=solved_orders,
        as_of_week_start=as_of_week,
        solver_meta=raw_res,
        validation_status="PASSED" if is_valid else "FAILED",
        warnings=violations,
    )

    worklist_df = pd.DataFrame([w.model_dump() for w in response.worklist])
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    worklist_df.to_csv(out_p, index=False)

    print(
        f"Reorder recommendations written to {out_p} (Status: {response.status}, Validated: {response.validation_status})"
    )
    print(worklist_df.to_string(index=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demandguard", description="DemandGuard CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Run system and prerequisite health check")

    p_acq = subparsers.add_parser("acquire", help="Acquire raw dataset")
    p_acq.add_argument("--config", default="config/project.yaml", help="Path to project config")

    p_prep = subparsers.add_parser("prepare", help="Prepare weekly sales panel")
    p_prep.add_argument("--config", default="config/project.yaml", help="Path to project config")

    p_split = subparsers.add_parser("split", help="Generate cohort and chronological splits")
    p_split.add_argument("--config", default="config/project.yaml", help="Path to project config")

    p_base = subparsers.add_parser("baseline", help="Evaluate baseline forecasting models")
    p_base.add_argument("--config", default="config/project.yaml", help="Path to project config")

    p_back = subparsers.add_parser(
        "backtest", help="Run full temporal validation across candidates"
    )
    p_back.add_argument("--config", default="config/project.yaml", help="Path to project config")

    p_sel = subparsers.add_parser(
        "select", help="Select and freeze champion forecast and inventory k"
    )
    p_sel.add_argument("--config", default="config/project.yaml", help="Path to project config")
    p_sel.add_argument("--scenario", default="config/scenario.yaml", help="Path to scenario config")

    p_eval = subparsers.add_parser("evaluate", help="Evaluate frozen model on test holdout")
    p_eval.add_argument(
        "--split", choices=["test", "validation"], default="test", help="Split to evaluate"
    )
    p_eval.add_argument("--config", default="config/project.yaml", help="Path to project config")
    p_eval.add_argument(
        "--scenario", default="config/scenario.yaml", help="Path to scenario config"
    )

    p_fc = subparsers.add_parser("forecast", help="Generate 4-week forecast from history file")
    p_fc.add_argument("--history", required=True, help="Path to history CSV file")
    p_fc.add_argument("--output", default="reports/forecast_output.csv", help="Output file path")
    p_fc.add_argument(
        "--artifact-dir", default="artifacts/champion", help="Champion artifact directory"
    )

    p_reord = subparsers.add_parser("reorder", help="Generate reorder recommendations")
    p_reord.add_argument("--history", required=True, help="Path to history CSV file")
    p_reord.add_argument(
        "--scenario", default="config/scenario.yaml", help="Scenario configuration"
    )
    p_reord.add_argument("--output", default="reports/reorder_output.csv", help="Output file path")
    p_reord.add_argument(
        "--artifact-dir", default="artifacts/champion", help="Champion artifact directory"
    )

    p_sim = subparsers.add_parser("simulate", help="Run multi-week inventory simulation")
    p_sim.add_argument(
        "--split", choices=["test", "validation"], default="test", help="Split to simulate"
    )
    p_sim.add_argument("--config", default="config/project.yaml", help="Path to project config")
    p_sim.add_argument("--scenario", default="config/scenario.yaml", help="Path to scenario config")

    p_mon = subparsers.add_parser("monitor", help="Run data and forecast monitoring")
    p_mon.add_argument("--history", required=True, help="Path to history CSV file")
    p_mon.add_argument("--output", default="reports/monitoring.json", help="Output JSON path")
    p_mon.add_argument(
        "--reference", default="data/processed/weekly_sales.parquet", help="Reference data"
    )

    p_rep = subparsers.add_parser("report", help="Generate comparison plots and release summary")
    p_rep.add_argument("--config", default="config/project.yaml", help="Path to project config")
    p_rep.add_argument("--scenario", default="config/scenario.yaml", help="Path to scenario config")

    return parser


def main(args: list[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)

    if parsed.command == "doctor":
        return run_doctor()

    if parsed.command == "acquire":
        from demandguard.data import acquire_source_data

        acquire_source_data(parsed.config)
        return 0

    if parsed.command == "prepare":
        from demandguard.data import run_prepare_pipeline

        run_prepare_pipeline(parsed.config)
        return 0

    if parsed.command == "split":
        from demandguard.splits import build_cohort_and_splits

        build_cohort_and_splits(parsed.config)
        return 0

    if parsed.command == "baseline" or parsed.command == "backtest":
        from demandguard.evaluation import run_temporal_backtests

        run_temporal_backtests(parsed.config)
        return 0

    if parsed.command == "select":
        from demandguard.evaluation import run_select_and_freeze

        run_select_and_freeze(parsed.config, parsed.scenario)
        return 0

    if parsed.command == "evaluate":
        from demandguard.evaluation import run_holdout_evaluation

        run_holdout_evaluation(parsed.config, parsed.scenario)
        return 0

    if parsed.command == "simulate":
        from demandguard.evaluation import run_holdout_simulation

        run_holdout_simulation(parsed.config, parsed.scenario)
        return 0

    if parsed.command == "forecast":
        return run_forecast_command(parsed.history, parsed.output, parsed.artifact_dir)

    if parsed.command == "reorder":
        return run_reorder_command(
            parsed.history, parsed.scenario, parsed.output, parsed.artifact_dir
        )

    if parsed.command == "monitor":
        from demandguard.monitoring import run_monitoring_pipeline

        run_monitoring_pipeline(parsed.history, parsed.output, parsed.reference)
        return 0

    if parsed.command == "report":
        from demandguard.reporting import generate_full_report

        generate_full_report(parsed.config, parsed.scenario)
        return 0

    print(f"Unknown command: {parsed.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
