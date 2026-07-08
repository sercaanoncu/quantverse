"""Visual portfolio analytics tables for QuantVerse v2.

This module produces chart-ready evidence tables only. It does not create new
portfolio models, change model selection, or make investment recommendations.
Each output carries the methodology fields required to audit what was computed,
why it is meaningful, and when it becomes invalid.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_numerical_integrity import portfolio_return_series

VISUAL_ANALYTICS_FILES = {
    "summary": "quantverse_v2_visual_analytics_summary.csv",
    "equity_curve": "quantverse_v2_visual_equity_curve.csv",
    "drawdown_curve": "quantverse_v2_visual_drawdown_curve.csv",
    "model_risk_return": "quantverse_v2_visual_model_risk_return.csv",
    "forecast_error": "quantverse_v2_visual_forecast_error.csv",
    "random_benchmark": "quantverse_v2_visual_random_benchmark.csv",
    "exposure": "quantverse_v2_visual_exposure.csv",
    "top_holdings": "quantverse_v2_visual_top_holdings.csv",
    "validation": "quantverse_v2_visual_validation.csv",
}

METADATA_COLUMNS = [
    "formula_method",
    "source_basis",
    "why_valid",
    "limitation",
    "invalidation_condition",
    "tested_by",
    "output_status",
]


def build_visual_analytics_outputs(
    processed_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Build chart-ready visual analytics outputs from existing v2 evidence."""
    processed = Path(processed_dir)
    output = Path(output_dir) if output_dir is not None else processed
    output.mkdir(parents=True, exist_ok=True)

    decision = _read_json(processed / "global_final_model_decision.json")
    summary_json = _read_json(processed / "quantverse_v2_demo_summary.json")
    final_model = str(
        decision.get("final_selected_model")
        or summary_json.get("final_selected_model")
        or "Equal Weight"
    )
    returns = _read_returns(processed / "global_security_simple_returns_usd.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    risk = _read_csv(processed / "global_portfolio_risk_report.csv")
    walk = _read_csv(processed / "global_walk_forward_model_comparison.csv")
    random_distribution = _read_csv(
        processed / "global_random_portfolio_distribution.csv"
    )
    random_percentiles = _read_csv(
        processed / "global_random_portfolio_percentile_report.csv"
    )
    forecast = _read_csv(processed / "global_forecast_validation_by_horizon.csv")

    final_weights = _weights_for_model(weights, final_model)
    final_returns = portfolio_return_series(returns, final_weights)

    equity_curve = build_equity_curve(final_returns, final_model=final_model)
    drawdown_curve = build_drawdown_curve(equity_curve, final_model=final_model)
    model_risk_return = build_model_risk_return_chart(
        risk, walk, final_model=final_model
    )
    forecast_error = build_forecast_error_chart(forecast)
    random_benchmark = build_random_benchmark_chart(
        random_distribution,
        random_percentiles,
        model_risk_return,
        final_model=final_model,
    )
    exposure = build_exposure_chart(processed)
    top_holdings = build_top_holdings_chart(weights, final_model=final_model)
    validation = validate_visual_analytics_frames(
        {
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve,
            "model_risk_return": model_risk_return,
            "forecast_error": forecast_error,
            "random_benchmark": random_benchmark,
            "exposure": exposure,
            "top_holdings": top_holdings,
        }
    )
    summary = build_visual_summary(
        final_model=final_model,
        validation=validation,
        frames={
            "equity_curve": equity_curve,
            "drawdown_curve": drawdown_curve,
            "model_risk_return": model_risk_return,
            "forecast_error": forecast_error,
            "random_benchmark": random_benchmark,
            "exposure": exposure,
            "top_holdings": top_holdings,
        },
    )

    outputs = {
        "summary": summary,
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "model_risk_return": model_risk_return,
        "forecast_error": forecast_error,
        "random_benchmark": random_benchmark,
        "exposure": exposure,
        "top_holdings": top_holdings,
        "validation": validation,
    }
    for key, frame in outputs.items():
        frame.to_csv(output / VISUAL_ANALYTICS_FILES[key], index=False)
    return outputs


def build_equity_curve(
    returns: pd.Series,
    *,
    final_model: str,
) -> pd.DataFrame:
    """Build a final-model equity curve starting at 1.0."""
    clean = pd.Series(returns, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        frame = pd.DataFrame(
            columns=["date", "model_name", "daily_return", "equity_curve"]
        )
    else:
        wealth = (1.0 + clean).cumprod()
        wealth = wealth / float(wealth.iloc[0])
        frame = pd.DataFrame(
            {
                "date": clean.index,
                "model_name": final_model,
                "daily_return": clean.to_numpy(dtype=float),
                "equity_curve": wealth.to_numpy(dtype=float),
            }
        )
    return _with_metadata(
        frame,
        formula_method="equity_curve_t = prod(1 + daily_simple_return) normalized so first point equals 1.0",
        source_basis="Portfolio theory and financial statistics: simple returns compound through cumulative wealth.",
        why_valid="A one-period simple-return portfolio aggregates linearly by weights and compounds multiplicatively through time.",
        limitation="Current-universe public data; not point-in-time institutional performance.",
        invalidation_condition="Invalid if first equity_curve is not 1.0, returns are missing, or returns are not daily simple returns.",
        tested_by="tests/test_visual_analytics_outputs.py::test_equity_curve_starts_at_one_and_drawdown_non_positive",
        output_status="diagnostic",
    )


def build_drawdown_curve(
    equity_curve: pd.DataFrame,
    *,
    final_model: str,
) -> pd.DataFrame:
    """Build a drawdown curve from an equity curve."""
    if equity_curve.empty or "equity_curve" not in equity_curve:
        frame = pd.DataFrame(columns=["date", "model_name", "equity_curve", "drawdown"])
    else:
        wealth = pd.to_numeric(equity_curve["equity_curve"], errors="coerce")
        running_max = wealth.cummax()
        drawdown = wealth / running_max - 1.0
        frame = pd.DataFrame(
            {
                "date": equity_curve["date"],
                "model_name": final_model,
                "equity_curve": wealth,
                "drawdown": drawdown.clip(upper=0.0),
            }
        )
    return _with_metadata(
        frame,
        formula_method="drawdown_t = equity_curve_t / running_max(equity_curve)_t - 1",
        source_basis="Portfolio risk management: drawdown measures peak-to-trough loss.",
        why_valid="Drawdown is non-positive by construction and directly measures capital path risk.",
        limitation="Historical drawdown does not prove future crisis behavior.",
        invalidation_condition="Invalid if any drawdown is positive or equity curve is not a cumulative wealth series.",
        tested_by="tests/test_visual_analytics_outputs.py::test_equity_curve_starts_at_one_and_drawdown_non_positive",
        output_status="diagnostic",
    )


def build_model_risk_return_chart(
    risk_report: pd.DataFrame,
    walk_forward: pd.DataFrame,
    *,
    final_model: str,
) -> pd.DataFrame:
    """Build risk-return scatter data with risk on x-axis and return on y-axis."""
    rows: list[dict[str, object]] = []
    if not walk_forward.empty:
        for _, row in walk_forward.iterrows():
            model = str(row.get("model_name", ""))
            rows.append(
                {
                    "model_name": model,
                    "x_axis": "annualized_volatility",
                    "y_axis": "annualized_return",
                    "risk_x": _float(row.get("avg_volatility")),
                    "return_y": _float(row.get("avg_annualized_return")),
                    "sharpe": _float(row.get("avg_sharpe")),
                    "sortino": _float(row.get("avg_sortino")),
                    "max_drawdown": _float(row.get("avg_max_drawdown")),
                    "cvar_95": _float(row.get("avg_cvar_95")),
                    "metric_source": "walk_forward",
                    "is_final_model": model == final_model,
                    "is_equal_weight": model == "Equal Weight",
                }
            )
    if not rows and not risk_report.empty:
        for _, row in risk_report.iterrows():
            model = str(row.get("model_name", ""))
            rows.append(
                {
                    "model_name": model,
                    "x_axis": "annualized_volatility",
                    "y_axis": "annualized_return",
                    "risk_x": _float(row.get("annualized_volatility")),
                    "return_y": _float(row.get("annualized_return")),
                    "sharpe": _float(row.get("sharpe")),
                    "sortino": _float(row.get("sortino")),
                    "max_drawdown": _float(row.get("max_drawdown")),
                    "cvar_95": _float(row.get("cvar_95")),
                    "metric_source": "realized_sample",
                    "is_final_model": model == final_model,
                    "is_equal_weight": model == "Equal Weight",
                }
            )
    return _with_metadata(
        pd.DataFrame(rows),
        formula_method="scatter x = annualized volatility; y = annualized realized return; point labels carry Sharpe, Sortino, drawdown and CVaR",
        source_basis="Portfolio theory: risk-return charts place risk on the x-axis and return on the y-axis.",
        why_valid="The chart separates return level from risk level and does not rank by raw return alone.",
        limitation="Walk-forward is current-universe public-data evidence, not institutional point-in-time evidence.",
        invalidation_condition="Invalid if risk_x is not volatility, return_y is not return, or values are non-finite.",
        tested_by="tests/test_visual_analytics_outputs.py::test_model_risk_return_uses_risk_x_return_y",
        output_status="diagnostic",
    )


def build_forecast_error_chart(forecast_validation: pd.DataFrame) -> pd.DataFrame:
    """Build forecast model error versus random-walk error chart data."""
    if forecast_validation.empty:
        frame = pd.DataFrame(
            columns=[
                "horizon",
                "horizon_days",
                "model_mae",
                "random_walk_mae",
                "model_minus_random_walk_mae",
                "forecast_validation_status",
                "allocation_signal_status",
            ]
        )
    else:
        frame = pd.DataFrame(
            {
                "horizon": forecast_validation["horizon"].astype(str),
                "horizon_days": pd.to_numeric(
                    forecast_validation["horizon_days"], errors="coerce"
                ),
                "model_mae": pd.to_numeric(
                    forecast_validation["mean_mae"], errors="coerce"
                ),
                "random_walk_mae": pd.to_numeric(
                    forecast_validation["mean_random_walk_mae"], errors="coerce"
                ),
                "forecast_validation_status": forecast_validation[
                    "forecast_validation_status"
                ].astype(str),
                "allocation_signal_status": forecast_validation[
                    "allocation_signal_status"
                ].astype(str),
            }
        )
        frame["model_minus_random_walk_mae"] = (
            frame["model_mae"] - frame["random_walk_mae"]
        )
    return _with_metadata(
        frame,
        formula_method="model_minus_random_walk_mae = mean_model_MAE - mean_random_walk_MAE by horizon",
        source_basis="Financial ML validation: forecast models must be compared with a random-walk baseline.",
        why_valid="The chart shows whether model errors are lower than a naive random-walk benchmark in return units.",
        limitation="Forecast validation remains diagnostic unless portfolio-level decision quality improves after costs and risk.",
        invalidation_condition="Invalid if MAE scales are absurd, missing, or not comparable to random-walk MAE.",
        tested_by="tests/test_visual_analytics_outputs.py::test_forecast_error_chart_compares_model_and_random_walk",
        output_status="diagnostic",
    )


def build_random_benchmark_chart(
    random_distribution: pd.DataFrame,
    random_percentiles: pd.DataFrame,
    model_risk_return: pd.DataFrame,
    *,
    final_model: str,
) -> pd.DataFrame:
    """Build random benchmark distribution data for Sharpe visualization."""
    if random_distribution.empty or "sharpe" not in random_distribution:
        frame = pd.DataFrame(
            columns=[
                "bucket_left",
                "bucket_right",
                "portfolio_count",
                "metric",
                "final_model",
                "final_model_value",
                "final_model_percentile",
                "distribution_std",
                "is_degenerate",
            ]
        )
    else:
        sharpe = pd.to_numeric(random_distribution["sharpe"], errors="coerce").dropna()
        bins = min(20, max(5, int(np.sqrt(max(len(sharpe), 1)))))
        cuts = pd.cut(sharpe, bins=bins)
        counts = cuts.value_counts(sort=False)
        final_value = _final_metric(model_risk_return, final_model, "sharpe")
        percentile = _final_percentile(
            random_percentiles, final_model, "sharpe_percentile"
        )
        std = float(sharpe.std(ddof=1)) if len(sharpe) > 1 else 0.0
        frame = pd.DataFrame(
            {
                "bucket_left": [float(interval.left) for interval in counts.index],
                "bucket_right": [float(interval.right) for interval in counts.index],
                "portfolio_count": counts.to_numpy(dtype=int),
                "metric": "sharpe",
                "final_model": final_model,
                "final_model_value": final_value,
                "final_model_percentile": percentile,
                "distribution_std": std,
                "is_degenerate": std <= 1e-12 or counts.shape[0] <= 1,
            }
        )
    return _with_metadata(
        frame,
        formula_method="Histogram of constrained random portfolio Sharpe values with final-model Sharpe percentile marker.",
        source_basis="Market practice and validation: compare candidates against random portfolios under the same constraints.",
        why_valid="A non-degenerate distribution contextualizes whether the candidate is unusual relative to random constrained allocations.",
        limitation="Random portfolio superiority is benchmark context, not proof of future performance.",
        invalidation_condition="Invalid if distribution standard deviation is zero, all percentiles are identical, or random portfolios use a different universe.",
        tested_by="tests/test_visual_analytics_outputs.py::test_random_benchmark_chart_is_not_degenerate",
        output_status="diagnostic",
    )


def build_exposure_chart(processed_dir: str | Path) -> pd.DataFrame:
    """Build combined exposure chart data from existing exposure reports."""
    processed = Path(processed_dir)
    quality = _read_csv(processed / "global_exposure_metadata_quality.csv")
    metadata_status = (
        str(quality["exposure_metadata_status"].iloc[0])
        if not quality.empty and "exposure_metadata_status" in quality
        else "diagnostic_metadata_incomplete"
    )
    sector_coverage = (
        _float(quality["sector_coverage_ratio"].iloc[0])
        if not quality.empty and "sector_coverage_ratio" in quality
        else 0.0
    )
    issuer_country_coverage = (
        _float(quality["issuer_country_coverage_ratio"].iloc[0])
        if not quality.empty and "issuer_country_coverage_ratio" in quality
        else 0.0
    )
    industry_coverage = (
        _float(quality["industry_coverage_ratio"].iloc[0])
        if not quality.empty and "industry_coverage_ratio" in quality
        else 0.0
    )
    economic_country_coverage = (
        _float(quality["economic_country_coverage_ratio"].iloc[0])
        if not quality.empty and "economic_country_coverage_ratio" in quality
        else 0.0
    )
    listing_country_coverage = (
        _float(quality["listing_country_coverage_ratio"].iloc[0])
        if not quality.empty and "listing_country_coverage_ratio" in quality
        else 0.0
    )
    confidence_distribution = (
        str(quality["metadata_confidence_distribution"].iloc[0])
        if not quality.empty and "metadata_confidence_distribution" in quality
        else "{}"
    )
    specs = {
        "region": processed / "global_region_exposure.csv",
        "listing_country": processed / "global_listing_country_exposure.csv",
        "issuer_country": processed / "global_issuer_country_exposure.csv",
        "economic_country": processed / "global_economic_country_exposure.csv",
        "currency": processed / "global_currency_exposure.csv",
        "exchange": processed / "global_exchange_exposure.csv",
        "sector": processed / "global_sector_exposure.csv",
        "industry": processed / "global_industry_exposure.csv",
        "sleeve": processed / "global_sleeve_exposure.csv",
    }
    frames = []
    for exposure_type, path in specs.items():
        frame = _read_csv(path)
        if frame.empty or not {"bucket", "weight"}.issubset(frame):
            continue
        selected = frame[["bucket", "weight"]].copy()
        selected["exposure_type"] = exposure_type
        selected["weight"] = pd.to_numeric(selected["weight"], errors="coerce")
        selected["exposure_sum"] = selected["weight"].sum()
        selected["exposure_metadata_status"] = metadata_status
        selected["sector_coverage_ratio"] = sector_coverage
        selected["industry_coverage_ratio"] = industry_coverage
        selected["issuer_country_coverage_ratio"] = issuer_country_coverage
        selected["economic_country_coverage_ratio"] = economic_country_coverage
        selected["listing_country_coverage_ratio"] = listing_country_coverage
        selected["metadata_confidence_distribution"] = confidence_distribution
        frames.append(selected[["exposure_type", "bucket", "weight", "exposure_sum"]])
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty:
        combined["exposure_metadata_status"] = metadata_status
        combined["sector_coverage_ratio"] = sector_coverage
        combined["industry_coverage_ratio"] = industry_coverage
        combined["issuer_country_coverage_ratio"] = issuer_country_coverage
        combined["economic_country_coverage_ratio"] = economic_country_coverage
        combined["listing_country_coverage_ratio"] = listing_country_coverage
        combined["metadata_confidence_distribution"] = confidence_distribution
    return _with_metadata(
        combined,
        formula_method="exposure_weight = sum(final_model_weight by exposure bucket)",
        source_basis="Market practice: concentration risk must distinguish listing venue, issuer domicile, economic exposure, currency, sector and industry.",
        why_valid="Exposure weights must sum to 1 by exposure type for a fully invested long-only portfolio; listing-country and issuer-country are intentionally separate.",
        limitation="Economic-country exposure is not inferred silently; missing provider metadata remains an explicit missing bucket.",
        invalidation_condition="Invalid if any exposure type sum differs from 1 beyond tolerance or uses stale weights.",
        tested_by="tests/test_visual_analytics_outputs.py::test_exposure_chart_sums_to_one",
        output_status=metadata_status,
    )


def build_top_holdings_chart(
    weights: pd.DataFrame, *, final_model: str
) -> pd.DataFrame:
    """Build top holdings weight chart data for the final model."""
    model_weights = _weights_for_model(weights, final_model)
    if model_weights.empty:
        frame = pd.DataFrame(columns=["model_name", "ticker", "weight", "rank"])
    else:
        top = model_weights.sort_values(ascending=False).head(15)
        frame = pd.DataFrame(
            {
                "model_name": final_model,
                "ticker": top.index.astype(str),
                "weight": top.to_numpy(dtype=float),
                "rank": np.arange(1, len(top) + 1),
            }
        )
    return _with_metadata(
        frame,
        formula_method="top holdings ranked by final_model_weight descending",
        source_basis="Portfolio reporting practice: final weights and concentration must be transparent.",
        why_valid="Weights are direct final-model allocation weights and should sum to the visible top-slice total.",
        limitation="Top holdings are not buy recommendations and omit smaller positions.",
        invalidation_condition="Invalid if weights are negative, missing, or final model weights do not sum to 1.",
        tested_by="tests/test_visual_analytics_outputs.py::test_top_holdings_weights_are_non_negative",
        output_status="diagnostic",
    )


def validate_visual_analytics_frames(
    frames: dict[str, pd.DataFrame],
    *,
    tolerance: float = 1e-6,
) -> pd.DataFrame:
    """Validate major visual analytics invariants."""
    checks = [
        _check(
            "equity_curve_starts_at_one",
            _first_value(frames["equity_curve"], "equity_curve") == 1.0,
            "Equity curve must be normalized to 1.0 at the first plotted observation.",
        ),
        _check(
            "drawdown_non_positive",
            _all_leq(frames["drawdown_curve"], "drawdown", 0.0),
            "Drawdown must be <= 0 because it is wealth/running peak - 1.",
        ),
        _check(
            "risk_return_axes_correct",
            _risk_return_axes_correct(frames["model_risk_return"]),
            "Risk-return chart must use risk on x-axis and return on y-axis.",
        ),
        _check(
            "forecast_compares_random_walk",
            {"model_mae", "random_walk_mae"}.issubset(frames["forecast_error"].columns),
            "Forecast chart must compare model error with random-walk error.",
        ),
        _check(
            "random_benchmark_not_degenerate",
            not _any_true(frames["random_benchmark"], "is_degenerate"),
            "Random benchmark distribution must not be degenerate.",
        ),
        _check(
            "exposure_sums_to_one",
            _exposures_sum_to_one(frames["exposure"], tolerance=tolerance),
            "Exposure weights must sum to 1 within tolerance for each exposure type.",
            status=_exposure_validation_status(frames["exposure"]),
        ),
        _check(
            "top_holdings_non_negative",
            _all_geq(frames["top_holdings"], "weight", 0.0),
            "Final top holdings weights must be non-negative.",
        ),
    ]
    return pd.DataFrame(checks)


def build_visual_summary(
    *,
    final_model: str,
    validation: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build one-row-per-chart summary with methodology and status."""
    rows = []
    for chart_name, frame in frames.items():
        status = "passed" if _chart_passed(chart_name, validation) else "failed"
        metadata = _metadata_from_frame(frame)
        if chart_name == "exposure" and status == "passed":
            output_status = str(metadata.get("output_status", ""))
            if output_status and output_status not in {"passed", "diagnostic"}:
                status = output_status
        rows.append(
            {
                "chart_name": chart_name,
                "final_model": final_model,
                "row_count": int(len(frame)),
                "validation_status": status,
                **metadata,
            }
        )
    return pd.DataFrame(rows)


def validate_visual_analytics_outputs(
    processed_dir: str | Path,
) -> dict[str, object]:
    """Validate visual analytics CSV files already written to disk."""
    processed = Path(processed_dir)
    frames = {
        "equity_curve": _read_csv(processed / VISUAL_ANALYTICS_FILES["equity_curve"]),
        "drawdown_curve": _read_csv(
            processed / VISUAL_ANALYTICS_FILES["drawdown_curve"]
        ),
        "model_risk_return": _read_csv(
            processed / VISUAL_ANALYTICS_FILES["model_risk_return"]
        ),
        "forecast_error": _read_csv(
            processed / VISUAL_ANALYTICS_FILES["forecast_error"]
        ),
        "random_benchmark": _read_csv(
            processed / VISUAL_ANALYTICS_FILES["random_benchmark"]
        ),
        "exposure": _read_csv(processed / VISUAL_ANALYTICS_FILES["exposure"]),
        "top_holdings": _read_csv(processed / VISUAL_ANALYTICS_FILES["top_holdings"]),
    }
    validation = validate_visual_analytics_frames(frames)
    missing_files = [
        filename
        for filename in VISUAL_ANALYTICS_FILES.values()
        if not (processed / filename).exists()
    ]
    if missing_files:
        validation = pd.concat(
            [
                validation,
                pd.DataFrame(
                    [
                        _check(
                            "visual_files_exist",
                            False,
                            f"missing_files={missing_files}",
                        )
                    ]
                ),
            ],
            ignore_index=True,
        )
    failed = validation.loc[~validation["passed"].astype(bool)]
    return {
        "overall_status": "passed" if failed.empty else "failed",
        "failed_check_count": int(len(failed)),
        "checks": validation.to_dict(orient="records"),
    }


def _with_metadata(
    frame: pd.DataFrame,
    *,
    formula_method: str,
    source_basis: str,
    why_valid: str,
    limitation: str,
    invalidation_condition: str,
    tested_by: str,
    output_status: str,
) -> pd.DataFrame:
    result = frame.copy()
    for column, value in {
        "formula_method": formula_method,
        "source_basis": source_basis,
        "why_valid": why_valid,
        "limitation": limitation,
        "invalidation_condition": invalidation_condition,
        "tested_by": tested_by,
        "output_status": output_status,
    }.items():
        result[column] = value
    return result


def _weights_for_model(weights: pd.DataFrame, model: str) -> pd.Series:
    if weights.empty or not {"model_name", "ticker", "weight"}.issubset(weights):
        return pd.Series(dtype=float)
    frame = weights.loc[weights["model_name"].astype(str).eq(str(model))].copy()
    if frame.empty:
        return pd.Series(dtype=float)
    series = frame.set_index("ticker")["weight"].astype(float)
    if float(series.sum()) > 0:
        series = series / float(series.sum())
    return series


def _read_returns(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    first = str(frame.columns[0]).lower() if len(frame.columns) else ""
    if first in {"date", "datetime", "timestamp"}:
        frame = frame.set_index(frame.columns[0])
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    return frame.loc[frame.index.notna()]


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _float(value: object) -> float:
    try:
        if value is None or pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _final_metric(frame: pd.DataFrame, final_model: str, column: str) -> float:
    if frame.empty or {"model_name", column}.difference(frame.columns):
        return float("nan")
    row = frame.loc[frame["model_name"].astype(str).eq(final_model)]
    return _float(row[column].iloc[0]) if not row.empty else float("nan")


def _final_percentile(frame: pd.DataFrame, final_model: str, column: str) -> float:
    return _final_metric(frame, final_model, column)


def _first_value(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame:
        return None
    value = _float(frame[column].iloc[0])
    if not np.isfinite(value):
        return None
    return round(value, 12)


def _all_leq(frame: pd.DataFrame, column: str, value: float) -> bool:
    if frame.empty or column not in frame:
        return False
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    return bool(not series.empty and (series <= value + 1e-12).all())


def _all_geq(frame: pd.DataFrame, column: str, value: float) -> bool:
    if frame.empty or column not in frame:
        return False
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    return bool(not series.empty and (series >= value - 1e-12).all())


def _any_true(frame: pd.DataFrame, column: str) -> bool:
    if frame.empty or column not in frame:
        return True
    return bool(frame[column].map(lambda item: str(item).lower() == "true").any())


def _risk_return_axes_correct(frame: pd.DataFrame) -> bool:
    if frame.empty or not {"x_axis", "y_axis", "risk_x", "return_y"}.issubset(frame):
        return False
    return bool(
        frame["x_axis"].astype(str).eq("annualized_volatility").all()
        and frame["y_axis"].astype(str).eq("annualized_return").all()
        and pd.to_numeric(frame["risk_x"], errors="coerce").notna().any()
        and pd.to_numeric(frame["return_y"], errors="coerce").notna().any()
    )


def _exposures_sum_to_one(frame: pd.DataFrame, *, tolerance: float) -> bool:
    if frame.empty or not {"exposure_type", "weight"}.issubset(frame):
        return False
    weights = frame.copy()
    weights["weight"] = pd.to_numeric(weights["weight"], errors="coerce")
    sums = weights.groupby("exposure_type")["weight"].sum()
    return bool(
        not sums.empty and np.allclose(sums.to_numpy(dtype=float), 1.0, atol=tolerance)
    )


def _exposure_validation_status(frame: pd.DataFrame) -> str:
    if frame.empty or "exposure_metadata_status" not in frame:
        return "failed"
    statuses = frame["exposure_metadata_status"].dropna().astype(str)
    if statuses.empty:
        return "failed"
    if statuses.eq("passed").all():
        return "passed"
    if statuses.eq("passed_with_metadata_warning").any():
        return "passed_with_metadata_warning"
    if statuses.eq("diagnostic_metadata_incomplete").any():
        return "diagnostic_metadata_incomplete"
    if statuses.eq("failed").any():
        return "failed"
    return "passed_with_metadata_warning"


def _chart_passed(chart_name: str, validation: pd.DataFrame) -> bool:
    mapping = {
        "equity_curve": "equity_curve_starts_at_one",
        "drawdown_curve": "drawdown_non_positive",
        "model_risk_return": "risk_return_axes_correct",
        "forecast_error": "forecast_compares_random_walk",
        "random_benchmark": "random_benchmark_not_degenerate",
        "exposure": "exposure_sums_to_one",
        "top_holdings": "top_holdings_non_negative",
    }
    check_name = mapping.get(chart_name)
    if check_name is None or validation.empty:
        return False
    row = validation.loc[validation["check"].astype(str).eq(check_name)]
    return bool(not row.empty and row["passed"].astype(bool).iloc[0])


def _metadata_from_frame(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty:
        return {column: "" for column in METADATA_COLUMNS}
    return {
        column: frame[column].iloc[0] if column in frame else ""
        for column in METADATA_COLUMNS
    }


def _check(
    name: str,
    passed: bool,
    details: str,
    *,
    status: str | None = None,
) -> dict[str, object]:
    return {
        "check": name,
        "passed": bool(passed),
        "status": status or ("passed" if passed else "failed"),
        "details": details,
    }
