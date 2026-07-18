"""Build robust QuantVerse v2 model-selection and random-benchmark reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
    build_random_percentile_report,
    simulate_constrained_random_distribution,
    write_model_selection_outputs,
)  # noqa: E402
from project.data_pipeline.security_identity import attach_run_metadata  # noqa: E402
from project.research.run_identity import (  # noqa: E402
    read_run_manifest,
    register_artifacts,
)

PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config).get("v2", {})
    league = _read_csv(PROCESSED / "global_portfolio_league.csv")
    returns = _read_returns(PROCESSED / "global_security_simple_returns_usd.csv")
    weights = _read_csv(PROCESSED / "global_portfolio_league_weights.csv")
    risk = _read_csv(PROCESSED / "global_portfolio_risk_report.csv")
    walk = _read_csv(PROCESSED / "global_walk_forward_model_comparison.csv")
    turnover = _read_csv(PROCESSED / "global_walk_forward_turnover.csv")
    forecast_validation = _read_csv(
        PROCESSED / "global_forecast_validation_by_horizon.csv"
    )
    robustness = _read_json(PROCESSED / "global_parameter_sensitivity_summary.json")
    if league.empty or returns.empty:
        print("Missing league or returns; model selection report not built.")
        return 0
    selected_tickers = _selected_tickers_from_weights(weights, returns)
    selected_returns = returns[selected_tickers] if selected_tickers else returns
    random_distribution = simulate_constrained_random_distribution(
        selected_returns,
        n_portfolios=int(config.get("random_portfolio_samples", 1000)),
        max_weight=float(config.get("max_weight", 0.10)),
        random_state=int(config.get("random_state", 42)),
    )
    random_percentiles = build_random_percentile_report(league, random_distribution)
    selection = build_model_selection_report(
        league,
        walk_forward=walk,
        risk_report=risk,
        turnover=turnover,
        random_percentiles=random_percentiles,
        drawdown_tolerance=float(
            config.get("max_drawdown_worsening_vs_equal_weight", 0.05)
        ),
        cvar_tolerance=float(config.get("max_cvar_worsening_vs_equal_weight", 0.005)),
        min_sharpe_improvement_vs_equal_weight=float(
            config.get("min_sharpe_improvement_vs_equal_weight", 0.10)
        ),
        min_random_sharpe_percentile=float(
            config.get("min_random_sharpe_percentile", 0.60)
        ),
        max_turnover=float(config.get("max_turnover", 2.0)),
        forecast_validation_status=_forecast_validation_status(forecast_validation),
        robustness_status=str(robustness.get("robustness_status", "stable")),
    )
    decision = build_final_model_decision(selection)
    run_metadata = read_run_manifest(PROCESSED)
    selection = attach_run_metadata(selection, run_metadata)
    random_distribution = attach_run_metadata(random_distribution, run_metadata)
    random_percentiles = attach_run_metadata(random_percentiles, run_metadata)
    decision.update(run_metadata)
    write_model_selection_outputs(
        selection,
        decision,
        random_distribution,
        random_percentiles,
        PROCESSED,
    )
    register_artifacts(
        PROCESSED,
        [
            PROCESSED / "global_model_selection_report.csv",
            PROCESSED / "global_final_model_decision.csv",
            PROCESSED / "global_final_model_decision.json",
            PROCESSED / "global_random_portfolio_distribution.csv",
            PROCESSED / "global_random_portfolio_percentile_report.csv",
        ],
        run_metadata,
    )
    print(
        "Global model selection report written: "
        f"{len(selection)} models; final={decision['final_selected_model']}"
    )
    return 0


def _selected_tickers_from_weights(
    weights: pd.DataFrame, returns: pd.DataFrame
) -> list[str]:
    if weights.empty or "ticker" not in weights:
        return list(returns.columns)
    tickers = weights["ticker"].dropna().astype(str).drop_duplicates().tolist()
    selected = [ticker for ticker in tickers if ticker in returns.columns]
    return selected or list(returns.columns)


def _config(path: str) -> dict:
    config_path = ROOT / path
    return (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_returns(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame


def _forecast_validation_status(frame: pd.DataFrame) -> str:
    if frame.empty or "forecast_validation_status" not in frame:
        return "missing"
    statuses = frame["forecast_validation_status"].dropna().astype(str)
    if statuses.empty:
        return "missing"
    if statuses.eq("failed_scale_sanity").any():
        return "failed_scale_sanity"
    if statuses.eq("diagnostic_only").any():
        return "diagnostic_only"
    return str(statuses.mode().iloc[0])


if __name__ == "__main__":
    sys.exit(main())
