"""Economic exposure interpretation for QuantVerse v2 final model weights."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from project.data_pipeline.security_identity import resolve_security_master_rows

EXPOSURE_COLUMNS = ["bucket", "weight", "asset_count", "interpretation"]

TOP_HOLDINGS_COLUMNS = [
    "model_name",
    "ticker",
    "name",
    "weight",
    "sleeve",
    "region",
    "listing_country",
    "issuer_country",
    "economic_country",
    "currency",
    "listing_currency",
    "exchange",
    "sector",
    "industry",
    "metadata_source",
    "metadata_confidence",
    "metadata_as_of_date",
    "metadata_missing_reason",
    "adr_or_foreign_issuer_flag",
    "risk_contribution_pct",
    "expected_return_contribution",
    "explanation",
]

WARNING_COLUMNS = [
    "warning_type",
    "severity",
    "evidence",
    "interpretation",
    "promotion_blocker",
]

METADATA_QUALITY_COLUMNS = [
    "exposure_metadata_status",
    "sector_coverage_ratio",
    "industry_coverage_ratio",
    "issuer_country_coverage_ratio",
    "economic_country_coverage_ratio",
    "listing_country_coverage_ratio",
    "metadata_confidence_distribution",
    "listing_country_vs_issuer_country_warning",
    "interpretation",
    "promotion_blocker",
]

MISSING_VALUE = "missing"
CORE_METADATA_THRESHOLD = 0.95
PARTIAL_METADATA_THRESHOLD = 0.50

YFINANCE_PROFILE_KEYS = [
    "country",
    "sector",
    "industry",
    "exchange",
    "currency",
    "quoteType",
    "longName",
]

KNOWN_FOREIGN_ISSUER_TICKERS = {
    "UBS",
    "MUFG",
    "RY",
    "TD",
    "AZN",
    "HSBC",
    "TSM",
    "SAP",
    "SHEL",
    "TM",
    "NVS",
    "SAN",
    "TTE",
    "BHP",
    "NVO",
    "BABA",
}


def build_exposure_analysis(
    weights: pd.DataFrame,
    universe: pd.DataFrame,
    *,
    final_model: str,
    metadata_as_of_date: str,
    risk_contributions: pd.DataFrame | None = None,
    forecasts: pd.DataFrame | None = None,
    concentration_threshold: float = 0.50,
    metadata_cache_dir: str | Path | None = None,
    allow_yfinance_metadata: bool = False,
) -> dict[str, pd.DataFrame]:
    """Build region, country, currency, sleeve, sector and holding explanations."""
    metadata_as_of_date = _validated_metadata_as_of_date(metadata_as_of_date)
    final_weights = _final_weights(weights, final_model)
    metadata = _metadata(universe)
    enriched = final_weights.merge(metadata, on="ticker", how="left")
    enriched["name"] = enriched["name"].fillna(enriched["ticker"])
    enriched = _enrich_exposure_metadata(
        enriched,
        metadata_cache_dir=metadata_cache_dir,
        allow_yfinance_metadata=allow_yfinance_metadata,
        metadata_as_of_date=metadata_as_of_date,
    )
    for column in [
        "sleeve",
        "region",
        "listing_country",
        "issuer_country",
        "economic_country",
        "currency",
        "listing_currency",
        "exchange",
        "sector",
        "industry",
    ]:
        if column not in enriched:
            enriched[column] = MISSING_VALUE
        enriched[column] = enriched[column].fillna(MISSING_VALUE).astype(str)
    enriched = _merge_risk_contribution(enriched, risk_contributions, final_model)
    enriched = _merge_forecast_contribution(enriched, forecasts)
    return {
        "region": _group_exposure(enriched, "region"),
        "country": _group_exposure(enriched, "listing_country"),
        "listing_country": _group_exposure(enriched, "listing_country"),
        "issuer_country": _group_exposure(enriched, "issuer_country"),
        "economic_country": _group_exposure(enriched, "economic_country"),
        "currency": _group_exposure(enriched, "currency"),
        "exchange": _group_exposure(enriched, "exchange"),
        "sleeve": _group_exposure(enriched, "sleeve"),
        "sector": _group_exposure(enriched, "sector"),
        "industry": _group_exposure(enriched, "industry"),
        "top_holdings": _top_holdings(enriched, final_model),
        "warnings": _warnings(enriched, concentration_threshold),
        "metadata_quality": _metadata_quality(enriched),
    }


def write_exposure_outputs(
    exposure: dict[str, pd.DataFrame],
    output_dir: str | Path,
) -> None:
    """Write exposure outputs with stable file names."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    exposure["region"].to_csv(path / "global_region_exposure.csv", index=False)
    exposure["country"].to_csv(path / "global_country_exposure.csv", index=False)
    exposure["listing_country"].to_csv(
        path / "global_listing_country_exposure.csv", index=False
    )
    exposure["issuer_country"].to_csv(
        path / "global_issuer_country_exposure.csv", index=False
    )
    exposure["economic_country"].to_csv(
        path / "global_economic_country_exposure.csv", index=False
    )
    exposure["currency"].to_csv(path / "global_currency_exposure.csv", index=False)
    exposure["exchange"].to_csv(path / "global_exchange_exposure.csv", index=False)
    exposure["sleeve"].to_csv(path / "global_sleeve_exposure.csv", index=False)
    exposure["sector"].to_csv(path / "global_sector_exposure.csv", index=False)
    exposure["industry"].to_csv(path / "global_industry_exposure.csv", index=False)
    exposure["top_holdings"].to_csv(
        path / "global_top_holdings_explanation.csv", index=False
    )
    exposure["warnings"].to_csv(path / "global_exposure_warnings.csv", index=False)
    exposure["metadata_quality"].to_csv(
        path / "global_exposure_metadata_quality.csv", index=False
    )


def _final_weights(weights: pd.DataFrame, final_model: str) -> pd.DataFrame:
    if weights.empty or not {"ticker", "weight"}.issubset(weights.columns):
        raise ValueError("Final-model exposure requires non-empty ticker/weight data.")
    frame = weights.copy()
    if "model_name" in frame:
        selected = frame.loc[frame["model_name"].astype(str).eq(str(final_model))]
        if selected.empty:
            raise ValueError(
                f"Final model {final_model!r} is missing from the weight artifact."
            )
        frame = selected
    frame = frame[["ticker", "weight"]].copy()
    frame["ticker"] = frame["ticker"].astype(str)
    frame["weight"] = pd.to_numeric(frame["weight"], errors="coerce")
    if frame["weight"].isna().any() or not np.isfinite(frame["weight"]).all():
        raise ValueError("Final-model exposure weights must be finite numeric values.")
    if (frame["weight"] < -1e-12).any():
        raise ValueError("Final-model exposure weights must be long-only.")
    total = float(frame["weight"].sum())
    if not np.isclose(total, 1.0, atol=1e-6, rtol=0.0):
        raise ValueError(
            f"Final-model exposure weights must sum to 1.0; observed {total:.12g}."
        )
    return frame


def _metadata(universe: pd.DataFrame) -> pd.DataFrame:
    if universe.empty or "ticker" not in universe:
        return pd.DataFrame(
            columns=[
                "ticker",
                "name",
                "sleeve",
                "region",
                "listing_country",
                "issuer_country",
                "economic_country",
                "currency",
                "listing_currency",
                "exchange",
                "sector",
                "industry",
                "metadata_source",
                "metadata_confidence",
                "metadata_as_of_date",
                "metadata_missing_reason",
            ]
        )
    frame = resolve_security_master_rows(universe)
    frame["ticker"] = frame["ticker"].astype(str)
    for column in ["name", "sleeve", "region", "country", "currency", "sector"]:
        _ensure_column(frame, column)
    for column in [
        "listing_country",
        "issuer_country",
        "economic_country",
        "listing_currency",
        "exchange",
        "industry",
        "metadata_source",
        "metadata_confidence",
        "metadata_as_of_date",
        "metadata_missing_reason",
    ]:
        _ensure_column(frame, column)
    frame["listing_country"] = _coalesce_text(
        frame["listing_country"], frame["country"]
    )
    frame["listing_currency"] = _coalesce_text(
        frame["listing_currency"], frame["currency"]
    )
    frame["issuer_country"] = _clean_text_series(frame["issuer_country"])
    frame["economic_country"] = _clean_text_series(frame["economic_country"])
    frame["sector"] = _clean_text_series(frame["sector"])
    frame["industry"] = _clean_text_series(frame["industry"])
    frame["metadata_source"] = _coalesce_text(
        frame["metadata_source"],
        _coalesce_text(frame.get("data_provider"), frame.get("source")),
    )
    frame["metadata_confidence"] = _clean_text_series(frame["metadata_confidence"])
    frame["metadata_as_of_date"] = _coalesce_text(
        frame["metadata_as_of_date"], frame.get("as_of_date")
    )
    frame["metadata_missing_reason"] = _clean_text_series(
        frame["metadata_missing_reason"]
    )
    return frame[
        [
            "ticker",
            "name",
            "sleeve",
            "region",
            "listing_country",
            "issuer_country",
            "economic_country",
            "currency",
            "listing_currency",
            "exchange",
            "sector",
            "industry",
            "metadata_source",
            "metadata_confidence",
            "metadata_as_of_date",
            "metadata_missing_reason",
        ]
    ]


def _enrich_exposure_metadata(
    enriched: pd.DataFrame,
    *,
    metadata_cache_dir: str | Path | None,
    allow_yfinance_metadata: bool,
    metadata_as_of_date: str,
) -> pd.DataFrame:
    frame = enriched.copy()
    for column in [
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
        "metadata_missing_reason",
    ]:
        _ensure_column(frame, column)
        frame[column] = _clean_text_series(frame[column])
    frame["metadata_as_of_date"] = frame["metadata_as_of_date"].where(
        frame["metadata_as_of_date"].ne(MISSING_VALUE),
        metadata_as_of_date,
    )

    cache_dir = Path(metadata_cache_dir) if metadata_cache_dir is not None else None
    enriched_rows = []
    for _, row in frame.iterrows():
        ticker = str(row.get("ticker", "")).strip()
        profile = (
            _yfinance_profile(ticker, cache_dir)
            if allow_yfinance_metadata and ticker
            else {}
        )
        updated = row.to_dict()
        used_provider_fields: list[str] = []
        provider_country = _clean_text(profile.get("country"))
        provider_sector = _clean_text(profile.get("sector"))
        provider_industry = _clean_text(profile.get("industry"))
        provider_exchange = _clean_text(profile.get("exchange"))
        provider_currency = _clean_text(profile.get("currency"))

        if _is_missing(updated.get("issuer_country")) and not _is_missing(
            provider_country
        ):
            updated["issuer_country"] = provider_country
            used_provider_fields.append("issuer_country")
        if _is_missing(updated.get("sector")) and not _is_missing(provider_sector):
            updated["sector"] = provider_sector
            used_provider_fields.append("sector")
        if _is_missing(updated.get("industry")) and not _is_missing(provider_industry):
            updated["industry"] = provider_industry
            used_provider_fields.append("industry")
        if _is_missing(updated.get("exchange")) and not _is_missing(provider_exchange):
            updated["exchange"] = provider_exchange
            used_provider_fields.append("exchange")
        if _is_missing(updated.get("listing_currency")) and not _is_missing(
            provider_currency
        ):
            updated["listing_currency"] = provider_currency
            used_provider_fields.append("listing_currency")

        updated["adr_or_foreign_issuer_flag"] = _foreign_issuer_flag(updated)
        missing = _missing_metadata_reasons(updated)
        updated["metadata_missing_reason"] = "; ".join(missing) if missing else "none"
        if used_provider_fields:
            updated["metadata_source"] = "yfinance_profile_cache"
            updated["metadata_confidence"] = (
                "medium"
                if not _is_missing(updated.get("issuer_country"))
                and not _is_missing(updated.get("sector"))
                else "low"
            )
            updated["metadata_as_of_date"] = metadata_as_of_date
        elif _is_missing(updated.get("metadata_confidence")):
            updated["metadata_confidence"] = (
                "low" if missing else "medium_from_universe_source"
            )
        enriched_rows.append(updated)
    return pd.DataFrame(enriched_rows)


def _yfinance_profile(ticker: str, cache_dir: Path | None) -> dict[str, object]:
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{_safe_cache_name(ticker)}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).get_info()
    except Exception:
        info = {}
    profile = {key: info.get(key) for key in YFINANCE_PROFILE_KEYS if info.get(key)}
    if cache_dir is not None and profile:
        path.write_text(json.dumps(profile, indent=2, default=str), encoding="utf-8")
    return profile


def _safe_cache_name(ticker: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in ticker)


def _ensure_column(frame: pd.DataFrame, column: str) -> None:
    if column not in frame:
        frame[column] = MISSING_VALUE


def _coalesce_text(
    primary: pd.Series | None,
    fallback: pd.Series | None,
) -> pd.Series:
    if primary is None:
        if fallback is None:
            return pd.Series(dtype=object)
        return _clean_text_series(fallback)
    clean_primary = _clean_text_series(primary)
    if fallback is None:
        return clean_primary
    clean_fallback = _clean_text_series(fallback)
    return clean_primary.where(clean_primary.ne(MISSING_VALUE), clean_fallback)


def _clean_text_series(values: pd.Series) -> pd.Series:
    clean = values.fillna(MISSING_VALUE).astype(str).str.strip()
    return clean.where(clean.ne("") & clean.str.lower().ne("nan"), MISSING_VALUE)


def _clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return MISSING_VALUE
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return MISSING_VALUE
    return text


def _validated_metadata_as_of_date(value: str) -> str:
    clean = _clean_text(value)
    if clean == MISSING_VALUE:
        raise ValueError("metadata_as_of_date must be supplied explicitly.")
    try:
        return date.fromisoformat(clean).isoformat()
    except ValueError as exc:
        raise ValueError("metadata_as_of_date must use ISO YYYY-MM-DD format.") from exc


def _is_missing(value: object) -> bool:
    return _clean_text(value).lower() == MISSING_VALUE


def _foreign_issuer_flag(row: dict[str, object]) -> bool:
    ticker = str(row.get("ticker", "")).strip().upper()
    listing = _clean_text(row.get("listing_country"))
    issuer = _clean_text(row.get("issuer_country"))
    return bool(
        (not _is_missing(issuer) and not _is_missing(listing) and issuer != listing)
        or (ticker in KNOWN_FOREIGN_ISSUER_TICKERS and _is_missing(issuer))
    )


def _missing_metadata_reasons(row: dict[str, object]) -> list[str]:
    reasons = []
    for column in ["issuer_country", "economic_country", "sector", "industry"]:
        if _is_missing(row.get(column)):
            reasons.append(f"{column}_missing")
    ticker = str(row.get("ticker", "")).strip().upper()
    if ticker in KNOWN_FOREIGN_ISSUER_TICKERS and _is_missing(
        row.get("issuer_country")
    ):
        reasons.append("foreign_issuer_review_required")
    return reasons


def _merge_risk_contribution(
    enriched: pd.DataFrame,
    risk_contributions: pd.DataFrame | None,
    final_model: str,
) -> pd.DataFrame:
    if (
        risk_contributions is None
        or risk_contributions.empty
        or not {"model_name", "ticker", "risk_contribution_pct"}.issubset(
            risk_contributions.columns
        )
    ):
        enriched["risk_contribution_pct"] = np.nan
        return enriched
    frame = risk_contributions.loc[
        risk_contributions["model_name"].astype(str).eq(str(final_model))
    ].copy()
    if frame.empty:
        enriched["risk_contribution_pct"] = np.nan
        return enriched
    frame["ticker"] = frame["ticker"].astype(str)
    frame["risk_contribution_pct"] = pd.to_numeric(
        frame["risk_contribution_pct"], errors="coerce"
    )
    return enriched.merge(
        frame[["ticker", "risk_contribution_pct"]], on="ticker", how="left"
    )


def _merge_forecast_contribution(
    enriched: pd.DataFrame,
    forecasts: pd.DataFrame | None,
) -> pd.DataFrame:
    if (
        forecasts is None
        or forecasts.empty
        or not {"ticker", "ensemble_expected_return"}.issubset(forecasts.columns)
    ):
        enriched["expected_return_contribution"] = np.nan
        return enriched
    frame = forecasts.copy()
    frame["ticker"] = frame["ticker"].astype(str)
    if "horizon" in frame and frame["horizon"].astype(str).eq("12M").any():
        frame = frame.loc[frame["horizon"].astype(str).eq("12M")]
    expected = (
        frame.drop_duplicates("ticker")
        .set_index("ticker")["ensemble_expected_return"]
        .astype(float)
    )
    enriched["expected_return_contribution"] = (
        enriched["ticker"].map(expected).astype(float) * enriched["weight"]
    )
    return enriched


def _group_exposure(enriched: pd.DataFrame, column: str) -> pd.DataFrame:
    if enriched.empty:
        return pd.DataFrame(columns=EXPOSURE_COLUMNS)
    grouped = enriched.groupby(column, dropna=False).agg(
        weight=("weight", "sum"),
        asset_count=("ticker", "nunique"),
    )
    grouped = grouped.reset_index().rename(columns={column: "bucket"})
    grouped["interpretation"] = grouped["weight"].map(
        lambda weight: (
            "High exposure; review concentration."
            if float(weight) >= 0.50
            else "Diversified exposure bucket."
        )
    )
    return grouped[EXPOSURE_COLUMNS].sort_values("weight", ascending=False)


def _top_holdings(enriched: pd.DataFrame, final_model: str) -> pd.DataFrame:
    if enriched.empty:
        return pd.DataFrame(columns=TOP_HOLDINGS_COLUMNS)
    frame = enriched.sort_values("weight", ascending=False).copy()
    frame["model_name"] = final_model
    frame["explanation"] = frame.apply(
        lambda row: (
            f"{row['ticker']} weight is {float(row['weight']):.4f}; "
            f"sleeve={row['sleeve']}, region={row['region']}, "
            f"listing_country={row['listing_country']}, "
            f"issuer_country={row['issuer_country']}, "
            f"economic_country={row['economic_country']}, "
            f"sector={row['sector']}, industry={row['industry']}, "
            f"risk contribution={_format_optional(row.get('risk_contribution_pct'))}."
        ),
        axis=1,
    )
    return frame[TOP_HOLDINGS_COLUMNS]


def _warnings(
    enriched: pd.DataFrame,
    concentration_threshold: float,
) -> pd.DataFrame:
    warnings: list[dict[str, object]] = []
    if enriched.empty:
        return pd.DataFrame(
            [
                {
                    "warning_type": "missing_weights",
                    "severity": "high",
                    "evidence": "No final weights available.",
                    "interpretation": "Exposure analysis cannot support a model decision.",
                    "promotion_blocker": True,
                }
            ],
            columns=WARNING_COLUMNS,
        )
    for column in [
        "sleeve",
        "region",
        "listing_country",
        "issuer_country",
        "economic_country",
        "currency",
        "exchange",
        "sector",
        "industry",
    ]:
        exposures = _group_exposure(enriched, column)
        if exposures.empty:
            continue
        top = exposures.iloc[0]
        if float(top["weight"]) >= concentration_threshold:
            warnings.append(
                {
                    "warning_type": f"{column}_concentration",
                    "severity": "medium",
                    "evidence": f"{top['bucket']} weight={float(top['weight']):.4f}",
                    "interpretation": (
                        "Concentration is economically interpretable but must be "
                        "reviewed before any stronger claim."
                    ),
                    "promotion_blocker": False,
                }
            )
    foreign_issuer_flags = (
        enriched["adr_or_foreign_issuer_flag"].map(
            lambda value: str(value).lower() == "true"
        )
        if "adr_or_foreign_issuer_flag" in enriched
        else pd.Series(False, index=enriched.index)
    )
    if bool(foreign_issuer_flags.any()):
        count = int(foreign_issuer_flags.sum())
        warnings.append(
            {
                "warning_type": "foreign_issuer_listing_country_mismatch",
                "severity": "medium",
                "evidence": f"foreign_issuer_or_adr_like_holdings={count}",
                "interpretation": (
                    "Some selected tickers trade in a listing venue that differs from "
                    "issuer domicile. Listing-country exposure must not be presented "
                    "as issuer-country or economic-country exposure."
                ),
                "promotion_blocker": False,
            }
        )
    metadata = _metadata_quality(enriched)
    if not metadata.empty:
        row = metadata.iloc[0]
        if str(row["exposure_metadata_status"]) != "passed":
            warnings.append(
                {
                    "warning_type": "exposure_metadata_incomplete",
                    "severity": "high",
                    "evidence": (
                        f"sector_coverage_ratio={row['sector_coverage_ratio']}; "
                        f"industry_coverage_ratio={row['industry_coverage_ratio']}; "
                        f"issuer_country_coverage_ratio={row['issuer_country_coverage_ratio']}; "
                        f"economic_country_coverage_ratio={row['economic_country_coverage_ratio']}"
                    ),
                    "interpretation": str(row["interpretation"]),
                    "promotion_blocker": bool(row["promotion_blocker"]),
                }
            )
    if not warnings:
        warnings.append(
            {
                "warning_type": "none",
                "severity": "low",
                "evidence": "No exposure bucket exceeded the configured threshold.",
                "interpretation": "Exposure concentration did not trigger this audit.",
                "promotion_blocker": False,
            }
        )
    return pd.DataFrame(warnings, columns=WARNING_COLUMNS)


def _metadata_quality(enriched: pd.DataFrame) -> pd.DataFrame:
    if enriched.empty:
        return pd.DataFrame(
            [
                {
                    "exposure_metadata_status": "diagnostic_metadata_incomplete",
                    "sector_coverage_ratio": 0.0,
                    "industry_coverage_ratio": 0.0,
                    "issuer_country_coverage_ratio": 0.0,
                    "economic_country_coverage_ratio": 0.0,
                    "listing_country_coverage_ratio": 0.0,
                    "metadata_confidence_distribution": "{}",
                    "listing_country_vs_issuer_country_warning": True,
                    "interpretation": "Exposure metadata cannot be audited without final holdings.",
                    "promotion_blocker": True,
                }
            ],
            columns=METADATA_QUALITY_COLUMNS,
        )

    def coverage(column: str | None) -> float:
        if column is None or column not in enriched:
            return 0.0
        values = enriched[column].fillna("missing").astype(str).str.strip()
        valid = values.ne("") & values.str.lower().ne("missing")
        weights = pd.to_numeric(enriched["weight"], errors="coerce")
        if weights.isna().any() or not np.isfinite(weights.to_numpy(dtype=float)).all():
            return 0.0
        total = float(weights.sum())
        if total <= 0:
            return 0.0
        return float(weights.loc[valid].sum() / total)

    sector_coverage = coverage("sector")
    industry_coverage = coverage("industry")
    issuer_coverage = coverage("issuer_country")
    economic_coverage = coverage("economic_country")
    listing_coverage = coverage("listing_country")
    confidence_distribution = _metadata_confidence_distribution(enriched)
    if (
        sector_coverage >= CORE_METADATA_THRESHOLD
        and issuer_coverage >= CORE_METADATA_THRESHOLD
        and industry_coverage >= PARTIAL_METADATA_THRESHOLD
    ):
        status = (
            "passed"
            if economic_coverage >= CORE_METADATA_THRESHOLD
            else "passed_with_metadata_warning"
        )
    elif (
        sector_coverage >= PARTIAL_METADATA_THRESHOLD
        and issuer_coverage >= PARTIAL_METADATA_THRESHOLD
    ):
        status = "passed_with_metadata_warning"
    else:
        status = "diagnostic_metadata_incomplete"
    issuer_warning = issuer_coverage < CORE_METADATA_THRESHOLD
    if "listing_country" in enriched and "issuer_country" in enriched:
        comparable = enriched.loc[
            ~enriched["listing_country"].map(_is_missing)
            & ~enriched["issuer_country"].map(_is_missing)
        ]
        issuer_warning = issuer_warning or bool(
            not comparable.empty
            and not comparable["listing_country"]
            .astype(str)
            .equals(comparable["issuer_country"].astype(str))
        )
    if status == "passed":
        interpretation = (
            "Sector, industry, issuer-country and economic-country metadata are "
            "sufficiently covered for separated exposure interpretation."
        )
        blocker = False
    elif status == "passed_with_metadata_warning":
        interpretation = (
            "Issuer-country and sector metadata are materially usable, but economic "
            "country or industry coverage is incomplete. Economic exposure remains "
            "diagnostic where unavailable and must not be inferred silently."
        )
        blocker = economic_coverage < PARTIAL_METADATA_THRESHOLD
    else:
        interpretation = (
            "Exposure analysis is diagnostic only because sector or issuer-country "
            "metadata coverage is incomplete. Listing-country exposure must not be "
            "presented as issuer/economic exposure."
        )
        blocker = True
    return pd.DataFrame(
        [
            {
                "exposure_metadata_status": status,
                "sector_coverage_ratio": sector_coverage,
                "industry_coverage_ratio": industry_coverage,
                "issuer_country_coverage_ratio": issuer_coverage,
                "economic_country_coverage_ratio": economic_coverage,
                "listing_country_coverage_ratio": listing_coverage,
                "metadata_confidence_distribution": json.dumps(
                    confidence_distribution, sort_keys=True
                ),
                "listing_country_vs_issuer_country_warning": bool(issuer_warning),
                "interpretation": interpretation,
                "promotion_blocker": blocker,
            }
        ],
        columns=METADATA_QUALITY_COLUMNS,
    )


def _metadata_confidence_distribution(enriched: pd.DataFrame) -> dict[str, float]:
    if "metadata_confidence" not in enriched or enriched.empty:
        return {}
    weights = pd.to_numeric(enriched["weight"], errors="coerce")
    if weights.isna().any() or not np.isfinite(weights.to_numpy(dtype=float)).all():
        return {}
    total = float(weights.sum())
    if total <= 0:
        return {}
    confidence = _clean_text_series(enriched["metadata_confidence"])
    result: dict[str, float] = {}
    for bucket, bucket_weights in weights.groupby(confidence):
        result[str(bucket)] = float(bucket_weights.sum() / total)
    return result


def _format_optional(value: object) -> str:
    try:
        if pd.isna(value):
            return "not available"
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "not available"
