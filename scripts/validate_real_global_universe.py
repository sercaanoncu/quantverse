"""Validate current global universe market-cap/rank evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.global_returns import load_global_universe
from project.data_pipeline.market_cap_rank_evidence import (
    write_market_cap_rank_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_master_portfolio.yaml",
        help="Path to a config containing universe_paths and output_dir.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    ) or {}
    universe_paths = config.get("universe_paths") or [
        "data/universe/current_global_equity_universe.csv",
        "data/universe/commodity_real_assets_universe.csv",
        "data/universe/defensive_assets_universe.csv",
        "data/universe/crypto_universe_template.csv",
    ]
    output_dir = Path(config.get("output_dir", "data/processed"))
    universe = load_global_universe(universe_paths)
    if universe.empty:
        outputs = write_market_cap_rank_outputs(pd.DataFrame(), output_dir)
        print("market_cap_rank_evidence_missing")
        return 0

    outputs = write_market_cap_rank_outputs(universe, output_dir)
    classification = outputs["classification_report"]
    blockers = outputs["blockers"]
    exact_supported = int(
        classification["classification"].eq("exact_market_cap_rank_supported").sum()
        if not classification.empty
        else 0
    )
    print(
        "market_cap_rank_evidence_validated: "
        f"sleeves={len(classification)} exact_supported={exact_supported} "
        f"blockers={len(blockers)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
