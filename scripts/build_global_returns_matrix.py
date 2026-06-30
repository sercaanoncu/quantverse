"""Build global security price and return matrices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.global_returns import (
    build_log_returns_matrix,
    build_returns_matrix,
    coverage_report,
    fetch_prices_with_yfinance,
    filter_prices_by_coverage,
    fx_mappings_from_config,
    load_global_universe,
    load_price_matrix,
    normalize_returns_to_base,
    return_outlier_report,
    simple_to_log_returns,
    required_fx_tickers,
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

    fx_config = config.get("fx", {}) or {}
    fx_mappings = fx_mappings_from_config(fx_config)
    fx_prices = _fx_prices(
        prices,
        investable,
        fx_mappings=fx_mappings,
        base_currency=str(config.get("base_currency", "USD")),
        start=config.get("start_date"),
        end=config.get("end_date"),
        local_price_csv=local_price_csv,
    )
    report = coverage_report(
        prices,
        universe,
        min_observations=int(config.get("min_price_observations", 20)),
    )
    covered_prices = filter_prices_by_coverage(prices, report)
    simple_returns_local = build_returns_matrix(covered_prices).dropna(how="all")
    log_returns_local = build_log_returns_matrix(covered_prices).dropna(how="all")
    simple_returns_usd, fx_report, fx_coverage = normalize_returns_to_base(
        simple_returns_local,
        universe,
        fx_prices,
        base_currency=str(config.get("base_currency", "USD")),
        fx_mappings=fx_mappings,
        max_forward_fill_days=int(fx_config.get("max_forward_fill_days", 2)),
    )
    simple_returns_usd = simple_returns_usd.dropna(how="all")
    log_returns_usd = simple_to_log_returns(simple_returns_usd).dropna(how="all")
    prices.to_csv(output_dir / "global_security_prices.csv", index_label="Date")
    simple_returns_local.to_csv(
        output_dir / "global_security_simple_returns_local.csv", index_label="Date"
    )
    simple_returns_usd.to_csv(
        output_dir / "global_security_simple_returns_usd.csv", index_label="Date"
    )
    log_returns_local.to_csv(
        output_dir / "global_security_log_returns_local.csv", index_label="Date"
    )
    log_returns_usd.to_csv(
        output_dir / "global_security_log_returns_usd.csv", index_label="Date"
    )
    simple_returns_usd.to_csv(
        output_dir / "global_security_simple_returns.csv", index_label="Date"
    )
    log_returns_usd.to_csv(
        output_dir / "global_security_log_returns.csv", index_label="Date"
    )
    simple_returns_usd.to_csv(
        output_dir / "global_security_returns.csv", index_label="Date"
    )
    report.to_csv(output_dir / "global_returns_coverage_report.csv", index=False)
    fx_report.to_csv(output_dir / "global_fx_normalization_report.csv", index=False)
    fx_coverage.to_csv(output_dir / "global_fx_rate_coverage_report.csv", index=False)
    return_outlier_report(simple_returns_usd).to_csv(
        output_dir / "global_return_outlier_report.csv", index=False
    )
    _write_status(
        output_dir,
        "completed",
        f"Built USD-normalized simple/log returns for {simple_returns_usd.shape[1]} assets.",
    )
    print(f"Global returns matrix assets: {simple_returns_usd.shape[1]}")
    return 0


def _fx_prices(
    prices: pd.DataFrame,
    investable: pd.DataFrame,
    *,
    fx_mappings: dict[str, dict[str, object]],
    base_currency: str,
    start: str | None,
    end: str | None,
    local_price_csv: str | None,
) -> pd.DataFrame:
    tickers = required_fx_tickers(
        investable,
        base_currency=base_currency,
        fx_mappings=fx_mappings,
    )
    local = prices[[ticker for ticker in tickers if ticker in prices]].copy()
    missing = [ticker for ticker in tickers if ticker not in local]
    if not missing or local_price_csv:
        return local
    fetched = fetch_prices_with_yfinance(missing, start=start, end=end)
    if fetched.empty:
        return local
    return pd.concat([local, fetched], axis=1).loc[
        :, ~pd.concat([local, fetched], axis=1).columns.duplicated()
    ]


def _write_status(output_dir: Path, status: str, message: str) -> None:
    (output_dir / "global_returns_matrix_status.json").write_text(
        json.dumps({"status": status, "message": message}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
