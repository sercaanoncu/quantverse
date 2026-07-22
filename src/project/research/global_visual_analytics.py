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
    final_model = _resolve_final_model(decision, summary_json)
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    risk = _read_csv(processed / "global_portfolio_risk_report.csv")
    walk = _read_csv(processed / "global_walk_forward_model_comparison.csv")
    walk_returns = _read_csv(processed / "global_walk_forward_returns.csv")
    random_distribution = _read_csv(
        processed / "global_random_portfolio_distribution.csv"
    )
    random_percentiles = _read_csv(
        processed / "global_random_portfolio_percentile_report.csv"
    )
    forecast = _read_csv(processed / "global_forecast_validation_by_horizon.csv")

    final_weights = _weights_for_model(weights, final_model)
    if final_weights.empty:
        raise ValueError(
            f"No portfolio weights were available for final model {final_model!r}."
        )
    final_returns = _walk_forward_model_returns(walk_returns, final_model)

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


def _resolve_final_model(
    decision: dict[str, object], summary: dict[str, object]
) -> str:
    del summary
    value = str(decision.get("final_selected_model", "")).strip()
    if value and value.lower() not in {"nan", "none", "not_available"}:
        return value
    raise ValueError(
        "Visual analytics require an explicit, available final-model decision "
        "artifact; a demo-summary fallback is not accepted."
    )


def build_equity_curve(
    returns: pd.Series,
    *,
    final_model: str,
) -> pd.DataFrame:
    """Build an OOS final-model equity curve with an explicit 1.0 baseline."""
    clean = pd.Series(returns, dtype=float).copy()
    if clean.empty:
        frame = pd.DataFrame(
            columns=[
                "date",
                "model_name",
                "daily_return",
                "equity_curve",
                "is_baseline",
            ]
        )
    else:
        values = clean.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("OOS equity-curve returns must be complete and finite.")
        if bool((values < -1.0 - 1e-12).any()):
            raise ValueError("A daily simple return below -100% is invalid.")
        dates = pd.to_datetime(clean.index, errors="coerce")
        if dates.isna().any() or dates.duplicated().any():
            raise ValueError("OOS equity-curve dates must be valid and unique.")
        clean.index = dates
        clean = clean.sort_index()
        wealth = (1.0 + clean).cumprod()
        baseline_date = clean.index[0] - pd.offsets.BDay(1)
        frame = pd.DataFrame(
            {
                "date": pd.DatetimeIndex([baseline_date]).append(clean.index),
                "model_name": final_model,
                "daily_return": np.concatenate(
                    [np.array([0.0]), clean.to_numpy(dtype=float)]
                ),
                "equity_curve": np.concatenate(
                    [np.array([1.0]), wealth.to_numpy(dtype=float)]
                ),
                "is_baseline": np.concatenate(
                    [np.array([True]), np.zeros(len(clean), dtype=bool)]
                ),
            }
        )
    result = _with_metadata(
        frame,
        formula_method="equity_curve_0 = 1; equity_curve_t = prod_{i=1..t}(1 + stitched_walk_forward_net_simple_return_i)",
        source_basis="Portfolio theory and financial statistics: simple returns compound through cumulative wealth.",
        why_valid="The plotted path uses the selected model's non-overlapping, transaction-cost-adjusted walk-forward OOS daily returns and preserves every return after an explicit 1.0 baseline.",
        limitation="Current-universe public-data OOS evidence; not point-in-time institutional performance.",
        invalidation_condition="Invalid if the source is not the selected model's stitched OOS net path, first equity_curve is not 1.0, any return is omitted, or dates overlap.",
        tested_by="tests/test_visual_analytics_outputs.py::test_equity_curve_starts_at_one_and_drawdown_non_positive",
        output_status="walk_forward_oos_net",
    )
    return _attach_path_scope(result, clean)


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
    result = _with_metadata(
        frame,
        formula_method="drawdown_t = equity_curve_t / running_max(equity_curve)_t - 1",
        source_basis="Portfolio risk management: drawdown measures peak-to-trough loss.",
        why_valid="Drawdown is recomputed from the same selected-model stitched OOS net wealth path and is non-positive by construction.",
        limitation="Current-universe historical OOS drawdown does not prove future crisis behavior.",
        invalidation_condition="Invalid if any drawdown is positive, the equity source is not walk-forward OOS net, or the curve omits an OOS return.",
        tested_by="tests/test_visual_analytics_outputs.py::test_equity_curve_starts_at_one_and_drawdown_non_positive",
        output_status="walk_forward_oos_net",
    )
    return _inherit_path_scope(result, equity_curve)


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
                "sampling_method",
                "benchmark_scope",
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
        sampling_method = _single_label(
            random_distribution,
            "sampling_method",
            default="not_available",
        )
        benchmark_scope = _single_label(
            random_distribution,
            "benchmark_scope",
            default="not_available",
        )
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
                "sampling_method": sampling_method,
                "benchmark_scope": benchmark_scope,
            }
        )
    return _with_metadata(
        frame,
        formula_method="Histogram of constrained random portfolio Sharpe values with final-model Sharpe percentile marker.",
        source_basis="Market practice and validation: compare candidates against random portfolios under the same constraints.",
        why_valid="A non-degenerate distribution contextualizes whether the candidate is unusual relative to random constrained allocations.",
        limitation="Random portfolio superiority is benchmark context, not proof of future performance. The current projected-raw-score sampler is not uniform over the capped simplex.",
        invalidation_condition="Invalid if distribution standard deviation is zero, all percentiles are identical, benchmark_scope is not comparable, or random portfolios use a different universe.",
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
            "equity_curve_uses_walk_forward_oos_net_scope",
            _single_scope_is_walk_forward_oos_net(frames["equity_curve"]),
            "Equity curve must be labelled as the selected model's stitched walk-forward OOS net path.",
        ),
        _check(
            "equity_curve_compounds_every_oos_return",
            _equity_curve_compounds_every_return(frames["equity_curve"]),
            "An explicit 1.0 baseline must precede the compounded path and no OOS return may be normalized away.",
        ),
        _check(
            "drawdown_non_positive",
            _all_leq(frames["drawdown_curve"], "drawdown", 0.0),
            "Drawdown must be <= 0 because it is wealth/running peak - 1.",
        ),
        _check(
            "drawdown_matches_equity_curve",
            _drawdown_matches_equity_curve(
                frames["equity_curve"],
                frames["drawdown_curve"],
                tolerance=tolerance,
            ),
            "Drawdown must be recomputable from the published OOS equity curve.",
        ),
        _check(
            "risk_return_axes_correct",
            _risk_return_axes_correct(frames["model_risk_return"]),
            "Risk-return chart must use risk on x-axis and return on y-axis.",
        ),
        _check(
            "forecast_compares_random_walk",
            _forecast_comparison_is_finite(frames["forecast_error"]),
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
    validation = pd.concat(
        [
            validation,
            pd.DataFrame(
                _validate_published_oos_path(
                    processed,
                    frames["equity_curve"],
                    frames["drawdown_curve"],
                )
            ),
        ],
        ignore_index=True,
    )
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


def _walk_forward_model_returns(
    walk_returns: pd.DataFrame,
    final_model: str,
) -> pd.Series:
    required = {"Date", "model_name", "return"}
    if walk_returns.empty or not required.issubset(walk_returns.columns):
        raise ValueError(
            "Visual analytics require the raw stitched walk-forward return path."
        )
    selected = walk_returns.loc[
        walk_returns["model_name"].astype(str).eq(str(final_model)),
        ["Date", "return"],
    ].copy()
    if selected.empty:
        raise ValueError(
            f"No stitched walk-forward returns were available for {final_model!r}."
        )
    selected["Date"] = pd.to_datetime(selected["Date"], errors="coerce")
    selected["return"] = pd.to_numeric(selected["return"], errors="coerce")
    values = selected["return"].to_numpy(dtype=float)
    if selected["Date"].isna().any() or not np.isfinite(values).all():
        raise ValueError("Stitched walk-forward dates and returns must be finite.")
    if selected["Date"].duplicated().any():
        raise ValueError(
            "Stitched walk-forward returns contain overlapping model-date rows."
        )
    selected = selected.sort_values("Date", kind="stable")
    return pd.Series(
        selected["return"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(selected["Date"]),
        name=final_model,
        dtype=float,
    )


def _attach_path_scope(frame: pd.DataFrame, returns: pd.Series) -> pd.DataFrame:
    result = frame.copy()
    result["evidence_scope"] = "walk_forward_oos_net"
    result["source_observations"] = int(len(returns))
    result["source_start_date"] = (
        pd.Timestamp(returns.index.min()).date().isoformat()
        if not returns.empty
        else ""
    )
    result["source_end_date"] = (
        pd.Timestamp(returns.index.max()).date().isoformat()
        if not returns.empty
        else ""
    )
    return result


def _inherit_path_scope(frame: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in [
        "evidence_scope",
        "source_observations",
        "source_start_date",
        "source_end_date",
    ]:
        result[column] = (
            source[column].iloc[0] if column in source and not source.empty else ""
        )
    return result


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


def _single_label(
    frame: pd.DataFrame,
    column: str,
    *,
    default: str,
) -> str:
    if frame.empty or column not in frame:
        return default
    values = frame[column].dropna().astype(str).unique()
    if len(values) != 1:
        return "mixed_or_unavailable"
    return str(values[0])


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
    series = pd.to_numeric(frame[column], errors="coerce")
    finite = np.isfinite(series.to_numpy(dtype=float))
    return bool(finite.all() and (series <= value + 1e-12).all())


def _all_geq(frame: pd.DataFrame, column: str, value: float) -> bool:
    if frame.empty or column not in frame:
        return False
    series = pd.to_numeric(frame[column], errors="coerce")
    finite = np.isfinite(series.to_numpy(dtype=float))
    return bool(finite.all() and (series >= value - 1e-12).all())


def _any_true(frame: pd.DataFrame, column: str) -> bool:
    if frame.empty or column not in frame:
        return True
    normalized = frame[column].astype(str).str.strip().str.lower()
    if not normalized.isin({"true", "false"}).all():
        return True
    return bool(normalized.eq("true").any())


def _forecast_comparison_is_finite(frame: pd.DataFrame) -> bool:
    required = {"model_mae", "random_walk_mae"}
    if frame.empty or not required.issubset(frame.columns):
        return False
    values = frame[list(required)].apply(pd.to_numeric, errors="coerce")
    return bool(np.isfinite(values.to_numpy(dtype=float)).all())


def _risk_return_axes_correct(frame: pd.DataFrame) -> bool:
    if frame.empty or not {"x_axis", "y_axis", "risk_x", "return_y"}.issubset(frame):
        return False
    risk = pd.to_numeric(frame["risk_x"], errors="coerce")
    returns = pd.to_numeric(frame["return_y"], errors="coerce")
    return bool(
        frame["x_axis"].astype(str).eq("annualized_volatility").all()
        and frame["y_axis"].astype(str).eq("annualized_return").all()
        and np.isfinite(risk.to_numpy(dtype=float)).all()
        and np.isfinite(returns.to_numpy(dtype=float)).all()
    )


def _single_scope_is_walk_forward_oos_net(frame: pd.DataFrame) -> bool:
    if frame.empty or "evidence_scope" not in frame:
        return False
    return bool(frame["evidence_scope"].astype(str).eq("walk_forward_oos_net").all())


def _equity_curve_compounds_every_return(frame: pd.DataFrame) -> bool:
    required = {"date", "daily_return", "equity_curve", "is_baseline"}
    if frame.empty or not required.issubset(frame.columns):
        return False
    dates = pd.to_datetime(frame["date"], errors="coerce")
    daily = pd.to_numeric(frame["daily_return"], errors="coerce")
    equity = pd.to_numeric(frame["equity_curve"], errors="coerce")
    baseline = frame["is_baseline"].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes"}
    )
    if (
        dates.isna().any()
        or dates.duplicated().any()
        or not dates.is_monotonic_increasing
        or not np.isfinite(daily.to_numpy(dtype=float)).all()
        or not np.isfinite(equity.to_numpy(dtype=float)).all()
        or int(baseline.sum()) != 1
        or not bool(baseline.iloc[0])
        or not np.isclose(float(daily.iloc[0]), 0.0, atol=1e-12)
        or not np.isclose(float(equity.iloc[0]), 1.0, atol=1e-12)
    ):
        return False
    returns = daily.loc[~baseline].to_numpy(dtype=float)
    if bool((returns < -1.0 - 1e-12).any()):
        return False
    expected = np.concatenate([np.array([1.0]), np.cumprod(1.0 + returns)])
    return bool(
        len(expected) == len(equity)
        and np.allclose(
            equity.to_numpy(dtype=float),
            expected,
            atol=1e-12,
            rtol=1e-10,
        )
    )


def _drawdown_matches_equity_curve(
    equity_curve: pd.DataFrame,
    drawdown_curve: pd.DataFrame,
    *,
    tolerance: float,
) -> bool:
    required_equity = {"date", "equity_curve"}
    required_drawdown = {"date", "drawdown"}
    if (
        equity_curve.empty
        or drawdown_curve.empty
        or not required_equity.issubset(equity_curve.columns)
        or not required_drawdown.issubset(drawdown_curve.columns)
        or len(equity_curve) != len(drawdown_curve)
        or not _single_scope_is_walk_forward_oos_net(drawdown_curve)
    ):
        return False
    equity_dates = pd.to_datetime(equity_curve["date"], errors="coerce")
    drawdown_dates = pd.to_datetime(drawdown_curve["date"], errors="coerce")
    wealth = pd.to_numeric(equity_curve["equity_curve"], errors="coerce")
    observed = pd.to_numeric(drawdown_curve["drawdown"], errors="coerce")
    if (
        equity_dates.isna().any()
        or drawdown_dates.isna().any()
        or not equity_dates.reset_index(drop=True).equals(
            drawdown_dates.reset_index(drop=True)
        )
        or not np.isfinite(wealth.to_numpy(dtype=float)).all()
        or not np.isfinite(observed.to_numpy(dtype=float)).all()
    ):
        return False
    expected = wealth / wealth.cummax() - 1.0
    return bool(
        np.allclose(
            observed.to_numpy(dtype=float),
            expected.to_numpy(dtype=float),
            atol=tolerance,
            rtol=1e-10,
        )
    )


def _validate_published_oos_path(
    processed: Path,
    equity_curve: pd.DataFrame,
    drawdown_curve: pd.DataFrame,
) -> list[dict[str, object]]:
    try:
        final_model = _resolve_final_model(
            _read_json(processed / "global_final_model_decision.json"),
            _read_json(processed / "quantverse_v2_demo_summary.json"),
        )
        expected = _walk_forward_model_returns(
            _read_csv(processed / "global_walk_forward_returns.csv"),
            final_model,
        )
        required = {
            "date",
            "model_name",
            "daily_return",
            "is_baseline",
            "source_observations",
            "source_start_date",
            "source_end_date",
        }
        if equity_curve.empty or not required.issubset(equity_curve.columns):
            raise ValueError("Published equity evidence is incomplete.")
        baseline = equity_curve["is_baseline"].map(
            lambda value: str(value).strip().lower() in {"1", "true", "yes"}
        )
        published = equity_curve.loc[~baseline].copy()
        published_dates = pd.to_datetime(published["date"], errors="coerce")
        published_returns = pd.to_numeric(
            published["daily_return"],
            errors="coerce",
        )
        source_matches = bool(
            len(published) == len(expected)
            and not published_dates.isna().any()
            and published_dates.reset_index(drop=True).equals(
                pd.Series(expected.index).reset_index(drop=True)
            )
            and np.allclose(
                published_returns.to_numpy(dtype=float),
                expected.to_numpy(dtype=float),
                atol=1e-12,
                rtol=1e-10,
            )
            and equity_curve["model_name"].astype(str).eq(final_model).all()
            and int(equity_curve["source_observations"].iloc[0]) == len(expected)
            and str(equity_curve["source_start_date"].iloc[0])
            == expected.index.min().date().isoformat()
            and str(equity_curve["source_end_date"].iloc[0])
            == expected.index.max().date().isoformat()
            and len(drawdown_curve) == len(equity_curve)
        )
        details = (
            f"model={final_model}; source_rows={len(expected)}; "
            f"published_return_rows={len(published)}; "
            f"published_curve_rows={len(equity_curve)}"
        )
    except (KeyError, TypeError, ValueError) as exc:
        source_matches = False
        details = f"error_type={type(exc).__name__}"
    return [
        _check(
            "published_equity_curve_reconciles_stitched_oos_source",
            source_matches,
            details,
        )
    ]


def _exposures_sum_to_one(frame: pd.DataFrame, *, tolerance: float) -> bool:
    if frame.empty or not {"exposure_type", "weight"}.issubset(frame):
        return False
    weights = frame.copy()
    weights["weight"] = pd.to_numeric(weights["weight"], errors="coerce")
    if (
        weights["exposure_type"].isna().any()
        or not np.isfinite(weights["weight"].to_numpy(dtype=float)).all()
        or (weights["weight"] < -tolerance).any()
    ):
        return False
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
