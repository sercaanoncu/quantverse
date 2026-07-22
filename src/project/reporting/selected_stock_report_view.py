"""Canonical report-facing selected-stock metadata view.

The raw stock-scoring table intentionally remains unchanged. This module joins
that research evidence to enriched security metadata while preserving the
distinct meanings of listing venue, issuer domicile, and economic exposure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from project.data_pipeline.security_identity import (
    attach_run_metadata,
    resolve_security_master_rows,
)

REPORT_COLUMNS = [
    "ticker",
    "name",
    "selection_rank",
    "composite_quant_score",
    "listing_country",
    "issuer_country",
    "economic_country",
    "listing_currency",
    "exchange",
    "sector",
    "industry",
    "metadata_source",
    "metadata_confidence",
    "metadata_as_of_date",
    "adr_or_foreign_issuer_flag",
    "warning_flags",
    "selection_reason",
]

QUALITY_COLUMNS = [
    "selected_stock_count",
    "matched_metadata_count",
    "unmatched_metadata_count",
    "duplicate_ticker_count",
    "listing_country_coverage_ratio",
    "issuer_country_coverage_ratio",
    "economic_country_coverage_ratio",
    "sector_coverage_ratio",
    "industry_coverage_ratio",
    "semantic_view_status",
    "interpretation",
    "invalidation_condition",
]

UNAVAILABLE = "unavailable"
_MISSING_TEXT = {"", "missing", "nan", "none", "not available", "unavailable"}


def build_selected_stock_report_view(
    stock_scores: pd.DataFrame,
    top_holdings_metadata: pd.DataFrame,
    universe_metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the selected-stock semantic view without mutating source frames.

    ``country`` and ``currency`` are treated only as documented legacy source
    aliases for listing country and listing currency. They are never used to
    populate issuer domicile or economic exposure.
    """

    if "ticker" not in stock_scores:
        raise ValueError("stock_scores must contain a ticker column")

    selected = _select_rows(stock_scores).reset_index(drop=True)
    selected["_ticker_key"] = _normalized_tickers(selected["ticker"])
    _raise_on_duplicate_keys(selected, "selected stock scores")
    selected_keys = set(selected["_ticker_key"])

    holdings = _prepare_metadata(
        top_holdings_metadata, "holding", selected_keys=selected_keys
    )
    universe = _prepare_metadata(
        universe_metadata, "universe", selected_keys=selected_keys
    )

    merged = selected.merge(
        holdings, on="_ticker_key", how="left", validate="one_to_one"
    ).merge(universe, on="_ticker_key", how="left", validate="one_to_one")

    result = pd.DataFrame(index=merged.index)
    result["ticker"] = merged["ticker"].astype(str).str.strip()
    result["name"] = _coalesce_text(merged, ["name", "holding__name", "universe__name"])
    result["selection_rank"] = _coalesce_numeric(
        merged, ["selection_rank", "rank_global"]
    )
    result["composite_quant_score"] = _coalesce_numeric(
        merged, ["composite_quant_score"]
    )

    result["listing_country"] = _coalesce_text(
        merged,
        [
            "holding__listing_country",
            "listing_country",
            "universe__listing_country",
            "country",
            "universe__country",
        ],
    )
    result["issuer_country"] = _coalesce_text(
        merged,
        ["holding__issuer_country", "issuer_country", "universe__issuer_country"],
    )
    result["economic_country"] = _coalesce_text(
        merged,
        [
            "holding__economic_country",
            "economic_country",
            "universe__economic_country",
        ],
    )
    result["listing_currency"] = _coalesce_text(
        merged,
        [
            "holding__listing_currency",
            "listing_currency",
            "universe__listing_currency",
            "currency",
            "universe__currency",
        ],
    )
    for column in ["exchange", "sector", "industry"]:
        result[column] = _coalesce_text(
            merged,
            [f"holding__{column}", column, f"universe__{column}"],
        )
    result["metadata_source"] = _coalesce_text(
        merged, ["holding__metadata_source", "universe__metadata_source"]
    )
    result["metadata_confidence"] = _coalesce_text(
        merged, ["holding__metadata_confidence", "universe__metadata_confidence"]
    )
    result["metadata_as_of_date"] = _coalesce_text(
        merged,
        [
            "holding__metadata_as_of_date",
            "universe__metadata_as_of_date",
            "universe__as_of_date",
        ],
    )
    result["adr_or_foreign_issuer_flag"] = _coalesce_flag(
        merged,
        [
            "holding__adr_or_foreign_issuer_flag",
            "adr_or_foreign_issuer_flag",
            "universe__adr_or_foreign_issuer_flag",
        ],
    )
    result["selection_reason"] = _coalesce_text(
        merged, ["selection_reason", "holding__selection_reason"]
    )

    matched = merged.get("holding___matched", pd.Series(False, index=merged.index)).map(
        _as_bool
    ) | merged.get("universe___matched", pd.Series(False, index=merged.index)).map(
        _as_bool
    )
    result["warning_flags"] = _semantic_warning_flags(merged, result, matched)

    result = result[REPORT_COLUMNS]
    result.attrs["selected_stock_count"] = len(result)
    result.attrs["matched_metadata_count"] = int(matched.sum())
    result.attrs["unmatched_metadata_count"] = int((~matched).sum())
    result.attrs["duplicate_ticker_count"] = 0
    return result


def build_selected_stock_report_view_quality(
    report_view: pd.DataFrame,
) -> pd.DataFrame:
    """Return one-row join and semantic coverage diagnostics."""

    selected_count = int(
        report_view.attrs.get("selected_stock_count", len(report_view))
    )
    matched_count = int(
        report_view.attrs.get(
            "matched_metadata_count",
            _coverage_count(report_view, "metadata_source"),
        )
    )
    unmatched_count = int(
        report_view.attrs.get(
            "unmatched_metadata_count", max(selected_count - matched_count, 0)
        )
    )
    duplicate_count = int(report_view.attrs.get("duplicate_ticker_count", 0))
    coverage = {
        column: _coverage_ratio(report_view, column)
        for column in [
            "listing_country",
            "issuer_country",
            "economic_country",
            "sector",
            "industry",
        ]
    }

    if selected_count == 0 or duplicate_count > 0:
        status = "failed"
    elif unmatched_count > 0 or any(
        coverage[column] < 1.0
        for column in ["listing_country", "issuer_country", "sector", "industry"]
    ):
        status = "diagnostic_metadata_incomplete"
    elif coverage["economic_country"] < 1.0:
        status = "passed_with_metadata_warning"
    else:
        status = "passed"

    if status == "passed_with_metadata_warning":
        interpretation = (
            "Selected rows reconcile one-to-one and listing, issuer, sector and "
            "industry metadata are complete. Economic-country exposure is unavailable "
            "where explicit business-exposure metadata does not exist and is not inferred."
        )
    elif status == "passed":
        interpretation = (
            "Selected rows reconcile one-to-one and all tracked semantic metadata fields "
            "are supported by the joined evidence."
        )
    else:
        interpretation = (
            "The report view preserves selected rows, but one or more required metadata "
            "fields or joins are incomplete and must remain diagnostic."
        )

    quality = pd.DataFrame(
        [
            {
                "selected_stock_count": selected_count,
                "matched_metadata_count": matched_count,
                "unmatched_metadata_count": unmatched_count,
                "duplicate_ticker_count": duplicate_count,
                "listing_country_coverage_ratio": coverage["listing_country"],
                "issuer_country_coverage_ratio": coverage["issuer_country"],
                "economic_country_coverage_ratio": coverage["economic_country"],
                "sector_coverage_ratio": coverage["sector"],
                "industry_coverage_ratio": coverage["industry"],
                "semantic_view_status": status,
                "interpretation": interpretation,
                "invalidation_condition": (
                    "Invalid if normalized ticker joins duplicate or drop selected rows, "
                    "or if listing country, issuer domicile, economic exposure, or listing "
                    "currency are silently substituted for one another."
                ),
            }
        ]
    )
    return quality[QUALITY_COLUMNS]


def write_selected_stock_report_artifacts(
    stock_scores: pd.DataFrame,
    top_holdings_metadata: pd.DataFrame,
    output_dir: str | Path,
    universe_metadata: pd.DataFrame | None = None,
    run_metadata: Mapping[str, object] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build and write the semantic view plus its quality report."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_view = build_selected_stock_report_view(
        stock_scores, top_holdings_metadata, universe_metadata
    )
    quality = build_selected_stock_report_view_quality(report_view)
    if run_metadata:
        report_view = attach_run_metadata(report_view, run_metadata)
        quality = attach_run_metadata(quality, run_metadata)
    report_view.to_csv(output / "global_selected_stocks_report_view.csv", index=False)
    quality.to_csv(
        output / "global_selected_stocks_report_view_quality.csv", index=False
    )
    return report_view, quality


def _select_rows(stock_scores: pd.DataFrame) -> pd.DataFrame:
    frame = stock_scores.copy()
    if "selection_flag" not in frame:
        return frame
    mask = frame["selection_flag"].map(_as_bool)
    return frame.loc[mask].copy()


def _prepare_metadata(
    frame: pd.DataFrame | None,
    prefix: str,
    *,
    selected_keys: set[str],
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame({"_ticker_key": pd.Series(dtype=str)})
    if "ticker" not in frame:
        raise ValueError(f"{prefix} metadata must contain a ticker column")
    prepared = (
        resolve_security_master_rows(frame) if prefix == "universe" else frame.copy()
    )
    prepared["_ticker_key"] = _normalized_tickers(prepared["ticker"])
    prepared = prepared.loc[prepared["_ticker_key"].isin(selected_keys)].copy()
    _raise_on_duplicate_keys(prepared, f"{prefix} metadata")
    prepared["_matched"] = True
    return prepared.rename(
        columns={
            column: f"{prefix}__{column}"
            for column in prepared.columns
            if column != "_ticker_key"
        }
    )


def _normalized_tickers(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.upper()
    if normalized.eq("").any():
        raise ValueError("ticker values must not be blank")
    return normalized


def _raise_on_duplicate_keys(frame: pd.DataFrame, label: str) -> None:
    if frame.empty:
        return
    duplicates = sorted(
        frame.loc[frame["_ticker_key"].duplicated(keep=False), "_ticker_key"].unique()
    )
    if duplicates:
        raise ValueError(f"duplicate normalized tickers in {label}: {duplicates}")


def _coalesce_text(frame: pd.DataFrame, columns: Iterable[str]) -> pd.Series:
    output = pd.Series(pd.NA, index=frame.index, dtype="object")
    for column in columns:
        if column not in frame:
            continue
        candidate = frame[column].map(_clean_text)
        output = output.where(output.notna(), candidate)
    return output.fillna(UNAVAILABLE).astype(str)


def _coalesce_numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.Series:
    output = pd.Series(float("nan"), index=frame.index, dtype=float)
    for column in columns:
        if column not in frame:
            continue
        candidate = pd.to_numeric(frame[column], errors="coerce")
        output = output.where(output.notna(), candidate)
    return output


def _coalesce_flag(frame: pd.DataFrame, columns: Iterable[str]) -> pd.Series:
    output = pd.Series(pd.NA, index=frame.index, dtype="object")
    for column in columns:
        if column not in frame:
            continue
        candidate = frame[column].map(_as_optional_bool)
        output = output.where(output.notna(), candidate)
    return output.map(lambda value: UNAVAILABLE if pd.isna(value) else bool(value))


def _semantic_warning_flags(
    merged: pd.DataFrame,
    result: pd.DataFrame,
    matched: pd.Series,
) -> pd.Series:
    source_warnings = (
        merged["warning_flags"]
        if "warning_flags" in merged
        else pd.Series("", index=merged.index)
    )
    warnings: list[str] = []
    for index in merged.index:
        flags = _split_flags(source_warnings.loc[index])
        if not bool(matched.loc[index]):
            flags.append("metadata_unmatched")
        if result.loc[index, "issuer_country"] == UNAVAILABLE:
            flags.append("issuer_country_unavailable")
        if result.loc[index, "economic_country"] == UNAVAILABLE:
            flags.append("economic_country_unavailable")
        listing = result.loc[index, "listing_country"]
        issuer = result.loc[index, "issuer_country"]
        if listing != UNAVAILABLE and issuer != UNAVAILABLE and listing != issuer:
            flags.append("listing_country_differs_from_issuer_country")
        warnings.append("; ".join(dict.fromkeys(flags)) if flags else "none")
    return pd.Series(warnings, index=merged.index, dtype="object")


def _split_flags(value: object) -> list[str]:
    cleaned = _clean_text(value)
    if cleaned is None or cleaned.lower() == "none":
        return []
    return [item.strip() for item in cleaned.split(";") if item.strip()]


def _clean_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    cleaned = str(value).strip()
    return None if cleaned.lower() in _MISSING_TEXT else cleaned


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _as_optional_bool(value: object) -> object:
    if value is None or pd.isna(value):
        return pd.NA
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return pd.NA


def _coverage_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame:
        return 0
    return int(frame[column].map(_clean_text).notna().sum())


def _coverage_ratio(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return 0.0
    return _coverage_count(frame, column) / len(frame)
