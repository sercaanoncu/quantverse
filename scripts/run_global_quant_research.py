"""Run the global quantitative research pipeline when inputs are available."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_quant_research.yaml",
        help="Path to global quant research orchestration config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    current_config = config.get("current_universe_config")
    if current_config and Path(current_config).exists():
        result = _run_step("scripts/build_current_global_universe.py", current_config)
        if result != 0:
            return result
    elif current_config:
        print(
            f"Skipping scripts/build_current_global_universe.py: missing config {current_config}"
        )

    universe_path = _current_universe_path(current_config)
    if not _has_investable_global_equity(universe_path):
        _write_insufficient_input_status(
            _master_output_dir(config.get("master_portfolio_config"))
        )
        print(
            "Global master portfolio not promoted: sourced global equity universe is missing."
        )
        return 0

    steps = [
        ("scripts/build_global_returns_matrix.py", config.get("returns_matrix_config")),
        (
            "scripts/run_global_master_portfolio.py",
            config.get("master_portfolio_config"),
        ),
        ("scripts/run_global_portfolio_projection.py", config.get("projection_config")),
    ]
    for script, step_config in steps:
        if not step_config or not Path(step_config).exists():
            print(f"Skipping {script}: missing config {step_config}")
            continue
        result = _run_step(script, step_config)
        if result != 0:
            return result
    return 0


def _run_step(script: str, config_path: str) -> int:
    result = subprocess.run(
        [sys.executable, script, "--config", str(config_path)],
        check=False,
        text=True,
    )
    return int(result.returncode)


def _current_universe_path(config_path: str | None) -> Path:
    if config_path and Path(config_path).exists():
        config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        return Path(
            config.get(
                "output_universe_path",
                "data/universe/current_global_equity_universe.csv",
            )
        )
    return Path("data/universe/current_global_equity_universe.csv")


def _master_output_dir(config_path: str | None) -> Path:
    if config_path and Path(config_path).exists():
        config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        return Path(config.get("output_dir", "data/processed"))
    return Path("data/processed")


def _has_investable_global_equity(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        universe = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return False
    if universe.empty or "sleeve" not in universe:
        return False
    flags = _boolean_series(universe, "include") & _boolean_series(
        universe, "investable"
    )
    if "benchmark_only" in universe:
        flags &= ~_boolean_series(universe, "benchmark_only")
    if "signal_only" in universe:
        flags &= ~_boolean_series(universe, "signal_only")
    equity = universe["sleeve"].astype(str).str.startswith("global_equity")
    return bool((equity & flags).any())


def _boolean_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes", "y"}
    )


def _write_insufficient_input_status(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    decision = {
        "status": "insufficient_global_equity_universe",
        "run_type": "insufficient_inputs",
        "promotion_decision": "insufficient_inputs",
        "reason": "Sourced current global equity universe is missing or has zero investable equity rows.",
    }
    (output_dir / "global_quant_research_status.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )
    (output_dir / "global_master_decision_summary.json").write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
