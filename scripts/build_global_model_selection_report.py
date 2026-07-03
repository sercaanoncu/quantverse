"""Build robust QuantVerse v2 model-selection and random-benchmark reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
    build_random_percentile_report,
    simulate_constrained_random_distribution,
    write_model_selection_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
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
    )
    decision = build_final_model_decision(selection)
    write_model_selection_outputs(
        selection,
        decision,
        random_distribution,
        random_percentiles,
        PROCESSED,
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


if __name__ == "__main__":
    sys.exit(main())
