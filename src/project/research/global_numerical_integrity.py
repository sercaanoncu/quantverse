"""Numerical integrity helpers for QuantVerse v2 research artifacts.

The checks in this module are intentionally economic and mathematical, not
only schema-based. A generated file is not valid if portfolio returns collapse
to an empty, all-zero, or crypto-contaminated series while the report still
looks complete.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

EXECUTABLE_MODEL_STATUSES = {"actually_run", "benchmark_only"}
RETURN_METRIC_COLUMNS = [
    "cagr",
    "annualized_return",
    "annualized_volatility",
    "sharpe",
    "sortino",
    "max_drawdown",
    "var_95",
    "cvar_95",
    "total_return",
]
LEAGUE_RETURN_METRIC_COLUMNS = [
    "cagr",
    "annualized_return",
    "volatility",
    "sharpe",
    "sortino",
    "max_drawdown",
    "var_95",
    "cvar_95",
]
WALK_FORWARD_METRIC_COLUMNS = [
    "avg_cagr",
    "avg_annualized_return",
    "avg_volatility",
    "avg_sharpe",
    "avg_sortino",
    "avg_max_drawdown",
    "avg_cvar_95",
]


def clean_returns_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Return a numeric, date-indexed simple-return matrix."""
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(clean.columns[0])
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.dropna(axis=1, how="all").dropna(how="all")


def portfolio_return_series(
    returns: pd.DataFrame,
    weights: pd.Series,
    *,
    min_available_weight: float = 0.50,
    min_assets: int = 1,
) -> pd.Series:
    """Build portfolio returns with per-date available-weight normalization.

    Public providers often have different listing histories across global
    equities. A direct matrix product turns any row with one missing constituent
    into NaN. This helper uses only constituents available on each date and
    rescales by available selected weight, while dropping dates with too little
    coverage.
    """
    clean = clean_returns_matrix(returns)
    if clean.empty:
        return pd.Series(dtype=float, name="portfolio_return")

    aligned = pd.Series(weights, dtype=float).reindex(clean.columns).fillna(0.0)
    aligned = aligned[aligned.abs() > 1e-12]
    if aligned.empty or float(aligned.abs().sum()) <= 0:
        return pd.Series(dtype=float, name="portfolio_return")
    if float(aligned.sum()) != 0:
        aligned = aligned / float(aligned.sum())

    selected = clean.reindex(columns=aligned.index)
    available = selected.notna()
    available_weight = available.mul(aligned.abs(), axis=1).sum(axis=1)
    available_count = available.sum(axis=1)
    weighted_sum = selected.mul(aligned, axis=1).sum(axis=1, skipna=True)
    series = weighted_sum / available_weight.replace(0.0, np.nan)
    valid = (available_weight >= float(min_available_weight)) & (
        available_count >= int(min_assets)
    )
    series = series.loc[valid].replace([np.inf, -np.inf], np.nan).dropna()
    return series.astype(float).rename("portfolio_return")


def return_series_diagnostics(series: pd.Series) -> dict[str, object]:
    """Summarize a portfolio return series for debug logs and integrity checks."""
    clean = pd.Series(series, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return {
            "observations": 0,
            "nonzero_count": 0,
            "minimum": np.nan,
            "maximum": np.nan,
            "mean": np.nan,
            "standard_deviation": np.nan,
            "metric_status": "insufficient_data",
        }
    nonzero = int((clean.abs() > 1e-12).sum())
    return {
        "observations": int(clean.shape[0]),
        "nonzero_count": nonzero,
        "minimum": float(clean.min()),
        "maximum": float(clean.max()),
        "mean": float(clean.mean()),
        "standard_deviation": float(clean.std(ddof=1)) if clean.shape[0] > 1 else 0.0,
        "metric_status": "valid" if nonzero > 0 else "zero_return_series",
    }


def validate_v2_numerical_integrity(
    root: str | Path,
    *,
    summary_override: dict[str, object] | None = None,
) -> dict[str, object]:
    """Validate generated QuantVerse v2 outputs for numerical plausibility."""
    root_path = Path(root)
    processed = root_path / "data" / "processed"
    checks: list[dict[str, object]] = []

    summary = (
        dict(summary_override)
        if summary_override is not None
        else _read_json(processed / "quantverse_v2_demo_summary.json")
    )
    final_model = str(summary.get("final_selected_model", "")).strip()
    final_holdings = _float(summary.get("final_selected_holdings"), default=0.0)
    returns = _read_returns(processed / "global_security_simple_returns_usd.csv")
    league = _read_csv(processed / "global_portfolio_league.csv")
    risk = _read_csv(processed / "global_portfolio_risk_report.csv")
    weights = _read_csv(processed / "global_portfolio_league_weights.csv")
    walk = _read_csv(processed / "global_walk_forward_model_comparison.csv")
    random_percentiles = _read_csv(
        processed / "global_random_portfolio_percentile_report.csv"
    )
    forecasts = _read_csv(processed / "global_forecast_validation_by_horizon.csv")
    contributions = _read_csv(processed / "global_risk_contribution_report.csv")
    scores = _read_csv(processed / "global_stock_scores.csv")

    _check_risk_metrics_not_all_zero(risk, league, checks)
    _check_final_model_volatility(summary, risk, final_model, final_holdings, checks)
    _check_final_return_series(returns, weights, final_model, checks)
    _check_walk_forward_not_all_zero(walk, checks)
    _check_random_percentiles_not_degenerate(random_percentiles, checks)
    _check_forecast_scale(forecasts, checks)
    _check_forecast_not_allocation_promoted(forecasts, checks)
    _check_final_weights(weights, returns, final_model, checks)
    _check_risk_contribution_sum(contributions, final_model, checks)
    _check_equity_scope(scores, weights, final_model, checks)
    _check_complete_claim_with_integrity(summary, checks)

    failed = [check for check in checks if not bool(check["passed"])]
    return {
        "overall_status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "checks": checks,
    }


def _check_risk_metrics_not_all_zero(
    risk: pd.DataFrame,
    league: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    executable = _executable_models(league)
    frame = _rows_for_models(risk, executable)
    numeric = _numeric(frame, RETURN_METRIC_COLUMNS)
    passed = bool(not numeric.empty and (numeric.abs().sum(axis=1) > 1e-12).any())
    checks.append(
        _check(
            "risk_metrics_not_all_zero_for_executable_models",
            passed,
            f"rows={len(frame)}; executable_models={sorted(executable)}",
        )
    )


def _check_final_model_volatility(
    summary: dict[str, object],
    risk: pd.DataFrame,
    final_model: str,
    final_holdings: float,
    checks: list[dict[str, object]],
) -> None:
    vol = _float(summary.get("expected_portfolio_volatility"), default=np.nan)
    if np.isnan(vol) and not risk.empty and "model_name" in risk:
        row = risk.loc[risk["model_name"].astype(str).eq(final_model)]
        if not row.empty:
            vol = _float(row.iloc[0].get("annualized_volatility"), default=np.nan)
    passed = bool(final_holdings <= 1 or (np.isfinite(vol) and abs(vol) > 1e-12))
    checks.append(
        _check(
            "final_model_volatility_nonzero_with_multiple_holdings",
            passed,
            f"final_model={final_model}; holdings={final_holdings}; volatility={vol}",
        )
    )


def _check_final_return_series(
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    final_model: str,
    checks: list[dict[str, object]],
) -> None:
    model_weights = _weights_for_model(weights, final_model)
    series = portfolio_return_series(returns, model_weights)
    diagnostics = return_series_diagnostics(series)
    passed = bool(
        diagnostics["observations"] > 0
        and diagnostics["nonzero_count"] > 0
        and float(diagnostics["standard_deviation"]) > 0
    )
    checks.append(
        _check(
            "final_portfolio_return_series_non_empty_nonzero",
            passed,
            f"final_model={final_model}; diagnostics={diagnostics}",
        )
    )


def _check_walk_forward_not_all_zero(
    walk: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    numeric = _numeric(walk, WALK_FORWARD_METRIC_COLUMNS)
    passed = bool(not numeric.empty and (numeric.abs().sum(axis=1) > 1e-12).any())
    checks.append(
        _check(
            "walk_forward_metrics_not_all_zero",
            passed,
            f"rows={len(walk)}; columns={WALK_FORWARD_METRIC_COLUMNS}",
        )
    )


def _check_random_percentiles_not_degenerate(
    random_percentiles: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    percentile_columns = [
        "return_percentile",
        "volatility_percentile",
        "sharpe_percentile",
        "max_drawdown_percentile",
        "cvar_percentile",
    ]
    numeric = _numeric(random_percentiles, percentile_columns)
    passed = True
    if numeric.empty:
        passed = False
    else:
        all_one = numeric.notna().all(axis=1) & np.isclose(numeric, 1.0).all(axis=1)
        passed = bool(not all_one.all() and numeric.nunique(dropna=True).sum() > 1)
    checks.append(
        _check(
            "random_percentiles_not_identical_one",
            passed,
            f"rows={len(random_percentiles)}",
        )
    )


def _check_forecast_scale(
    forecasts: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    if forecasts.empty:
        checks.append(_check("forecast_error_scale_sane", False, "missing forecasts"))
        return
    frame = forecasts.copy()
    for column in ["mean_mae", "mean_rmse", "mean_random_walk_mae"]:
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    model_error = frame[["mean_mae", "mean_rmse"]].max(axis=1)
    random_error = frame["mean_random_walk_mae"]
    absurd_absolute = model_error > 2.0
    absurd_relative = (model_error > 10.0 * random_error.clip(lower=1e-12)) & (
        model_error > 0.50
    )
    passed = bool(not (absurd_absolute | absurd_relative).fillna(False).any())
    checks.append(
        _check(
            "forecast_error_scale_sane",
            passed,
            f"max_model_error={_safe_max(model_error)}; max_random_walk_error={_safe_max(random_error)}",
        )
    )


def _check_forecast_not_allocation_promoted(
    forecasts: pd.DataFrame,
    checks: list[dict[str, object]],
) -> None:
    if forecasts.empty or "allocation_signal_status" not in forecasts:
        checks.append(
            _check(
                "forecast_underperformance_not_allocation_promoted",
                True,
                "no allocation-promoting forecast status present",
            )
        )
        return
    promoted = forecasts["allocation_signal_status"].astype(str).str.contains(
        "promot|allocat", case=False, na=False
    ) & ~forecasts["allocation_signal_status"].astype(str).str.contains(
        "diagnostic|not_allowed|blocked", case=False, na=False
    )
    checks.append(
        _check(
            "forecast_underperformance_not_allocation_promoted",
            not bool(promoted.any()),
            f"promoted_rows={int(promoted.sum())}",
        )
    )


def _check_final_weights(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    final_model: str,
    checks: list[dict[str, object]],
) -> None:
    model_weights = _weights_for_model(weights, final_model)
    weight_sum = float(model_weights.sum()) if not model_weights.empty else 0.0
    missing = [
        ticker for ticker in model_weights.index if ticker not in returns.columns
    ]
    checks.append(
        _check(
            "final_weights_sum_to_one_integrity",
            abs(weight_sum - 1.0) <= 1e-6,
            f"final_model={final_model}; weight_sum={weight_sum}",
        )
    )
    checks.append(
        _check(
            "final_weight_tickers_exist_in_returns",
            not missing,
            f"missing_tickers={missing[:10]}; missing_count={len(missing)}",
        )
    )


def _check_risk_contribution_sum(
    contributions: pd.DataFrame,
    final_model: str,
    checks: list[dict[str, object]],
) -> None:
    if contributions.empty or "risk_contribution_pct" not in contributions:
        checks.append(_check("risk_contribution_pct_sums_to_one", False, "missing"))
        return
    frame = (
        contributions.loc[contributions["model_name"].astype(str).eq(final_model)]
        if "model_name" in contributions
        else contributions
    )
    total = pd.to_numeric(frame["risk_contribution_pct"], errors="coerce").sum()
    checks.append(
        _check(
            "risk_contribution_pct_sums_to_one",
            bool(np.isfinite(total) and abs(float(total) - 1.0) <= 1e-4),
            f"final_model={final_model}; risk_contribution_pct_sum={total}",
        )
    )


def _check_equity_scope(
    scores: pd.DataFrame,
    weights: pd.DataFrame,
    final_model: str,
    checks: list[dict[str, object]],
) -> None:
    frames = []
    if not scores.empty and {"ticker", "sleeve", "selection_flag"}.issubset(scores):
        frames.append(
            scores.loc[scores["selection_flag"].astype(bool), ["ticker", "sleeve"]]
        )
    if not weights.empty and {"ticker", "model_name"}.issubset(weights):
        final = weights.loc[
            weights["model_name"].astype(str).eq(final_model), ["ticker"]
        ]
        if not scores.empty and {"ticker", "sleeve"}.issubset(scores):
            final = final.merge(scores[["ticker", "sleeve"]], on="ticker", how="left")
        frames.append(final)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if combined.empty or "sleeve" not in combined:
        checks.append(
            _check("equity_scope_not_crypto_dominated", False, "missing scope evidence")
        )
        return
    crypto_ratio = (
        combined["sleeve"]
        .astype(str)
        .str.contains("crypto", case=False, na=False)
        .mean()
    )
    checks.append(
        _check(
            "equity_scope_not_crypto_dominated",
            bool(crypto_ratio <= 0.10),
            f"crypto_ratio={crypto_ratio}; rows={len(combined)}",
        )
    )


def _check_complete_claim_with_integrity(
    summary: dict[str, object],
    checks: list[dict[str, object]],
) -> None:
    status = str(summary.get("run_status", "")).lower()
    failed_so_far = [check for check in checks if not bool(check["passed"])]
    passed = not (status == "completed" and failed_so_far)
    checks.append(
        _check(
            "completed_summary_requires_numerical_integrity",
            passed,
            f"run_status={status}; failed_before_this={len(failed_so_far)}",
        )
    )


def _executable_models(league: pd.DataFrame) -> set[str]:
    if league.empty or not {"model_name", "actual_status"}.issubset(league):
        return set()
    frame = league.loc[
        league["actual_status"].astype(str).isin(EXECUTABLE_MODEL_STATUSES)
    ]
    return set(frame["model_name"].astype(str))


def _rows_for_models(frame: pd.DataFrame, models: set[str]) -> pd.DataFrame:
    if frame.empty or "model_name" not in frame or not models:
        return frame.head(0)
    return frame.loc[frame["model_name"].astype(str).isin(models)].copy()


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    present = [column for column in columns if column in frame]
    if not present:
        return pd.DataFrame()
    return frame[present].apply(pd.to_numeric, errors="coerce")


def _weights_for_model(weights: pd.DataFrame, model: str) -> pd.Series:
    if weights.empty or not {"ticker", "weight"}.issubset(weights):
        return pd.Series(dtype=float)
    frame = weights.copy()
    if "model_name" in frame:
        frame = frame.loc[frame["model_name"].astype(str).eq(str(model))]
    elif "Model" in frame:
        frame = frame.loc[frame["Model"].astype(str).eq(str(model))]
    if frame.empty:
        return pd.Series(dtype=float)
    return frame.set_index("ticker")["weight"].astype(float)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_returns(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return clean_returns_matrix(pd.read_csv(path))


def _float(value: object, *, default: float = np.nan) -> float:
    try:
        if value is None or pd.isna(value):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_max(series: pd.Series) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return float(clean.max()) if not clean.empty else None


def _check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "details": str(details)}
