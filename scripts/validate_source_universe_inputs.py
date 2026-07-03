"""Validate sourced global universe candidate CSV inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

REQUIRED_COLUMNS = [
    "ticker",
    "name",
    "sleeve",
    "region",
    "country",
    "exchange",
    "currency",
    "asset_type",
    "sector",
    "industry",
    "market_cap_usd",
    "market_cap_rank",
    "source",
    "source_url",
    "as_of_date",
    "data_provider",
    "investable",
    "benchmark_only",
    "signal_only",
    "include",
    "proxy_type",
    "source_method",
    "notes",
]

COMPACT_SOURCE_COLUMNS = [
    "ticker",
    "name",
    "exchange",
    "country",
    "currency",
    "source",
    "source_url",
    "as_of_date",
    "data_provider",
    "market_cap_usd",
    "market_cap_rank",
    "notes",
    "source_method",
]

ALLOWED_SOURCE_METHODS = {
    "exact_market_cap_rank",
    "index_proxy",
    "manual_review_required",
    "api_market_cap_enriched",
    "yfinance_enriched",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="configs/source_universe_validation.yaml",
        help="Path to source universe validation YAML config.",
    )
    return parser.parse_args()


def validate_source_inputs(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Validate configured source files without dropping rows."""
    source_dir = Path(config.get("source_dir", "data/universe/sources"))
    files = config.get("files", {}) or {}
    allowed_currencies = set(config.get("allowed_currencies", []) or [])
    summary_rows = []
    issues = []
    any_file_found = False
    malformed_schema = False
    for sleeve, filename in files.items():
        path = source_dir / filename
        if not path.exists():
            summary_rows.append(
                {
                    "sleeve": sleeve,
                    "file": str(path),
                    "status": "missing",
                    "rows": 0,
                    "issues": 1,
                }
            )
            issues.append(_issue(sleeve, path, "", "file_missing", "warning"))
            continue
        any_file_found = True
        try:
            frame = pd.read_csv(path)
        except Exception as exc:
            summary_rows.append(
                {
                    "sleeve": sleeve,
                    "file": str(path),
                    "status": "unreadable",
                    "rows": 0,
                    "issues": 1,
                }
            )
            issues.append(_issue(sleeve, path, "", f"unreadable_csv: {exc}", "error"))
            malformed_schema = True
            continue
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame]
        compact_missing = [
            column for column in COMPACT_SOURCE_COLUMNS if column not in frame
        ]
        if missing_columns and not compact_missing:
            frame = _expand_compact_source_frame(frame, sleeve)
            missing_columns = [
                column for column in REQUIRED_COLUMNS if column not in frame
            ]
        if missing_columns:
            issues.append(
                _issue(
                    sleeve,
                    path,
                    "",
                    "missing_required_columns: " + ", ".join(missing_columns),
                    "error",
                )
            )
            malformed_schema = True
        else:
            issues.extend(_row_issues(frame, sleeve, path, allowed_currencies))
        sleeve_issues = [
            issue
            for issue in issues
            if issue["sleeve"] == sleeve and issue["file"] == str(path)
        ]
        summary_rows.append(
            {
                "sleeve": sleeve,
                "file": str(path),
                "status": "validated",
                "rows": int(len(frame)),
                "issues": int(len(sleeve_issues)),
            }
        )
    status = {
        "status": (
            "source_inputs_missing"
            if not any_file_found
            else (
                "schema_error"
                if malformed_schema
                else "validated_with_issues" if issues else "validated"
            )
        ),
        "files_found": int(any_file_found),
        "issue_count": int(len(issues)),
    }
    return pd.DataFrame(summary_rows), pd.DataFrame(issues), status


def write_validation_outputs(
    summary: pd.DataFrame,
    issues: pd.DataFrame,
    status: dict,
    output_dir: str | Path,
) -> None:
    """Write validation summary, issue and status outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path / "source_universe_validation_summary.csv", index=False)
    if issues.empty:
        issues = pd.DataFrame(
            columns=["sleeve", "file", "row_index", "ticker", "issue", "severity"]
        )
    issues.to_csv(path / "source_universe_validation_issues.csv", index=False)
    (path / "source_universe_validation_status.json").write_text(
        json.dumps(status, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    summary, issues, status = validate_source_inputs(config)
    write_validation_outputs(
        summary,
        issues,
        status,
        config.get("output_dir", "data/processed"),
    )
    print(status["status"])
    return 1 if status["status"] == "schema_error" else 0


def _row_issues(
    frame: pd.DataFrame,
    sleeve: str,
    path: Path,
    allowed_currencies: set[str],
) -> list[dict[str, object]]:
    issues = []
    duplicates = frame["ticker"].astype(str).duplicated(keep=False)
    for idx, row in frame.iterrows():
        ticker = str(row.get("ticker", "") or "").strip()
        notes = str(row.get("notes", "") or "")
        if not ticker:
            issues.append(_issue(sleeve, path, idx, "ticker_missing", "error"))
        if not str(row.get("source", "") or "").strip():
            issues.append(_issue(sleeve, path, idx, "source_missing", "error", ticker))
        if not str(row.get("as_of_date", "") or "").strip():
            issues.append(
                _issue(sleeve, path, idx, "as_of_date_missing", "error", ticker)
            )
        elif pd.isna(pd.to_datetime(row.get("as_of_date"), errors="coerce")):
            issues.append(
                _issue(sleeve, path, idx, "invalid_as_of_date", "error", ticker)
            )
        if not str(row.get("source_url", "") or "").strip() and (
            "manual_review_required" not in notes
            and str(row.get("source_method", "") or "") != "manual_review_required"
        ):
            issues.append(
                _issue(
                    sleeve,
                    path,
                    idx,
                    "source_url_missing_without_manual_review_required",
                    "error",
                    ticker,
                )
            )
        currency = str(row.get("currency", "") or "").strip().upper()
        if allowed_currencies and currency not in allowed_currencies:
            issues.append(
                _issue(sleeve, path, idx, "invalid_currency", "error", ticker)
            )
        source_method = str(row.get("source_method", "") or "").strip()
        if source_method not in ALLOWED_SOURCE_METHODS:
            issues.append(
                _issue(sleeve, path, idx, "invalid_source_method", "error", ticker)
            )
        market_cap = pd.to_numeric(row.get("market_cap_usd"), errors="coerce")
        rank = pd.to_numeric(row.get("market_cap_rank"), errors="coerce")
        if pd.isna(market_cap):
            issues.append(
                _issue(sleeve, path, idx, "market_cap_usd_missing", "warning", ticker)
            )
        if pd.isna(rank):
            issues.append(
                _issue(sleeve, path, idx, "market_cap_rank_missing", "warning", ticker)
            )
        if bool(duplicates.iloc[idx]):
            issues.append(
                _issue(sleeve, path, idx, "duplicate_ticker_in_sleeve", "error", ticker)
            )
    return issues


def _expand_compact_source_frame(frame: pd.DataFrame, sleeve: str) -> pd.DataFrame:
    """Expand v2 market-cap-enriched source CSVs to the validation schema."""
    expanded = frame.copy()
    expanded["sleeve"] = sleeve
    expanded["region"] = expanded["country"].map(_region_from_country).fillna("Global")
    expanded["asset_type"] = "equity" if sleeve.startswith("global_equity") else "proxy"
    for column in ["sector", "industry"]:
        if column not in expanded:
            expanded[column] = ""
    for column, value in {
        "investable": True,
        "benchmark_only": False,
        "signal_only": False,
        "include": True,
        "proxy_type": "direct_listing",
    }.items():
        expanded[column] = value
    return expanded


def _region_from_country(country: object) -> str:
    value = str(country or "").lower()
    if "united states" in value:
        return "North America"
    if any(
        token in value for token in ["europe", "germany", "united kingdom", "turkey"]
    ):
        return "Europe"
    if any(token in value for token in ["china", "hong kong", "japan"]):
        return "Asia"
    return "Global"


def _issue(
    sleeve: str,
    path: Path,
    row_index: int | str,
    issue: str,
    severity: str,
    ticker: str = "",
) -> dict[str, object]:
    return {
        "sleeve": sleeve,
        "file": str(path),
        "row_index": row_index,
        "ticker": ticker,
        "issue": issue,
        "severity": severity,
    }


if __name__ == "__main__":
    sys.exit(main())
