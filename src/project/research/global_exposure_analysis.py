"""Economic exposure interpretation for QuantVerse v2 final model weights."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

EXPOSURE_COLUMNS = ["bucket", "weight", "asset_count", "interpretation"]

TOP_HOLDINGS_COLUMNS = [
    "model_name",
    "ticker",
    "name",
    "weight",
    "sleeve",
    "region",
    "country",
    "currency",
    "sector",
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
    "issuer_country_coverage_ratio",
    "listing_country_coverage_ratio",
    "listing_country_vs_issuer_country_warning",
    "interpretation",
    "promotion_blocker",
]


def build_exposure_analysis(
    weights: pd.DataFrame,
    universe: pd.DataFrame,
    *,
    final_model: str,
    risk_contributions: pd.DataFrame | None = None,
    forecasts: pd.DataFrame | None = None,
    concentration_threshold: float = 0.50,
) -> dict[str, pd.DataFrame]:
    """Build region, country, currency, sleeve, sector and holding explanations."""
    final_weights = _final_weights(weights, final_model)
    metadata = _metadata(universe)
    enriched = final_weights.merge(metadata, on="ticker", how="left")
    enriched["name"] = enriched["name"].fillna(enriched["ticker"])
    for column in ["sleeve", "region", "country", "currency", "sector"]:
        if column not in enriched:
            enriched[column] = "missing"
        enriched[column] = enriched[column].fillna("missing").astype(str)
    enriched = _merge_risk_contribution(enriched, risk_contributions, final_model)
    enriched = _merge_forecast_contribution(enriched, forecasts)
    return {
        "region": _group_exposure(enriched, "region"),
        "country": _group_exposure(enriched, "country"),
        "currency": _group_exposure(enriched, "currency"),
        "sleeve": _group_exposure(enriched, "sleeve"),
        "sector": _group_exposure(enriched, "sector"),
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
    exposure["currency"].to_csv(path / "global_currency_exposure.csv", index=False)
    exposure["sleeve"].to_csv(path / "global_sleeve_exposure.csv", index=False)
    exposure["sector"].to_csv(path / "global_sector_exposure.csv", index=False)
    exposure["top_holdings"].to_csv(
        path / "global_top_holdings_explanation.csv", index=False
    )
    exposure["warnings"].to_csv(path / "global_exposure_warnings.csv", index=False)
    exposure["metadata_quality"].to_csv(
        path / "global_exposure_metadata_quality.csv", index=False
    )


def _final_weights(weights: pd.DataFrame, final_model: str) -> pd.DataFrame:
    if weights.empty or not {"ticker", "weight"}.issubset(weights.columns):
        return pd.DataFrame(columns=["ticker", "weight"])
    frame = weights.copy()
    if "model_name" in frame:
        selected = frame.loc[frame["model_name"].astype(str).eq(str(final_model))]
        if selected.empty:
            selected = frame.loc[frame["model_name"].astype(str).eq("Equal Weight")]
        frame = selected if not selected.empty else frame
    frame = frame[["ticker", "weight"]].copy()
    frame["ticker"] = frame["ticker"].astype(str)
    frame["weight"] = pd.to_numeric(frame["weight"], errors="coerce").fillna(0.0)
    total = float(frame["weight"].sum())
    if total > 0:
        frame["weight"] = frame["weight"] / total
    return frame


def _metadata(universe: pd.DataFrame) -> pd.DataFrame:
    if universe.empty or "ticker" not in universe:
        return pd.DataFrame(
            columns=[
                "ticker",
                "name",
                "sleeve",
                "region",
                "country",
                "currency",
                "sector",
            ]
        )
    frame = universe.copy()
    frame["ticker"] = frame["ticker"].astype(str)
    for column in ["name", "sleeve", "region", "country", "currency", "sector"]:
        if column not in frame:
            frame[column] = "missing"
    optional = [
        column
        for column in ["issuer_country", "economic_country"]
        if column in frame.columns
    ]
    return frame.drop_duplicates("ticker", keep="first")[
        ["ticker", "name", "sleeve", "region", "country", "currency", "sector"]
        + optional
    ]


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
    for column in ["sleeve", "region", "country", "currency", "sector"]:
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
    metadata = _metadata_quality(enriched)
    if not metadata.empty:
        row = metadata.iloc[0]
        if str(row["exposure_metadata_status"]) != "complete":
            warnings.append(
                {
                    "warning_type": "exposure_metadata_incomplete",
                    "severity": "high",
                    "evidence": (
                        f"sector_coverage_ratio={row['sector_coverage_ratio']}; "
                        f"issuer_country_coverage_ratio={row['issuer_country_coverage_ratio']}"
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
                    "issuer_country_coverage_ratio": 0.0,
                    "listing_country_coverage_ratio": 0.0,
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
        weights = pd.to_numeric(enriched["weight"], errors="coerce").fillna(0.0)
        total = float(weights.sum())
        if total <= 0:
            return 0.0
        return float(weights.loc[valid].sum() / total)

    issuer_column = next(
        (
            column
            for column in ["issuer_country", "economic_country"]
            if column in enriched
        ),
        None,
    )
    sector_coverage = coverage("sector")
    issuer_coverage = coverage(issuer_column)
    listing_coverage = coverage("country")
    status = (
        "complete"
        if sector_coverage >= 0.95 and issuer_coverage >= 0.95
        else "diagnostic_metadata_incomplete"
    )
    issuer_warning = issuer_coverage < 0.95 or issuer_column is None
    if issuer_column is not None and "country" in enriched:
        issuer_warning = issuer_warning or not enriched["country"].astype(str).equals(
            enriched[issuer_column].astype(str)
        )
    if status == "complete":
        interpretation = (
            "Sector and issuer-country exposure metadata are sufficiently covered."
        )
        blocker = False
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
                "issuer_country_coverage_ratio": issuer_coverage,
                "listing_country_coverage_ratio": listing_coverage,
                "listing_country_vs_issuer_country_warning": bool(issuer_warning),
                "interpretation": interpretation,
                "promotion_blocker": blocker,
            }
        ],
        columns=METADATA_QUALITY_COLUMNS,
    )


def _format_optional(value: object) -> str:
    try:
        if pd.isna(value):
            return "not available"
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "not available"
