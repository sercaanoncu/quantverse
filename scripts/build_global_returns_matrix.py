"""Build global security price and return matrices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.global_returns import (
    build_returns_matrix,
    coverage_report,
    fetch_prices_with_yfinance,
    filter_prices_by_coverage,
    fx_normalization_report,
    load_global_universe,
    load_price_matrix,
)
from project.data_pipeline.security_universe import filter_included_investable_assets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_returns_matrix.yaml",
        help="Path to global returns matrix YAML config.",
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

    universe_paths = [config.get("equity_universe_path", "")]
    universe_paths.extend(config.get("additional_universe_paths", []) or [])
    universe = load_global_universe([path for path in universe_paths if path])
    if universe.empty:
        _write_status(output_dir, "missing_universe", "No universe files were found.")
        print("No universe files found; returns matrix not built.")
        return 0

    investable = filter_included_investable_assets(universe)
    if investable.empty:
        _write_status(
            output_dir, "empty_investable_universe", "No investable rows found."
        )
        print("No investable assets found; returns matrix not built.")
        return 0

    local_price_csv = config.get("local_price_csv")
    if local_price_csv:
        prices = load_price_matrix(local_price_csv)
    else:
        prices = fetch_prices_with_yfinance(
            investable["ticker"].dropna().astype(str).drop_duplicates().tolist(),
            start=config.get("start_date"),
            end=config.get("end_date"),
        )
    if prices.empty:
        _write_status(
            output_dir,
            "missing_prices",
            "No local price CSV was supplied and optional yfinance fetch returned no data.",
        )
        print("No prices available; returns matrix not built.")
        return 0

    report = coverage_report(
        prices,
        universe,
        min_observations=int(config.get("min_price_observations", 20)),
    )
    covered_prices = filter_prices_by_coverage(prices, report)
    returns = build_returns_matrix(covered_prices).dropna(how="all")
    prices.to_csv(output_dir / "global_security_prices.csv", index_label="Date")
    returns.to_csv(output_dir / "global_security_returns.csv", index_label="Date")
    report.to_csv(output_dir / "global_returns_coverage_report.csv", index=False)
    fx_normalization_report(
        universe,
        base_currency=str(config.get("base_currency", "USD")),
    ).to_csv(output_dir / "global_fx_normalization_report.csv", index=False)
    _write_status(
        output_dir, "completed", f"Built returns for {returns.shape[1]} assets."
    )
    print(f"Global returns matrix assets: {returns.shape[1]}")
    return 0


def _write_status(output_dir: Path, status: str, message: str) -> None:
    (output_dir / "global_returns_matrix_status.json").write_text(
        json.dumps({"status": status, "message": message}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
