"""Build global security price and return matrices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
from project.data_pipeline.security_identity import (
    apply_security_history_boundaries,
    attach_run_metadata,
    build_security_history_eligibility,
    build_security_identity_audit,
    load_security_identity_overrides,
    resolve_security_master_rows,
)
from project.research.run_identity import (
    build_run_manifest,
    register_artifacts,
    write_run_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/global_returns_matrix.yaml",
        help="Path to global returns matrix YAML config.",
    )
    parser.add_argument(
        "--analysis-config",
        default="configs/global_equity_research.yaml",
        help=(
            "Path to the downstream analytical YAML included in the composite "
            "run identity."
        ),
    )
    parser.add_argument(
        "--master-config",
        default="configs/global_master_portfolio.yaml",
        help=(
            "Path to the master-portfolio YAML included in the composite run "
            "identity."
        ),
    )
    parser.add_argument(
        "--source-config",
        default="configs/source_universe_validation.yaml",
        help="Path to the source-universe validation YAML included in run identity.",
    )
    parser.add_argument(
        "--universe-config",
        default="configs/current_global_universe.yaml",
        help="Path to the current-universe build YAML included in run identity.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    analysis_config_path = Path(args.analysis_config)
    if not analysis_config_path.exists():
        print(f"Analysis config not found: {analysis_config_path}")
        return 1
    analysis_config = (
        yaml.safe_load(analysis_config_path.read_text(encoding="utf-8")) or {}
    )
    master_config_path = Path(args.master_config)
    if not master_config_path.exists():
        print(f"Master portfolio config not found: {master_config_path}")
        return 1
    master_config = yaml.safe_load(master_config_path.read_text(encoding="utf-8")) or {}
    source_config_path = Path(args.source_config)
    if not source_config_path.exists():
        print(f"Source universe config not found: {source_config_path}")
        return 1
    source_config = yaml.safe_load(source_config_path.read_text(encoding="utf-8")) or {}
    universe_config_path = Path(args.universe_config)
    if not universe_config_path.exists():
        print(f"Current universe config not found: {universe_config_path}")
        return 1
    universe_config = (
        yaml.safe_load(universe_config_path.read_text(encoding="utf-8")) or {}
    )
    output_dir = Path(config.get("output_dir", "data/processed"))
    output_dir.mkdir(parents=True, exist_ok=True)

    universe_paths = [config.get("equity_universe_path", "")]
    universe_paths.extend(config.get("additional_universe_paths", []) or [])
    universe = load_global_universe([path for path in universe_paths if path])
    if universe.empty:
        _write_status(output_dir, "missing_universe", "No universe files were found.")
        print("No universe files found; returns matrix not built.")
        return 0
    universe = resolve_security_master_rows(universe)

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
    provider_prices = prices.copy()
    identity_overrides = load_security_identity_overrides(
        config.get(
            "security_identity_overrides_path",
            "data/reference/security_identity_overrides.csv",
        )
    )
    prices, truncation_report = apply_security_history_boundaries(
        prices, identity_overrides
    )

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
    simple_returns_usd = simple_returns_usd.dropna(axis=1, how="all").dropna(how="all")
    log_returns_usd = simple_to_log_returns(simple_returns_usd).dropna(how="all")
    data_as_of = (
        pd.Timestamp(prices.dropna(how="all").index.max()).date().isoformat()
        if not prices.dropna(how="all").empty
        else "unavailable"
    )
    run_manifest = build_run_manifest(
        universe,
        data_as_of_date=data_as_of,
        data_snapshot=simple_returns_usd,
        config_components={
            "returns_matrix": config,
            "analysis": analysis_config,
            "master_portfolio": master_config,
            "source_universe": source_config,
            "current_universe": universe_config,
        },
    )
    write_run_manifest(output_dir, run_manifest, reset_registry=True)
    identity_audit = build_security_identity_audit(
        universe,
        provider_prices,
        prices,
        simple_returns_usd,
        identity_overrides,
        truncation_report,
        minimum_standard_observations=int(
            config.get("minimum_standard_history_observations", 252)
        ),
        minimum_forecast_observations=int(
            config.get("minimum_forecast_history_observations", 252)
        ),
        minimum_walk_forward_observations=int(
            config.get("minimum_walk_forward_history_observations", 252)
        ),
    )
    identity_audit = attach_run_metadata(identity_audit, run_manifest)
    history_eligibility = attach_run_metadata(
        build_security_history_eligibility(identity_audit), run_manifest
    )
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
    fx_prices.to_csv(output_dir / "global_fx_prices.csv", index_label="Date")
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
    identity_audit.to_csv(
        output_dir / "global_security_identity_audit.csv", index=False
    )
    history_eligibility.to_csv(
        output_dir / "global_security_history_eligibility.csv", index=False
    )
    _write_status(
        output_dir,
        "completed",
        f"Built USD-normalized simple/log returns for {simple_returns_usd.shape[1]} assets.",
        run_manifest=run_manifest,
    )
    register_artifacts(
        output_dir,
        [
            *[Path(path) for path in universe_paths if path and Path(path).exists()],
            output_dir / "global_security_prices.csv",
            output_dir / "global_security_simple_returns_local.csv",
            output_dir / "global_security_simple_returns_usd.csv",
            output_dir / "global_security_log_returns_local.csv",
            output_dir / "global_security_log_returns_usd.csv",
            output_dir / "global_fx_prices.csv",
            output_dir / "global_returns_coverage_report.csv",
            output_dir / "global_fx_normalization_report.csv",
            output_dir / "global_security_identity_audit.csv",
            output_dir / "global_security_history_eligibility.csv",
            output_dir / "global_returns_matrix_status.json",
        ],
        run_manifest,
        root=ROOT,
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


def _write_status(
    output_dir: Path,
    status: str,
    message: str,
    *,
    run_manifest: dict[str, str] | None = None,
) -> None:
    payload = {"status": status, "message": message}
    payload.update(run_manifest or {})
    (output_dir / "global_returns_matrix_status.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
