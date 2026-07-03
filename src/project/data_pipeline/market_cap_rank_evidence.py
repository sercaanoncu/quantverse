"""Market-cap and rank evidence gates for global universe claims.

The functions here are offline validators. They do not fetch market caps,
infer missing ranks, or upgrade proxy/index rows into exact top-100 evidence.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

MARKET_CAP_RANK_EVIDENCE_COLUMNS = [
    "ticker",
    "name",
    "sleeve",
    "region",
    "country",
    "exchange",
    "currency",
    "asset_type",
    "market_cap_native",
    "market_cap_usd",
    "market_cap_rank",
    "rank_universe",
    "rank_method",
    "source_name",
    "source_url",
    "source_provider",
    "as_of_date",
    "retrieved_at",
    "source_method",
    "exact_proxy_status",
    "evidence_status",
    "notes",
]

EVIDENCE_STATUS_VALUES = {
    "exact_market_cap_rank",
    "index_proxy",
    "manual_review_required",
    "api_market_cap_enriched",
    "missing_market_cap_rank",
    "invalid_source",
    "stale_source",
    "duplicate_rank",
    "currency_missing",
}

EXACT_REQUIRED_COLUMNS = [
    "ticker",
    "market_cap_usd",
    "market_cap_rank",
    "rank_universe",
    "source_name",
    "source_url",
    "source_provider",
    "as_of_date",
    "region",
    "country",
    "exchange",
    "currency",
]

EXACT_TOP100_UNSUPPORTED_TEXT = (
    "Exact top-100 market-cap claim is not supported for these sleeves."
)

TURKISH_UNSUPPORTED_TEXT = (
    "Bu sleeve exact top-100 olarak tanitilamaz; cunku market-cap/rank kaniti, "
    "kaynak URL/provider veya as-of date eksiktir."
)


def normalize_market_cap_rank_evidence(
    frame: pd.DataFrame,
    retrieved_at: str | None = None,
) -> pd.DataFrame:
    """Return a canonical evidence frame without mutating ``frame``."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=MARKET_CAP_RANK_EVIDENCE_COLUMNS)

    normalized = pd.DataFrame(index=frame.index)
    for column in MARKET_CAP_RANK_EVIDENCE_COLUMNS:
        normalized[column] = ""

    passthrough = {
        "ticker": "ticker",
        "name": "name",
        "sleeve": "sleeve",
        "region": "region",
        "country": "country",
        "exchange": "exchange",
        "currency": "currency",
        "asset_type": "asset_type",
        "market_cap_native": "market_cap_native",
        "market_cap_usd": "market_cap_usd",
        "market_cap_rank": "market_cap_rank",
        "rank_universe": "rank_universe",
        "rank_method": "rank_method",
        "source_name": "source_name",
        "source_url": "source_url",
        "source_provider": "source_provider",
        "as_of_date": "as_of_date",
        "retrieved_at": "retrieved_at",
        "source_method": "source_method",
        "exact_proxy_status": "exact_proxy_status",
        "evidence_status": "evidence_status",
        "notes": "notes",
    }
    for target, source in passthrough.items():
        if source in frame:
            normalized[target] = frame[source]

    if "source_name" not in frame and "source" in frame:
        normalized["source_name"] = frame["source"]
    if "source_provider" not in frame and "data_provider" in frame:
        normalized["source_provider"] = frame["data_provider"]
    if "market_cap_native" not in frame and "market_cap_usd" in frame:
        normalized["market_cap_native"] = frame["market_cap_usd"]
    if "rank_universe" not in frame and "sleeve" in frame:
        normalized["rank_universe"] = frame["sleeve"]
    if "retrieved_at" not in frame:
        normalized["retrieved_at"] = retrieved_at or date.today().isoformat()
    if "source_method" not in frame:
        normalized["source_method"] = _infer_source_method(frame)

    normalized["exact_proxy_status"] = normalized.apply(
        _infer_exact_proxy_status, axis=1
    )
    normalized["evidence_status"] = normalized["exact_proxy_status"]

    for column in ["ticker", "sleeve", "currency", "rank_universe"]:
        normalized[column] = normalized[column].fillna("").astype(str).str.strip()
    return normalized[MARKET_CAP_RANK_EVIDENCE_COLUMNS].copy()


def validate_market_cap_rank_evidence(
    frame: pd.DataFrame,
    *,
    today: str | None = None,
    max_staleness_days: int = 370,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Validate evidence and return report, classification, blockers and BL report."""
    evidence = normalize_market_cap_rank_evidence(frame)
    if evidence.empty:
        empty_classification = pd.DataFrame(
            columns=[
                "sleeve",
                "rows",
                "classification",
                "exact_supported_rows",
                "blocking_rows",
                "reason",
                "required_text",
                "turkish_explanation",
            ]
        )
        empty_blockers = pd.DataFrame(columns=_blocker_columns())
        empty_bl = pd.DataFrame(columns=_black_litterman_columns())
        return evidence, empty_classification, empty_blockers, empty_bl

    blockers: list[dict[str, object]] = []
    report = evidence.copy()
    as_of = pd.to_datetime(report["as_of_date"], errors="coerce")
    today_ts = pd.Timestamp(today) if today else pd.Timestamp(date.today())
    stale_mask = as_of.notna() & ((today_ts - as_of).dt.days > max_staleness_days)
    duplicate_rank_mask = _duplicate_rank_mask(report)

    statuses = []
    for idx, row in report.iterrows():
        row_blockers = _row_blockers(row)
        if bool(stale_mask.loc[idx]):
            row_blockers.append(("as_of_date", "stale_source", "Source date is stale."))
        if bool(duplicate_rank_mask.loc[idx]):
            row_blockers.append(
                (
                    "market_cap_rank",
                    "duplicate_rank",
                    "Duplicate rank inside same sleeve/as-of/rank universe.",
                )
            )

        status = _status_from_row(row, row_blockers)
        statuses.append(status)
        blockers.extend(_blocker_rows(row, row_blockers, status))

    report["evidence_status"] = statuses
    classification = classify_exact_proxy_support(report)
    blocker_report = pd.DataFrame(blockers, columns=_blocker_columns())
    bl_report = build_black_litterman_prerequisite_report(report)
    return report, classification, blocker_report, bl_report


def classify_exact_proxy_support(report: pd.DataFrame) -> pd.DataFrame:
    """Build a sleeve-level exact/proxy classification report."""
    if report.empty:
        return pd.DataFrame(
            columns=[
                "sleeve",
                "rows",
                "classification",
                "exact_supported_rows",
                "blocking_rows",
                "reason",
                "required_text",
                "turkish_explanation",
            ]
        )

    rows = []
    for sleeve, sleeve_df in report.groupby("sleeve", dropna=False, sort=True):
        statuses = set(sleeve_df["evidence_status"].astype(str))
        exact_rows = int(sleeve_df["evidence_status"].eq("exact_market_cap_rank").sum())
        blocking_rows = int(
            sleeve_df["evidence_status"]
            .isin(
                {
                    "missing_market_cap_rank",
                    "invalid_source",
                    "stale_source",
                    "duplicate_rank",
                    "currency_missing",
                    "manual_review_required",
                    "index_proxy",
                }
            )
            .sum()
        )
        if exact_rows == len(sleeve_df) and len(sleeve_df) > 0:
            classification = "exact_market_cap_rank_supported"
            reason = "All rows have valid market-cap/rank/source/as-of evidence."
        elif exact_rows > 0 or "api_market_cap_enriched" in statuses:
            classification = "partial_market_cap_rank_supported"
            reason = "Only part of the sleeve has usable market-cap/rank evidence."
        elif "index_proxy" in statuses:
            classification = "index_proxy_only"
            reason = "Rows are index/proxy constituents, not exact top-100 evidence."
        elif "manual_review_required" in statuses:
            classification = "manual_review_required"
            reason = "Rows require manual source review before exact claims."
        elif statuses <= {"invalid_source"}:
            classification = "source_unavailable"
            reason = "Source metadata is unavailable or invalid."
        else:
            classification = "blocked"
            reason = "Market-cap/rank/source evidence is incomplete."
        rows.append(
            {
                "sleeve": sleeve,
                "rows": int(len(sleeve_df)),
                "classification": classification,
                "exact_supported_rows": exact_rows,
                "blocking_rows": blocking_rows,
                "reason": reason,
                "required_text": (
                    ""
                    if classification == "exact_market_cap_rank_supported"
                    else EXACT_TOP100_UNSUPPORTED_TEXT
                ),
                "turkish_explanation": (
                    ""
                    if classification == "exact_market_cap_rank_supported"
                    else TURKISH_UNSUPPORTED_TEXT
                ),
            }
        )
    return pd.DataFrame(rows)


def build_black_litterman_prerequisite_report(report: pd.DataFrame) -> pd.DataFrame:
    """Return row-level Black-Litterman prior eligibility."""
    if report.empty:
        return pd.DataFrame(columns=_black_litterman_columns())
    rows = []
    for _, row in report.iterrows():
        cap = pd.to_numeric(row.get("market_cap_usd"), errors="coerce")
        valid = (
            pd.notna(cap)
            and float(cap) > 0
            and str(row.get("evidence_status", ""))
            in {"exact_market_cap_rank", "api_market_cap_enriched"}
            and _non_empty(row.get("source_url"))
            and _non_empty(row.get("source_provider"))
            and _non_empty(row.get("as_of_date"))
        )
        rows.append(
            {
                "ticker": row.get("ticker", ""),
                "sleeve": row.get("sleeve", ""),
                "market_cap_usd": row.get("market_cap_usd", ""),
                "market_cap_rank": row.get("market_cap_rank", ""),
                "evidence_status": row.get("evidence_status", ""),
                "black_litterman_prior_valid": bool(valid),
                "prerequisite_status": "allowed" if valid else "blocked_by_data",
                "reason": (
                    "Valid market-cap prior evidence is available."
                    if valid
                    else "Black-Litterman requires sourced positive market-cap priors."
                ),
            }
        )
    return pd.DataFrame(rows, columns=_black_litterman_columns())


def black_litterman_priors_available(
    metadata: pd.DataFrame,
    tickers: list[str] | pd.Index | None = None,
) -> bool:
    """Return True only when all requested tickers have valid BL priors."""
    if metadata is None or metadata.empty:
        return False
    frame = metadata.copy()
    if tickers is not None:
        wanted = {str(ticker) for ticker in tickers}
        frame = frame.loc[frame["ticker"].astype(str).isin(wanted)].copy()
        if frame.empty or set(frame["ticker"].astype(str)) != wanted:
            return False
    report, _, _, bl_report = validate_market_cap_rank_evidence(frame)
    if report.empty or bl_report.empty:
        return False
    return bool(bl_report["black_litterman_prior_valid"].all())


def write_market_cap_rank_outputs(
    frame: pd.DataFrame,
    output_dir: str | Path = "data/processed",
) -> dict[str, pd.DataFrame]:
    """Validate and write the four generated evidence reports."""
    report, classification, blockers, bl_report = validate_market_cap_rank_evidence(
        frame
    )
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    report.to_csv(path / "global_market_cap_rank_evidence_report.csv", index=False)
    classification.to_csv(
        path / "global_exact_proxy_classification_report.csv", index=False
    )
    blockers.to_csv(path / "global_market_cap_rank_blockers.csv", index=False)
    bl_report.to_csv(
        path / "global_black_litterman_prerequisite_report.csv", index=False
    )
    return {
        "evidence_report": report,
        "classification_report": classification,
        "blockers": blockers,
        "black_litterman_report": bl_report,
    }


def _infer_source_method(frame: pd.DataFrame) -> pd.Series:
    text = pd.Series("", index=frame.index, dtype=object)
    for column in ["source_method", "proxy_type", "source", "notes"]:
        if column in frame:
            text = text + " " + frame[column].fillna("").astype(str)
    lower = text.str.lower()
    return lower.map(_source_method_from_text)


def _source_method_from_text(value: str) -> str:
    if "manual_review_required" in value or "manual review" in value:
        return "manual_review_required"
    if "index_proxy" in value or "index" in value or "proxy" in value:
        return "index_proxy"
    if "api_market_cap_enriched" in value or "api" in value:
        return "api_market_cap_enriched"
    return ""


def _infer_exact_proxy_status(row: pd.Series) -> str:
    explicit = str(row.get("exact_proxy_status", "") or "").strip()
    if explicit:
        return explicit
    method = str(row.get("source_method", "") or "").strip()
    if method in EVIDENCE_STATUS_VALUES:
        return method
    notes = str(row.get("notes", "") or "").lower()
    if "manual_review_required" in notes:
        return "manual_review_required"
    if method == "api_market_cap_enriched":
        return "api_market_cap_enriched"
    cap = pd.to_numeric(row.get("market_cap_usd"), errors="coerce")
    rank = pd.to_numeric(row.get("market_cap_rank"), errors="coerce")
    if pd.notna(cap) and float(cap) > 0 and pd.notna(rank) and float(rank) > 0:
        return "exact_market_cap_rank"
    source_text = " ".join(
        str(row.get(column, "") or "").lower()
        for column in ["source_name", "source_method", "notes"]
    )
    if "index" in source_text or "proxy" in source_text:
        return "index_proxy"
    return "missing_market_cap_rank"


def _duplicate_rank_mask(report: pd.DataFrame) -> pd.Series:
    rank = pd.to_numeric(report["market_cap_rank"], errors="coerce")
    candidate = report.assign(_rank=rank).loc[rank.notna()].copy()
    if candidate.empty:
        return pd.Series(False, index=report.index)
    duplicate = candidate.duplicated(
        subset=["sleeve", "as_of_date", "rank_universe", "_rank"], keep=False
    )
    mask = pd.Series(False, index=report.index)
    mask.loc[candidate.index] = duplicate
    return mask


def _row_blockers(row: pd.Series) -> list[tuple[str, str, str]]:
    blockers = []
    cap = pd.to_numeric(row.get("market_cap_usd"), errors="coerce")
    rank = pd.to_numeric(row.get("market_cap_rank"), errors="coerce")
    desired_exact = str(row.get("exact_proxy_status", "")) == "exact_market_cap_rank"
    method = str(row.get("source_method", "") or "")

    if not _non_empty(row.get("currency")):
        blockers.append(("currency", "currency_missing", "Currency is required."))
    if method == "index_proxy" and desired_exact:
        blockers.append(
            (
                "source_method",
                "index_proxy",
                "Index proxy cannot be upgraded to exact top-100 evidence.",
            )
        )
    if method == "manual_review_required":
        blockers.append(
            (
                "source_method",
                "manual_review_required",
                "Manual review rows remain research/proxy only.",
            )
        )
    if pd.isna(cap) or float(cap) <= 0:
        blockers.append(
            (
                "market_cap_usd",
                "missing_market_cap_rank",
                "Missing positive market cap blocks exact status.",
            )
        )
    if pd.isna(rank) or float(rank) <= 0:
        blockers.append(
            (
                "market_cap_rank",
                "missing_market_cap_rank",
                "Missing positive rank blocks exact status.",
            )
        )
    for column in [
        "ticker",
        "rank_universe",
        "source_name",
        "source_url",
        "source_provider",
        "as_of_date",
        "region",
        "country",
        "exchange",
    ]:
        if not _non_empty(row.get(column)):
            status = "invalid_source"
            blockers.append((column, status, f"{column} is required."))
    return blockers


def _status_from_row(row: pd.Series, blockers: list[tuple[str, str, str]]) -> str:
    if not blockers:
        status = str(row.get("exact_proxy_status", "") or "")
        if status in {"exact_market_cap_rank", "api_market_cap_enriched"}:
            return status
        return "exact_market_cap_rank"
    status_order = [
        "duplicate_rank",
        "stale_source",
        "currency_missing",
        "index_proxy",
        "manual_review_required",
        "invalid_source",
        "missing_market_cap_rank",
    ]
    blocker_statuses = {status for _, status, _ in blockers}
    for status in status_order:
        if status in blocker_statuses:
            return status
    return "invalid_source"


def _blocker_rows(
    row: pd.Series,
    blockers: list[tuple[str, str, str]],
    status: str,
) -> list[dict[str, object]]:
    rows = []
    for column, issue, detail in blockers:
        rows.append(
            {
                "ticker": row.get("ticker", ""),
                "sleeve": row.get("sleeve", ""),
                "evidence_status": status,
                "issue": issue,
                "column": column,
                "what_wrong": detail,
                "why_important": "Exact top-100 and Black-Litterman claims need auditable market-cap/rank evidence.",
                "promotion_blocker": True,
                "next_fix": "Provide sourced market cap, rank, provider, URL, rank universe and as-of date; otherwise keep proxy/manual status.",
            }
        )
    return rows


def _non_empty(value: object) -> bool:
    if pd.isna(value):
        return False
    return bool(str(value).strip())


def _blocker_columns() -> list[str]:
    return [
        "ticker",
        "sleeve",
        "evidence_status",
        "issue",
        "column",
        "what_wrong",
        "why_important",
        "promotion_blocker",
        "next_fix",
    ]


def _black_litterman_columns() -> list[str]:
    return [
        "ticker",
        "sleeve",
        "market_cap_usd",
        "market_cap_rank",
        "evidence_status",
        "black_litterman_prior_valid",
        "prerequisite_status",
        "reason",
    ]
