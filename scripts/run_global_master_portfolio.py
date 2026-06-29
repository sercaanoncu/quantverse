"""Run the global master portfolio research allocator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.global_returns import load_global_universe
from project.research.global_master_portfolio import (
    run_master_portfolio_research,
    write_master_portfolio_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_master_portfolio.yaml",
        help="Path to global master portfolio YAML config.",
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
    if not returns_path.exists():
        _write_status(output_dir, "missing_returns", "Global returns CSV is required.")
        print("Missing returns matrix; master portfolio not run.")
        return 0
    metadata = load_global_universe(config.get("universe_paths", []) or [])
    if metadata.empty:
        _write_status(
            output_dir, "missing_universe", "Global universe metadata is required."
        )
        print("Missing universe metadata; master portfolio not run.")
        return 0
    returns = _load_returns(returns_path)
    selection = config.get("selection", {}) or {}
    random_cfg = config.get("random_portfolios", {}) or {}
    result = run_master_portfolio_research(
        returns,
        metadata,
        min_holdings=int(selection.get("min_holdings", 10)),
        max_holdings=int(selection.get("max_holdings", 40)),
        max_weight=float(selection.get("max_weight", 0.10)),
        n_random_portfolios=int(random_cfg.get("n_portfolios", 10000)),
        random_state=int(selection.get("random_state", 42)),
    )
    write_master_portfolio_outputs(result, output_dir)
    print(result["decision_summary"]["promotion_decision"])
    return 0


def _load_returns(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    first = raw.columns[0]
    if str(first).lower() in {"date", "datetime", "timestamp"}:
        raw = raw.set_index(first)
    return raw.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")


def _write_status(output_dir: Path, status: str, message: str) -> None:
    (output_dir / "global_master_decision_summary.json").write_text(
        json.dumps({"status": status, "message": message}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
