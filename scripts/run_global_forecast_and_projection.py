"""Run global forecast, simulation and projection outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.global_returns import load_global_universe
from project.projection.global_forecast_engine import run_global_forecasts
from project.projection.global_simulation_engine import run_global_simulations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_portfolio_projection.yaml",
        help="Path to projection config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = Path(config.get("output_dir", "data/processed"))
    output_dir.mkdir(parents=True, exist_ok=True)
    returns_path = Path(
        config.get("returns_path", "data/processed/global_security_returns.csv")
    )
    weights_path = Path(
        config.get("weights_path", "data/processed/global_master_candidate_weights.csv")
    )
    if not returns_path.exists() or not weights_path.exists():
        _write_status(
            output_dir, "insufficient_inputs", "Returns and final weights are required."
        )
        print("Global forecast/projection skipped: insufficient inputs.")
        return 0
    returns = _load_returns(returns_path)
    weights = (
        _load_final_weights(weights_path, output_dir).reindex(returns.columns).dropna()
    )
    if weights.empty:
        _write_status(
            output_dir, "insufficient_inputs", "No final weights overlap returns."
        )
        print("Global forecast/projection skipped: no overlapping weights.")
        return 0
    weights = weights / weights.sum()
    portfolio_returns = returns[weights.index]
    horizons = [int(value) for value in config.get("horizons_months", [1, 3, 6, 12])]
    forecasts = run_global_forecasts(
        portfolio_returns,
        horizons_months=horizons,
        random_state=int(config.get("random_state", 42)),
    )
    file_map = {
        "model_league": "global_forecast_model_league.csv",
        "regression_metrics": "global_forecast_regression_metrics.csv",
        "classification_metrics": "global_forecast_classification_metrics.csv",
        "time_series_metrics": "global_forecast_time_series_metrics.csv",
        "confusion_matrix": "global_forecast_confusion_matrix.csv",
        "roc_auc": "global_forecast_roc_auc.csv",
    }
    for key, filename in file_map.items():
        forecasts[key].to_csv(output_dir / filename, index=False)
    metadata = load_global_universe(
        ["data/universe/current_global_equity_universe.csv"]
    )
    simulations = run_global_simulations(
        portfolio_returns,
        weights,
        metadata,
        horizons_months=horizons,
        n_simulations=int(config.get("n_simulations", 1000)),
        random_state=int(config.get("random_state", 42)),
    )
    projection = simulations["monte_carlo"]
    for horizon in horizons:
        projection.loc[projection["Horizon_Months"].eq(horizon)].to_csv(
            output_dir / f"global_portfolio_projection_{horizon}m.csv",
            index=False,
        )
    projection.to_csv(output_dir / "global_monte_carlo_projection.csv", index=False)
    simulations["scenario_analysis"].to_csv(
        output_dir / "global_scenario_analysis.csv", index=False
    )
    simulations["stress_tests"].to_csv(
        output_dir / "global_stress_test_results.csv", index=False
    )
    _write_status(
        output_dir, "completed", "Global forecast and projection outputs written."
    )
    print("Global forecast and projection outputs written.")
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def _load_final_weights(path: Path, output_dir: Path) -> pd.Series:
    raw = pd.read_csv(path)
    final_model = None
    decision_path = output_dir / "global_master_decision_summary.json"
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        final_model = decision.get("final_model")
    if final_model and "Model" in raw:
        selected = raw.loc[raw["Model"].astype(str).eq(str(final_model))]
    elif "Model" in raw:
        selected = raw.loc[raw["Model"].astype(str).eq(str(raw["Model"].iloc[0]))]
    else:
        selected = raw
    return pd.Series(
        selected["Weight"].to_numpy(dtype=float), index=selected["Ticker"].astype(str)
    )


def _write_status(output_dir: Path, status: str, message: str) -> None:
    (output_dir / "global_forecast_projection_status.json").write_text(
        json.dumps({"status": status, "message": message}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
