"""Run QuantVerse v2 public-data global walk-forward validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.research.global_walk_forward import (
    run_public_data_walk_forward,
    write_walk_forward_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/global_quant_research.yaml")
    args = parser.parse_args()
    config = _config(args.config).get("v2", {})
    output = Path("data/processed")
    returns_path = output / "global_security_simple_returns_usd.csv"
    universe_path = Path("data/universe/current_global_equity_universe.csv")
    if not returns_path.exists() or not universe_path.exists():
        print("Missing returns or universe; walk-forward not run.")
        return 0
    result = run_public_data_walk_forward(
        _read_returns(returns_path),
        pd.read_csv(universe_path),
        train_window_days=int(config.get("walk_forward_train_days", 252)),
        test_window_days=int(config.get("walk_forward_test_days", 21)),
        step_days=int(config.get("walk_forward_step_days", 21)),
        max_assets=int(config.get("walk_forward_max_assets", 20)),
        max_weight=float(config.get("max_weight", 0.10)),
        transaction_cost_bps=float(config.get("transaction_cost_bps", 10.0)),
        max_folds=int(config.get("walk_forward_max_folds", 12)),
    )
    write_walk_forward_outputs(result, output)
    print(result["summary"].get("walk_forward_status", "not_run"))
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
