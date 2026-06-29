"""Build a source-aware current global equity universe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from project.data_pipeline.security_universe import (
    REQUIRED_UNIVERSE_COLUMNS,
    detect_survivorship_bias_risk,
    summarize_security_universe,
    validate_security_universe_schema,
)

INPUT_COLUMNS = [
    "ticker",
    "name",
    "exchange",
    "country",
    "currency",
    "source",
    "as_of_date",
    "notes",
]

REGION_BY_SLEEVE = {
    "global_equity_us": "North America",
    "global_equity_europe": "Europe",
    "global_equity_uk": "Europe",
    "global_equity_turkey": "Europe / Middle East",
    "global_equity_china": "Asia",
    "global_equity_japan": "Asia",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/current_global_universe.yaml",
        help="Path to current global universe YAML config.",
    )
    return parser.parse_args()


def build_current_global_universe(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a current universe and missing-market-cap report."""
    mode = str(config.get("mode", "csv")).lower()
    if mode not in {"csv", "online"}:
        raise ValueError("mode must be 'csv' or 'online'.")
    if mode == "online":
        return _empty_universe(), pd.DataFrame(
            [
                {
                    "ticker": "",
                    "sleeve": "",
                    "issue": "online_source_not_available",
                    "detail": "Online fetching hooks exist, but sourced CSV files are required in this sprint.",
                }
            ]
        )

    source_files = config.get("source_files", {}) or {}
    frames = []
    for sleeve, raw_path in source_files.items():
        path = Path(raw_path)
        if not path.exists():
            continue
        source = pd.read_csv(path)
        _validate_source_columns(source, path)
        frames.append(_normalize_source_frame(source, sleeve))

    if not frames:
        return _empty_universe(), pd.DataFrame(
            [
                {
                    "ticker": "",
                    "sleeve": "",
                    "issue": "source_csv_missing",
                    "detail": "No source CSV files were found. Populate data/universe/sources/*.csv.",
                }
            ]
        )

    universe = pd.concat(frames, ignore_index=True)
    universe = _rank_and_select_by_market_cap(
        universe,
        top_n_per_sleeve=int(config.get("top_n_per_sleeve", 100)),
    )
    validate_security_universe_schema(universe)
    missing = _missing_market_cap_report(universe)
    if missing.empty:
        missing = pd.DataFrame(columns=["ticker", "sleeve", "issue", "severity"])
    return universe, missing


def write_universe_outputs(
    universe: pd.DataFrame,
    missing_caps: pd.DataFrame,
    config: dict,
) -> None:
    """Write current universe, summary and warning reports."""
    output_universe = Path(
        config.get(
            "output_universe_path", "data/universe/current_global_equity_universe.csv"
        )
    )
    summary_path = Path(
        config.get("summary_path", "data/processed/current_global_universe_summary.csv")
    )
    missing_path = Path(
        config.get(
            "missing_market_caps_path",
            "data/processed/current_global_universe_missing_market_caps.csv",
        )
    )
    bias_path = Path(
        config.get(
            "bias_warnings_path",
            "data/processed/current_global_universe_bias_warnings.csv",
        )
    )
    for path in [output_universe, summary_path, missing_path, bias_path]:
        path.parent.mkdir(parents=True, exist_ok=True)

    universe.to_csv(output_universe, index=False)
    summary = (
        summarize_security_universe(universe) if not universe.empty else pd.DataFrame()
    )
    summary.to_csv(summary_path, index=False)
    missing_caps.to_csv(missing_path, index=False)
    bias = (
        detect_survivorship_bias_risk(universe)
        if not universe.empty
        else pd.DataFrame(columns=["ticker", "sleeve", "issue", "severity"])
    )
    bias.to_csv(bias_path, index=False)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    universe, missing = build_current_global_universe(config)
    write_universe_outputs(universe, missing, config)
    if universe.empty:
        print("No current global universe built; sourced CSV inputs are required.")
    else:
        print(f"Current global universe rows: {len(universe)}")
    return 0


def _validate_source_columns(df: pd.DataFrame, path: Path) -> None:
    missing = [column for column in INPUT_COLUMNS if column not in df]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def _normalize_source_frame(df: pd.DataFrame, sleeve: str) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        market_cap = pd.to_numeric(row.get("market_cap_usd", pd.NA), errors="coerce")
        rows.append(
            {
                "ticker": row["ticker"],
                "name": row["name"],
                "sleeve": sleeve,
                "region": REGION_BY_SLEEVE.get(sleeve, ""),
                "country": row["country"],
                "exchange": row["exchange"],
                "currency": row["currency"],
                "asset_type": "equity",
                "sector": row.get("sector", ""),
                "industry": row.get("industry", ""),
                "market_cap_usd": float(market_cap) if pd.notna(market_cap) else "",
                "market_cap_rank": "",
                "as_of_date": row["as_of_date"],
                "source": row["source"],
                "data_provider": row.get("data_provider", "source_csv"),
                "investable": True,
                "benchmark_only": False,
                "signal_only": False,
                "include": True,
                "proxy_type": "direct_listing",
                "notes": row["notes"],
            }
        )
    return pd.DataFrame(rows, columns=REQUIRED_UNIVERSE_COLUMNS)


def _rank_and_select_by_market_cap(
    universe: pd.DataFrame,
    top_n_per_sleeve: int,
) -> pd.DataFrame:
    selected = []
    for _, sleeve_df in universe.groupby("sleeve", sort=True):
        frame = sleeve_df.copy()
        cap = pd.to_numeric(frame["market_cap_usd"], errors="coerce")
        ranked = frame.loc[cap.notna() & (cap > 0)].copy()
        missing = frame.loc[cap.isna() | (cap <= 0)].copy()
        if not ranked.empty:
            ranked["_market_cap_numeric"] = pd.to_numeric(
                ranked["market_cap_usd"], errors="coerce"
            )
            ranked = ranked.sort_values("_market_cap_numeric", ascending=False)
            ranked = ranked.head(int(top_n_per_sleeve)).copy()
            ranked["market_cap_rank"] = range(1, len(ranked) + 1)
            ranked = ranked.drop(columns=["_market_cap_numeric"])
        if not missing.empty:
            missing["include"] = False
            missing["notes"] = (
                missing["notes"].fillna("").astype(str)
                + " | Missing market cap; retained for coverage audit, not selected."
            )
        selected.append(pd.concat([ranked, missing], ignore_index=True))
    if not selected:
        return _empty_universe()
    return pd.concat(selected, ignore_index=True)[REQUIRED_UNIVERSE_COLUMNS]


def _missing_market_cap_report(universe: pd.DataFrame) -> pd.DataFrame:
    cap = pd.to_numeric(universe["market_cap_usd"], errors="coerce")
    mask = universe["sleeve"].astype(str).str.startswith("global_equity") & (
        cap.isna() | (cap <= 0)
    )
    issues = universe.loc[mask, ["ticker", "sleeve"]].copy()
    if issues.empty:
        return pd.DataFrame(columns=["ticker", "sleeve", "issue", "severity"])
    issues["issue"] = "missing_market_cap_usd"
    issues["severity"] = "warning"
    return issues


def _empty_universe() -> pd.DataFrame:
    return pd.DataFrame(columns=REQUIRED_UNIVERSE_COLUMNS)


if __name__ == "__main__":
    sys.exit(main())
