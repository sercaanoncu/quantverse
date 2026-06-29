"""Run the global quantitative research pipeline when inputs are available."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

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
    steps = [
        (
            "scripts/build_current_global_universe.py",
            config.get("current_universe_config"),
        ),
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
        result = subprocess.run(
            [sys.executable, script, "--config", str(step_config)],
            check=False,
            text=True,
        )
        if result.returncode != 0:
            return int(result.returncode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
