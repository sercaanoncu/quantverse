"""QuantVerse v2 public-data return forecasting diagnostics.

Forecasts are research estimates, not trading signals. The module keeps a
random-walk baseline, uses chronological historical data only, and labels model
status explicitly so weak forecasts cannot be mistaken for advice.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from project.data_pipeline.security_identity import attach_run_metadata

TRADING_DAYS_BY_HORIZON = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}

FORECAST_COLUMNS = [
    "ticker",
    "horizon",
    "horizon_days",
    "expected_return_unit",
    "forecast_horizon_label",
    "annualization_method",
    "observations",
    "naive_random_walk_expected_return",
    "momentum_expected_return",
    "mean_reversion_expected_return",
    "rolling_mean_expected_return",
    "ridge_or_lasso_expected_return",
    "tree_or_boosting_expected_return",
    "ensemble_expected_return",
    "prediction_interval_low",
    "prediction_interval_high",
    "forecast_confidence",
    "forecast_confidence_method",
    "benchmark_random_walk_error",
    "rmse",
    "mae",
    "r2",
    "ridge_training_observations",
    "ridge_test_observations",
    "ridge_purge_observations",
    "ridge_prediction_as_of",
    "model_status",
    "diagnostic_warning",
    "extreme_expected_return_warning",
    "run_id",
    "execution_id",
    "data_as_of_date",
    "generated_at",
    "universe_snapshot_id",
    "data_snapshot_id",
    "config_hash",
    "input_fingerprint",
]


def build_return_forecasts(
    returns: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp | None = None,
    horizons: dict[str, int] | None = None,
    run_metadata: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Build transparent expected-return diagnostics for each asset/horizon."""
    clean = _clean_returns(returns, as_of_date=as_of_date)
    horizon_map = horizons or TRADING_DAYS_BY_HORIZON
    rows: list[dict[str, object]] = []
    for ticker in clean.columns:
        series = clean[ticker].dropna().astype(float)
        for horizon, days in horizon_map.items():
            rows.append(_forecast_one(ticker, series, horizon, int(days)))
    frame = pd.DataFrame(rows)
    frame = attach_run_metadata(frame, run_metadata)
    return frame.reindex(columns=FORECAST_COLUMNS)


def write_return_forecasts(forecasts: pd.DataFrame, output_path: str | Path) -> None:
    """Write forecasts with stable schema."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    forecasts.reindex(columns=FORECAST_COLUMNS).to_csv(path, index=False)


def _forecast_one(
    ticker: str,
    series: pd.Series,
    horizon: str,
    horizon_days: int,
) -> dict[str, object]:
    series = _forecast_safe_series(series)
    observations = int(series.shape[0])
    random_walk = 0.0
    momentum = (
        _period_return(series, horizon_days) if observations >= horizon_days else np.nan
    )
    mean_reversion = (
        -0.35 * _period_return(series, 21)
        if horizon_days == 21 and observations >= 21
        else np.nan
    )
    rolling_history = min(126, horizon_days)
    rolling_mean = (
        float(series.tail(rolling_history).mean() * horizon_days)
        if observations >= rolling_history
        else np.nan
    )
    ridge, errors = _ridge_forecast_and_errors(series, horizon_days)
    components = [random_walk, momentum, mean_reversion, rolling_mean]
    if np.isfinite(ridge):
        components.append(float(ridge))
    ensemble = float(np.nanmean(components)) if components else 0.0
    sigma = float(
        series.tail(min(252, observations)).std(ddof=1) * np.sqrt(horizon_days)
    )
    confidence = _forecast_confidence(observations, sigma)
    if np.isfinite(sigma):
        interval = 1.64 * sigma * (1.0 + (1.0 - confidence))
        low = max(-1.0, ensemble - interval)
        high = ensemble + interval
    else:
        low = np.nan
        high = np.nan
    status = (
        "diagnostic_only"
        if observations >= max(60, horizon_days)
        else "low_data_diagnostic"
    )
    warning = _warning(observations, sigma, errors, horizon_days=horizon_days)
    extreme_warning = _extreme_expected_return_warning(ensemble, horizon_days)
    return {
        "ticker": ticker,
        "horizon": horizon,
        "horizon_days": horizon_days,
        "expected_return_unit": "decimal cumulative simple return over forecast horizon",
        "forecast_horizon_label": f"{horizon_days} trading days",
        "annualization_method": "not annualized; horizon return estimated from trailing simple returns",
        "observations": observations,
        "naive_random_walk_expected_return": random_walk,
        "momentum_expected_return": float(momentum),
        "mean_reversion_expected_return": float(mean_reversion),
        "rolling_mean_expected_return": float(rolling_mean),
        "ridge_or_lasso_expected_return": (
            float(ridge) if np.isfinite(ridge) else np.nan
        ),
        "tree_or_boosting_expected_return": np.nan,
        "ensemble_expected_return": ensemble,
        "prediction_interval_low": float(low),
        "prediction_interval_high": float(high),
        "forecast_confidence": confidence,
        "forecast_confidence_method": (
            "heuristic_history_coverage_and_dispersion_score_not_probability"
        ),
        "benchmark_random_walk_error": errors.get("random_walk_mae", np.nan),
        "rmse": errors.get("rmse", np.nan),
        "mae": errors.get("mae", np.nan),
        "r2": errors.get("r2", np.nan),
        "ridge_training_observations": errors.get("training_observations", 0),
        "ridge_test_observations": errors.get("test_observations", 0),
        "ridge_purge_observations": errors.get("purge_observations", 0),
        "ridge_prediction_as_of": errors.get("prediction_as_of", ""),
        "model_status": status,
        "diagnostic_warning": warning,
        "extreme_expected_return_warning": extreme_warning,
    }


def _ridge_forecast_and_errors(
    series: pd.Series,
    horizon_days: int,
) -> tuple[float, dict[str, object]]:
    clean = series.dropna().astype(float)
    min_rows = max(90, horizon_days + 30)
    if clean.shape[0] < min_rows:
        return np.nan, {}
    features, target = _supervised_frame(clean, horizon_days)
    if features.empty or target.empty or len(features) < 40:
        return np.nan, {}
    split = max(int(len(features) * 0.70), len(features) - 60)
    split = min(split, len(features) - 10)
    purge_observations = int(horizon_days)
    train_end = split - purge_observations
    if train_end <= 30:
        return np.nan, {}
    train_x, test_x = features.iloc[:train_end], features.iloc[split:]
    train_y, test_y = target.iloc[:train_end], target.iloc[split:]
    if test_x.empty:
        return np.nan, {}
    model = Ridge(alpha=10.0)
    model.fit(train_x, train_y)
    predictions = pd.Series(model.predict(test_x), index=test_y.index)
    errors = predictions - test_y
    baseline_error = (pd.Series(0.0, index=test_y.index) - test_y).abs().mean()
    ss_res = float(((test_y - predictions) ** 2).sum())
    ss_tot = float(((test_y - test_y.mean()) ** 2).sum())
    latest_features = _feature_frame(clean).dropna()
    if latest_features.empty:
        return np.nan, {}
    latest = latest_features.iloc[[-1]]
    return float(model.predict(latest)[0]), {
        "rmse": float(np.sqrt((errors**2).mean())),
        "mae": float(errors.abs().mean()),
        "r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0,
        "random_walk_mae": float(baseline_error),
        "training_observations": int(len(train_x)),
        "test_observations": int(len(test_x)),
        "purge_observations": purge_observations,
        "prediction_as_of": latest.index[-1].date().isoformat(),
    }


def _supervised_frame(
    series: pd.Series,
    horizon_days: int,
) -> tuple[pd.DataFrame, pd.Series]:
    frame = _feature_frame(series)
    target = (1.0 + series).rolling(horizon_days).apply(np.prod, raw=True).shift(
        -horizon_days
    ) - 1.0
    combined = frame.join(target.rename("target")).dropna()
    if combined.empty:
        return pd.DataFrame(), pd.Series(dtype=float)
    return combined.drop(columns=["target"]), combined["target"]


def _feature_frame(series: pd.Series) -> pd.DataFrame:
    """Build features observable before each decision timestamp."""
    frame = pd.DataFrame(index=series.index)
    frame["lag_1"] = series.shift(1)
    frame["mean_21"] = series.shift(1).rolling(21).mean()
    frame["mean_63"] = series.shift(1).rolling(63).mean()
    frame["vol_63"] = series.shift(1).rolling(63).std()
    frame["mom_21"] = (1.0 + series.shift(1)).rolling(21).apply(np.prod, raw=True) - 1.0
    frame["mom_63"] = (1.0 + series.shift(1)).rolling(63).apply(np.prod, raw=True) - 1.0
    return frame


def _forecast_confidence(observations: int, sigma: float) -> float:
    coverage = min(float(observations) / 252.0, 1.0)
    risk_penalty = float(np.clip(sigma, 0.0, 1.0)) if np.isfinite(sigma) else 1.0
    return float(np.clip(0.15 + 0.75 * coverage - 0.25 * risk_penalty, 0.05, 0.95))


def _warning(
    observations: int,
    sigma: float,
    errors: dict[str, object],
    *,
    horizon_days: int,
) -> str:
    flags: list[str] = ["heuristic_uncalibrated_interval"]
    if int(horizon_days) != 21:
        flags.append("mean_reversion_component_not_applicable_beyond_1m")
    if observations < 126:
        flags.append("low_history")
    if sigma > 0.50:
        flags.append("wide_prediction_interval")
    if errors and np.isfinite(errors.get("r2", np.nan)) and errors["r2"] < 0:
        flags.append("ridge_underperforms_mean")
    if errors:
        flags.append("overlapping_horizon_labels_dependence")
    return "; ".join(flags) if flags else "forecast_is_diagnostic_not_advice"


def _extreme_expected_return_warning(ensemble: float, horizon_days: int) -> str:
    threshold = 1.0 if int(horizon_days) >= 252 else 0.50
    if abs(float(ensemble)) > threshold:
        return "extreme_horizon_expected_return_review_required"
    return "none"


def _period_return(series: pd.Series, window: int) -> float:
    clean = series.dropna().tail(max(int(window), 1))
    if clean.empty:
        return 0.0
    return float((1.0 + clean).prod() - 1.0)


def _clean_returns(
    returns: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(clean.columns[0])
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    if as_of_date is not None:
        clean = clean.loc[clean.index <= pd.Timestamp(as_of_date)]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.dropna(axis=1, how="all").dropna(how="all")


def _forecast_safe_series(series: pd.Series) -> pd.Series:
    """Validate simple returns without full-sample winsorization leakage."""
    clean = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if (clean < -1.0 - 1e-12).any():
        raise ValueError("Simple returns below -100% are invalid for forecasting.")
    return clean
