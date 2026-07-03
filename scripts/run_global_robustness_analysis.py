"""Run bounded QuantVerse v2 robustness and sensitivity analysis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.research.global_robustness import (
    run_robustness_sensitivity,
    write_robustness_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config).get("v2", {})
    returns = _read_returns(PROCESSED / "global_security_simple_returns_usd.csv")
    scores = _read_csv(PROCESSED / "global_stock_scores.csv")
    forecasts = _read_csv(PROCESSED / "global_stock_return_forecasts.csv")
    universe = _read_csv(
        ROOT / "data" / "universe" / "current_global_equity_universe.csv"
    )
    if returns.empty or scores.empty:
        print("Missing returns or scores; robustness analysis not run.")
        return 0
    result = run_robustness_sensitivity(
        returns,
        scores,
        forecasts=forecasts,
        metadata=universe,
        random_portfolios=int(config.get("robustness_random_portfolios", 150)),
        max_scenarios=int(config.get("robustness_max_scenarios", 48)),
    )
    write_robustness_outputs(result, PROCESSED)
    print(
        "Global robustness analysis written: "
        f"{result['summary'].get('robustness_status', 'missing')}"
    )
    return 0


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
