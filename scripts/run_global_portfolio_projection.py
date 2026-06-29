"""Run global asset and portfolio projection research."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.projection.portfolio_projection import monte_carlo_projection
from project.projection.return_forecasting import (
    downside_roc,
    forecast_asset_returns,
    forecast_model_league,
    optional_model_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_portfolio_projection.yaml",
        help="Path to global portfolio projection YAML config.",
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
    returns_path = Path(config.get("returns_path", ""))
    weights_path = Path(config.get("weights_path", ""))
    if not _valid_candidate_weights_available(weights_path, output_dir):
        _write_status(
            output_dir,
            "insufficient_inputs",
            "Valid global master candidate weights are required before projection.",
        )
        print("Projection skipped: valid global master candidate weights are missing.")
        return 0
    if not returns_path.exists():
        _write_status(output_dir, "missing_returns", "Returns CSV is required.")
        print("Missing returns matrix; projection not run.")
        return 0
    returns = _load_returns(returns_path)
    horizons = [int(value) for value in config.get("horizons_months", [1, 3, 6, 12])]
    forecasts = forecast_asset_returns(
        returns,
        horizons_months=horizons,
        random_state=int(config.get("random_state", 42)),
    )
    forecasts.to_csv(output_dir / "asset_return_forecasts.csv", index=False)
    forecast_model_league(forecasts).to_csv(
        output_dir / "forecast_model_league.csv",
        index=False,
    )
    weights = _load_weights(weights_path, returns.columns)
    projection = monte_carlo_projection(
        returns,
        weights,
        horizons_months=horizons,
        n_simulations=int(config.get("n_simulations", 1000)),
        random_state=int(config.get("random_state", 42)),
    )
    for horizon in horizons:
        projection.loc[projection["Horizon_Months"].eq(horizon)].to_csv(
            output_dir / f"portfolio_projection_{horizon}m.csv",
            index=False,
        )
    downside_roc(returns).to_csv(
        output_dir / "downside_classifier_roc.csv", index=False
    )
    _write_status(output_dir, "completed", "Projection outputs written.")
    print("Projection outputs written.")
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def _valid_candidate_weights_available(path: Path, output_dir: Path) -> bool:
    decision_path = output_dir / "global_master_decision_summary.json"
    if decision_path.exists():
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        if decision.get("promotion_decision") == "insufficient_inputs":
            return False
        if decision.get("run_type") == "insufficient_inputs":
            return False
    if not path.exists():
        return False
    raw = pd.read_csv(path)
    return {"Ticker", "Weight"}.issubset(raw.columns) and not raw.empty


def _load_weights(path: Path, tickers: pd.Index) -> pd.Series:
    raw = pd.read_csv(path)
    if "Model" in raw.columns:
        raw = raw.loc[raw["Model"].eq(raw["Model"].iloc[0])]
    weights = pd.Series(raw["Weight"].to_numpy(dtype=float), index=raw["Ticker"])
    weights = weights.reindex(tickers).dropna()
    if weights.empty or weights.sum() <= 0:
        raise ValueError("Candidate weights do not overlap returns columns.")
    return weights / weights.sum()


def _write_status(output_dir: Path, status: str, message: str) -> None:
    payload = {
        "status": status,
        "message": message,
        "optional_models": optional_model_status(),
    }
    (output_dir / "projection_model_status.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
