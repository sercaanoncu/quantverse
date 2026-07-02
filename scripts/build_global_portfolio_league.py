"""Build QuantVerse v2 global portfolio model league."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.research.global_portfolio_league import (
    build_portfolio_league,
    write_portfolio_league_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config)
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    scores_path = output / "global_stock_scores.csv"
    forecasts_path = output / "global_stock_return_forecasts.csv"
    universe_path = Path("data/universe/current_global_equity_universe.csv")
    if not returns_path.exists() or not scores_path.exists():
        print("Missing returns or scores; portfolio league not built.")
        return 0
    league, weights, status = build_portfolio_league(
        _read_returns(returns_path),
        pd.read_csv(scores_path),
        pd.read_csv(forecasts_path) if forecasts_path.exists() else None,
        pd.read_csv(universe_path) if universe_path.exists() else None,
        max_assets=int(config.get("v2", {}).get("max_selected_stocks", 40)),
        max_weight=float(config.get("v2", {}).get("max_weight", 0.10)),
    )
    write_portfolio_league_outputs(league, weights, status, output)
    print(f"Global portfolio league written: {len(league)} models")
    return 0


def _config(path: str) -> dict:
    config_path = Path(path)
    return (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )


def _read_returns(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    first = frame.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(first)
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame


if __name__ == "__main__":
    sys.exit(main())
