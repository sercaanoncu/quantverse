"""Security-identity and history-eligibility controls for QuantVerse v2.

Ticker symbols are routing labels, not permanent security identifiers. This
module keeps current-security history separate from prior symbol owners and
prevents short-history securities from entering the standard 12-month score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

ELIGIBILITY_STATUSES = {
    "eligible",
    "diagnostic_short_history",
    "blocked_identity_uncertain",
    "blocked_ticker_reuse_contamination",
    "blocked_insufficient_history",
    "manual_review_required",
}

IDENTITY_AUDIT_COLUMNS = [
    "ticker",
    "normalized_ticker",
    "security_name",
    "issuer_name",
    "listing_exchange",
    "listing_country",
    "issuer_country",
    "security_type",
    "stable_identifier_type",
    "stable_identifier",
    "current_listing_start_date",
    "provider_history_start_date",
    "first_valid_price_date",
    "first_valid_return_date",
    "effective_history_start",
    "observed_return_count",
    "observations_before_current_listing",
    "ticker_reuse_status",
    "identity_continuity_status",
    "history_contamination_status",
    "history_truncation_applied",
    "metadata_source",
    "evidence_url",
    "evidence_confidence",
    "eligibility_status",
    "standard_scoring_eligible",
    "forecast_eligible",
    "walk_forward_eligible",
    "exclusion_reason",
    "warning_flags",
]

HISTORY_ELIGIBILITY_COLUMNS = [
    "ticker",
    "effective_history_start",
    "first_valid_return_date",
    "observed_return_count",
    "identity_continuity_status",
    "ticker_reuse_status",
    "history_contamination_status",
    "eligibility_status",
    "standard_scoring_eligible",
    "forecast_eligible",
    "walk_forward_eligible",
    "exclusion_reason",
    "warning_flags",
]

FEATURE_HISTORY_COLUMNS = [
    "ticker",
    "observations",
    "1m_eligible",
    "3m_eligible",
    "6m_eligible",
    "12m_eligible",
    "volatility_3m_eligible",
    "volatility_12m_eligible",
    "sharpe_eligible",
    "sortino_eligible",
    "diversification_eligible",
    "standard_composite_score_eligible",
    "eligibility_status",
    "eligibility_reason",
]

BLOCKED_IDENTITY_STATUSES = {
    "blocked_identity_uncertain",
    "blocked_ticker_reuse_contamination",
    "manual_review_required",
}

VERIFIED_CONTINUITY_STATUSES = {
    "verified_same_security_continuity",
    "verified_predecessor_continuity",
}


def load_security_identity_overrides(path: str | Path | None) -> pd.DataFrame:
    """Load documented security-identity overrides, if supplied."""
    if path is None:
        return pd.DataFrame()
    source = Path(path)
    if not source.exists():
        return pd.DataFrame()
    frame = pd.read_csv(source, dtype=str).fillna("")
    if "ticker" not in frame:
        raise ValueError("Security-identity override file must contain ticker.")
    frame["ticker"] = frame["ticker"].map(normalize_ticker)
    duplicated = frame["ticker"].duplicated(keep=False)
    if duplicated.any():
        tickers = sorted(frame.loc[duplicated, "ticker"].unique())
        raise ValueError(f"Duplicate security-identity overrides: {tickers}")
    return frame


def resolve_security_master_rows(universe: pd.DataFrame) -> pd.DataFrame:
    """Resolve overlapping sleeve rows to one canonical row per ticker.

    Included investable rows take precedence over proxy rows that are retained
    only for coverage documentation. This prevents an excluded proxy row from
    silently suppressing a valid included security with the same ticker.
    """
    if universe.empty:
        return universe.copy()
    if "ticker" not in universe:
        raise ValueError("Universe must contain ticker.")
    frame = universe.copy()
    frame["ticker"] = frame["ticker"].map(normalize_ticker)
    frame["_row_order"] = np.arange(len(frame))
    frame["_investable_priority"] = frame.apply(
        lambda row: int(_included_investable(row)), axis=1
    )
    frame["_include_priority"] = frame.get(
        "include", pd.Series(True, index=frame.index)
    ).map(_as_bool)
    source_method = frame.get("source_method", pd.Series("", index=frame.index)).astype(
        str
    )
    frame["_source_priority"] = source_method.map(
        lambda value: (
            2
            if value in {"official_exchange", "regulatory_filing"}
            else 1 if value in {"api_market_cap_enriched", "direct_listing"} else 0
        )
    )
    frame["_as_of"] = pd.to_datetime(
        frame.get("as_of_date", pd.Series("", index=frame.index)),
        errors="coerce",
    )
    frame = frame.sort_values(
        [
            "ticker",
            "_investable_priority",
            "_include_priority",
            "_source_priority",
            "_as_of",
            "_row_order",
        ],
        ascending=[True, False, False, False, False, True],
        kind="mergesort",
    )
    canonical = frame.drop_duplicates("ticker", keep="first").sort_values(
        "_row_order", kind="mergesort"
    )
    return canonical.drop(
        columns=[
            "_row_order",
            "_investable_priority",
            "_include_priority",
            "_source_priority",
            "_as_of",
        ]
    ).reset_index(drop=True)


def apply_security_history_boundaries(
    prices: pd.DataFrame,
    overrides: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove observations that predate a verified current-security boundary."""
    clean = prices.copy()
    clean.index = pd.to_datetime(clean.index, errors="coerce", utc=True).tz_convert(
        None
    )
    rows: list[dict[str, object]] = []
    if overrides is None or overrides.empty:
        return clean, pd.DataFrame(
            columns=[
                "ticker",
                "current_listing_start_date",
                "observations_before_boundary",
                "history_truncation_applied",
            ]
        )
    for record in overrides.to_dict("records"):
        ticker = normalize_ticker(record.get("ticker", ""))
        start = _timestamp(record.get("current_listing_start_date"))
        continuity = str(record.get("identity_continuity_status", "")).strip()
        before_count = 0
        applied = False
        if ticker in clean and start is not None:
            before = clean.index < start
            before_count = int(clean.loc[before, ticker].notna().sum())
            if before_count and continuity not in VERIFIED_CONTINUITY_STATUSES:
                clean.loc[before, ticker] = np.nan
                applied = True
        rows.append(
            {
                "ticker": ticker,
                "current_listing_start_date": _date_label(start),
                "observations_before_boundary": before_count,
                "history_truncation_applied": bool(applied),
            }
        )
    return clean, pd.DataFrame(rows)


def build_security_identity_audit(
    universe: pd.DataFrame,
    provider_prices: pd.DataFrame,
    valid_prices: pd.DataFrame,
    returns: pd.DataFrame,
    overrides: pd.DataFrame | None = None,
    truncation_report: pd.DataFrame | None = None,
    *,
    minimum_standard_observations: int = 252,
    minimum_forecast_observations: int = 252,
    minimum_walk_forward_observations: int = 252,
) -> pd.DataFrame:
    """Build one auditable security-identity record per canonical ticker."""
    canonical = resolve_security_master_rows(universe)
    override_map = _record_map(overrides)
    truncation_map = _record_map(truncation_report)
    provider = _numeric_frame(provider_prices)
    valid = _numeric_frame(valid_prices)
    return_frame = _numeric_frame(returns)
    tickers = list(
        dict.fromkeys(
            canonical.get("ticker", pd.Series(dtype=str)).astype(str).tolist()
            + list(provider.columns)
            + list(return_frame.columns)
        )
    )
    metadata = (
        canonical.set_index("ticker", drop=False)
        if not canonical.empty
        else pd.DataFrame()
    )
    rows: list[dict[str, object]] = []
    for ticker in tickers:
        row = (
            metadata.loc[ticker]
            if not metadata.empty and ticker in metadata.index
            else pd.Series(dtype=object)
        )
        override = override_map.get(ticker, {})
        current_start = _timestamp(override.get("current_listing_start_date"))
        provider_series = _series(provider, ticker)
        valid_series = _series(valid, ticker)
        return_series = _series(return_frame, ticker)
        provider_start = _first_valid_index(provider_series)
        valid_start = _first_valid_index(valid_series)
        return_start = _first_valid_index(return_series)
        observations = int(return_series.notna().sum())
        pre_listing = (
            int(
                provider_series.loc[provider_series.index < current_start].notna().sum()
            )
            if current_start is not None and not provider_series.empty
            else 0
        )
        reuse_status = (
            str(override.get("ticker_reuse_status", "not_known")).strip() or "not_known"
        )
        continuity_status = str(
            override.get(
                "identity_continuity_status",
                _default_continuity_status(universe, ticker),
            )
        ).strip()
        truncation = truncation_map.get(ticker, {})
        truncation_applied = _as_bool(
            truncation.get("history_truncation_applied", False)
        )
        contamination_status = _contamination_status(
            current_start=current_start,
            pre_listing_observations=pre_listing,
            continuity_status=continuity_status,
            truncation_applied=truncation_applied,
        )
        identity_block = _identity_block_status(
            continuity_status=continuity_status,
            reuse_status=reuse_status,
            contamination_status=contamination_status,
        )
        eligibility_status = _eligibility_status(
            identity_block,
            observations,
            minimum_standard_observations,
        )
        standard_eligible = bool(
            identity_block is None
            and observations >= int(minimum_standard_observations)
        )
        forecast_eligible = bool(
            identity_block is None
            and observations >= int(minimum_forecast_observations)
        )
        walk_forward_eligible = bool(
            identity_block is None
            and observations >= int(minimum_walk_forward_observations)
        )
        exclusion_reason = _exclusion_reason(
            eligibility_status,
            observations,
            minimum_standard_observations,
            continuity_status,
        )
        warning_flags = _warning_flags(
            reuse_status=reuse_status,
            continuity_status=continuity_status,
            observations=observations,
            minimum_standard_observations=minimum_standard_observations,
            contamination_status=contamination_status,
        )
        effective_start = _maximum_timestamp(provider_start, current_start, valid_start)
        rows.append(
            {
                "ticker": ticker,
                "normalized_ticker": ticker,
                "security_name": override.get(
                    "current_security_name", row.get("name", ticker)
                ),
                "issuer_name": override.get(
                    "issuer_name", row.get("name", "unavailable")
                ),
                "listing_exchange": override.get(
                    "listing_exchange", row.get("exchange", "unavailable")
                ),
                "listing_country": override.get(
                    "listing_country", row.get("country", "unavailable")
                ),
                "issuer_country": override.get(
                    "issuer_country", row.get("country", "unavailable")
                ),
                "security_type": override.get(
                    "security_type", row.get("asset_type", "unavailable")
                ),
                "stable_identifier_type": override.get(
                    "stable_identifier_type", "unavailable"
                )
                or "unavailable",
                "stable_identifier": override.get("stable_identifier", "unavailable")
                or "unavailable",
                "current_listing_start_date": _date_label(current_start),
                "provider_history_start_date": _date_label(provider_start),
                "first_valid_price_date": _date_label(valid_start),
                "first_valid_return_date": _date_label(return_start),
                "effective_history_start": _date_label(effective_start),
                "observed_return_count": observations,
                "observations_before_current_listing": pre_listing,
                "ticker_reuse_status": reuse_status,
                "identity_continuity_status": continuity_status,
                "history_contamination_status": contamination_status,
                "history_truncation_applied": truncation_applied,
                "metadata_source": override.get(
                    "metadata_source",
                    row.get("data_provider", row.get("source", "unavailable")),
                ),
                "evidence_url": override.get(
                    "evidence_url", row.get("source_url", "unavailable")
                ),
                "evidence_confidence": override.get("evidence_confidence", "low")
                or "low",
                "eligibility_status": eligibility_status,
                "standard_scoring_eligible": standard_eligible,
                "forecast_eligible": forecast_eligible,
                "walk_forward_eligible": walk_forward_eligible,
                "exclusion_reason": exclusion_reason,
                "warning_flags": warning_flags,
            }
        )
    return pd.DataFrame(rows).reindex(columns=IDENTITY_AUDIT_COLUMNS)


def build_security_history_eligibility(
    identity_audit: pd.DataFrame,
) -> pd.DataFrame:
    """Return the compact downstream eligibility contract."""
    return identity_audit.reindex(columns=HISTORY_ELIGIBILITY_COLUMNS).copy()


def build_feature_history_eligibility(
    returns: pd.DataFrame,
    identity_audit: pd.DataFrame | None = None,
    *,
    minimum_standard_observations: int = 252,
) -> pd.DataFrame:
    """Audit whether each feature has its stated amount of valid history."""
    clean = _numeric_frame(returns)
    identity_map = _record_map(identity_audit)
    rows: list[dict[str, object]] = []
    for ticker in clean.columns:
        observations = int(clean[ticker].notna().sum())
        identity = identity_map.get(normalize_ticker(ticker), {})
        identity_eligible = _as_bool(identity.get("standard_scoring_eligible", True))
        one_month = observations >= 21
        three_month = observations >= 63
        six_month = observations >= 126
        twelve_month = observations >= 252
        standard = bool(
            identity_eligible
            and observations >= int(minimum_standard_observations)
            and twelve_month
        )
        status = str(identity.get("eligibility_status", "")).strip()
        if not status:
            status = "eligible" if standard else "diagnostic_short_history"
        if identity_eligible and not standard:
            status = "diagnostic_short_history"
        reason = (
            "All standard 12-month feature-history requirements are satisfied."
            if standard
            else (
                str(identity.get("exclusion_reason", "")).strip()
                or (
                    f"{observations} valid returns are available; "
                    f"{max(252, int(minimum_standard_observations))} are required "
                    "for the standard composite score."
                )
            )
        )
        rows.append(
            {
                "ticker": normalize_ticker(ticker),
                "observations": observations,
                "1m_eligible": one_month,
                "3m_eligible": three_month,
                "6m_eligible": six_month,
                "12m_eligible": twelve_month,
                "volatility_3m_eligible": three_month,
                "volatility_12m_eligible": twelve_month,
                "sharpe_eligible": twelve_month,
                "sortino_eligible": twelve_month,
                "diversification_eligible": three_month,
                "standard_composite_score_eligible": standard,
                "eligibility_status": status,
                "eligibility_reason": reason,
            }
        )
    return pd.DataFrame(rows).reindex(columns=FEATURE_HISTORY_COLUMNS)


def filter_standard_history_eligible_inputs(
    returns: pd.DataFrame,
    universe: pd.DataFrame,
    feature_eligibility: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Restrict portfolio inputs to canonical, standard-history-eligible assets.

    The feature-history audit is the shared downstream contract for scoring,
    forecasting, covariance estimation and portfolio construction. Assets that
    remain visible as short-history diagnostics must not enter these inputs.
    """
    required = {"ticker", "standard_composite_score_eligible"}
    missing = required.difference(feature_eligibility.columns)
    if missing:
        raise ValueError(
            "Feature-history eligibility is missing required columns: "
            f"{sorted(missing)}"
        )
    canonical = resolve_security_master_rows(universe)
    clean = returns.copy()
    normalized_columns = [normalize_ticker(column) for column in clean.columns]
    if len(normalized_columns) != len(set(normalized_columns)):
        raise ValueError("Returns contain duplicate tickers after normalization.")
    clean.columns = normalized_columns

    eligibility = feature_eligibility.copy()
    eligibility["ticker"] = eligibility["ticker"].map(normalize_ticker)
    duplicated = eligibility["ticker"].duplicated(keep=False)
    if duplicated.any():
        tickers = sorted(eligibility.loc[duplicated, "ticker"].unique())
        raise ValueError(f"Duplicate feature-history eligibility rows: {tickers}")
    eligible_tickers = set(
        eligibility.loc[
            eligibility["standard_composite_score_eligible"].map(_as_bool),
            "ticker",
        ]
    )
    available = [
        ticker
        for ticker in canonical["ticker"].astype(str)
        if ticker in clean and ticker in eligible_tickers
    ]
    excluded = sorted(
        ticker
        for ticker in canonical["ticker"].astype(str)
        if ticker in clean and ticker not in eligible_tickers
    )
    filtered_metadata = canonical.loc[
        canonical["ticker"].astype(str).isin(available)
    ].copy()
    return clean.loc[:, available].copy(), filtered_metadata, excluded


def attach_run_metadata(
    frame: pd.DataFrame,
    metadata: Mapping[str, object] | None,
) -> pd.DataFrame:
    """Attach the shared run identity to a generated tabular artifact."""
    result = frame.copy()
    for column in [
        "run_id",
        "execution_id",
        "data_as_of_date",
        "generated_at",
        "universe_snapshot_id",
        "data_snapshot_id",
        "config_hash",
        "input_fingerprint",
    ]:
        result[column] = str((metadata or {}).get(column, "unavailable"))
    return result


def normalize_ticker(value: object) -> str:
    """Normalize ticker labels without treating them as permanent identifiers."""
    return str(value).strip().upper()


def _numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame.copy()
    clean.index = pd.to_datetime(clean.index, errors="coerce", utc=True).tz_convert(
        None
    )
    clean = clean.loc[clean.index.notna()]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.sort_index()


def _series(frame: pd.DataFrame, ticker: str) -> pd.Series:
    if ticker not in frame:
        return pd.Series(dtype=float, index=frame.index)
    return pd.to_numeric(frame[ticker], errors="coerce")


def _record_map(frame: pd.DataFrame | None) -> dict[str, dict[str, object]]:
    if frame is None or frame.empty or "ticker" not in frame:
        return {}
    return {
        normalize_ticker(record["ticker"]): record
        for record in frame.to_dict("records")
    }


def _included_investable(row: pd.Series) -> bool:
    return bool(
        _as_bool(row.get("include", True))
        and _as_bool(row.get("investable", True))
        and not _as_bool(row.get("benchmark_only", False))
        and not _as_bool(row.get("signal_only", False))
    )


def _as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _timestamp(value: object) -> pd.Timestamp | None:
    if value is None or str(value).strip() in {"", "unavailable", "nan", "NaT"}:
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else pd.Timestamp(parsed).tz_convert(None)


def _first_valid_index(series: pd.Series) -> pd.Timestamp | None:
    valid = series.dropna()
    if valid.empty:
        return None
    return pd.Timestamp(valid.index.min())


def _maximum_timestamp(
    *values: pd.Timestamp | None,
) -> pd.Timestamp | None:
    available = [value for value in values if value is not None]
    return max(available) if available else None


def _date_label(value: pd.Timestamp | None) -> str:
    return value.date().isoformat() if value is not None else "unavailable"


def _default_continuity_status(universe: pd.DataFrame, ticker: str) -> str:
    rows = universe.loc[
        universe.get("ticker", pd.Series(dtype=str)).map(normalize_ticker).eq(ticker)
    ]
    if rows.empty:
        return "manual_review_required"
    security_types = set(rows.get("asset_type", pd.Series(dtype=str)).astype(str))
    currencies = set(rows.get("currency", pd.Series(dtype=str)).astype(str))
    if len(security_types) > 1 or len(currencies) > 1:
        return "manual_review_required"
    return "no_known_conflict_provider_only"


def _contamination_status(
    *,
    current_start: pd.Timestamp | None,
    pre_listing_observations: int,
    continuity_status: str,
    truncation_applied: bool,
) -> str:
    if current_start is None:
        return "not_assessable_without_listing_date"
    if pre_listing_observations == 0:
        return "none_detected"
    if continuity_status in VERIFIED_CONTINUITY_STATUSES:
        return "verified_continuity_preserved"
    return "detected_and_removed" if truncation_applied else "detected_unresolved"


def _identity_block_status(
    *,
    continuity_status: str,
    reuse_status: str,
    contamination_status: str,
) -> str | None:
    if continuity_status == "manual_review_required":
        return "manual_review_required"
    if contamination_status == "detected_unresolved":
        return "blocked_ticker_reuse_contamination"
    if (
        "unresolved" in continuity_status
        or continuity_status == "blocked_identity_uncertain"
    ):
        return "blocked_identity_uncertain"
    if "known_reuse" in reuse_status and not continuity_status.startswith("verified"):
        return "blocked_identity_uncertain"
    return None


def _eligibility_status(
    identity_block: str | None,
    observations: int,
    minimum_standard_observations: int,
) -> str:
    if identity_block:
        return identity_block
    if observations < int(minimum_standard_observations):
        return "diagnostic_short_history"
    return "eligible"


def _exclusion_reason(
    status: str,
    observations: int,
    minimum_standard_observations: int,
    continuity_status: str,
) -> str:
    if status == "eligible":
        return ""
    if status == "diagnostic_short_history":
        return (
            f"{observations} valid returns are available; "
            f"{minimum_standard_observations} are required for standard scoring."
        )
    if status == "blocked_ticker_reuse_contamination":
        return (
            "Ticker-reuse observations precede the verified current listing boundary."
        )
    if status == "blocked_identity_uncertain":
        return f"Security identity continuity is unresolved: {continuity_status}."
    return "Security identity requires manual review."


def _warning_flags(
    *,
    reuse_status: str,
    continuity_status: str,
    observations: int,
    minimum_standard_observations: int,
    contamination_status: str,
) -> str:
    flags: list[str] = []
    if "known_reuse" in reuse_status:
        flags.append("known_ticker_reuse")
    if continuity_status == "no_known_conflict_provider_only":
        flags.append("identity_provider_only")
    if observations < int(minimum_standard_observations):
        flags.append("short_history")
    if contamination_status not in {
        "none_detected",
        "not_assessable_without_listing_date",
    }:
        flags.append(contamination_status)
    return "; ".join(flags) if flags else "none"
