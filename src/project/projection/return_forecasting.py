"""Return forecasting utilities for projection research."""

from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import roc_curve
from sklearn.tree import DecisionTreeRegressor

from project.constants import TRADING_DAYS_PER_YEAR

HORIZON_TO_DAYS = {1: 21, 3: 63, 6: 126, 12: 252}


def optional_model_status() -> dict[str, str]:
    """Report optional heavy model availability without importing them eagerly."""
    return {
        "xgboost": (
            "available" if importlib.util.find_spec("xgboost") else "not_available"
        ),
        "lightgbm": (
            "available" if importlib.util.find_spec("lightgbm") else "not_available"
        ),
        "tensorflow": (
            "available" if importlib.util.find_spec("tensorflow") else "not_available"
        ),
    }


def forecast_asset_returns(
    returns: pd.DataFrame,
    horizons_months: list[int] | None = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Forecast asset-level future returns with deterministic baseline models."""
    clean = (
        returns.apply(pd.to_numeric, errors="coerce")
        .dropna(how="all")
        .dropna(axis=1, how="all")
    )
    horizons = horizons_months or [1, 3, 6, 12]
    rows = []
    for asset in clean.columns:
        series = clean[asset].dropna().astype(float)
        features = _lag_features(series)
        for horizon in horizons:
            days = HORIZON_TO_DAYS[int(horizon)]
            target = _forward_compound_return(series, days)
            dataset = features.join(target.rename("target")).dropna()
            baseline = _baseline_forecasts(series, days)
            rows.extend(
                {
                    "Ticker": asset,
                    "Horizon_Months": int(horizon),
                    "Model": model,
                    "Forecast_Return": float(value),
                    "Status": "diagnostic_only_unvalidated",
                    "Task_Type": "regression",
                }
                for model, value in baseline.items()
            )
            rows.extend(
                _sklearn_forecast_rows(
                    asset,
                    int(horizon),
                    dataset,
                    features.dropna().tail(1),
                    random_state=random_state,
                )
            )
    return pd.DataFrame(rows)


def forecast_model_league(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Summarize forecast model availability and average forecast output."""
    if forecasts.empty:
        return pd.DataFrame(columns=["Model", "Status", "Task_Type", "Mean_Forecast"])
    league = (
        forecasts.groupby(["Model", "Status", "Task_Type"], as_index=False)[
            "Forecast_Return"
        ]
        .mean()
        .rename(columns={"Forecast_Return": "Mean_Forecast"})
    )
    optional_rows = [
        {
            "Model": name,
            "Status": status,
            "Task_Type": "regression",
            "Mean_Forecast": np.nan,
        }
        for name, status in optional_model_status().items()
        if status == "not_available"
    ]
    return pd.concat([league, pd.DataFrame(optional_rows)], ignore_index=True)


def downside_roc(returns: pd.DataFrame, horizon_days: int = 21) -> pd.DataFrame:
    """Build ROC points for a downside classification task only."""
    clean = returns.apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if clean.empty:
        return pd.DataFrame(columns=["fpr", "tpr", "threshold", "Task_Type"])
    portfolio = clean.mean(axis=1)
    realized = _forward_compound_return(portfolio, horizon_days)
    score = -_trailing_compound_return(portfolio, horizon_days)
    dataset = pd.concat(
        [realized.rename("target"), score.rename("score")], axis=1
    ).dropna()
    split = int(len(dataset) * 0.70)
    holdout = dataset.iloc[split:]
    if holdout.empty or holdout["target"].lt(0).nunique() < 2:
        return pd.DataFrame(columns=["fpr", "tpr", "threshold", "Task_Type"])
    fpr, tpr, thresholds = roc_curve(
        holdout["target"].lt(0).astype(int), holdout["score"]
    )
    return pd.DataFrame(
        {
            "fpr": fpr,
            "tpr": tpr,
            "threshold": thresholds,
            "Task_Type": "classification_downside_event",
        }
    )


def _baseline_forecasts(series: pd.Series, horizon_days: int) -> dict[str, float]:
    if len(series) < max(21, int(horizon_days)):
        return {"historical_mean": np.nan, "ewma_mean": np.nan}
    annual_mean = float(series.mean() * TRADING_DAYS_PER_YEAR)
    ewma_daily = float(
        series.ewm(span=min(63, max(5, len(series))), adjust=False).mean().iloc[-1]
    )
    return {
        "historical_mean": annual_mean * horizon_days / TRADING_DAYS_PER_YEAR,
        "ewma_mean": ewma_daily * horizon_days,
    }


def _lag_features(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lag_1": series.shift(1),
            "lag_5": series.rolling(5).mean().shift(1),
            "lag_21": series.rolling(21).mean().shift(1),
            "vol_21": series.rolling(21).std().shift(1),
        }
    )


def _sklearn_forecast_rows(
    asset: str,
    horizon: int,
    dataset: pd.DataFrame,
    latest_features: pd.DataFrame,
    random_state: int,
) -> list[dict[str, object]]:
    models = {
        "linear_regression": LinearRegression(),
        "ridge_regression": Ridge(alpha=1.0),
        "decision_tree": DecisionTreeRegressor(max_depth=3, random_state=random_state),
        "random_forest": RandomForestRegressor(
            n_estimators=25,
            max_depth=3,
            random_state=random_state,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            max_depth=2,
            random_state=random_state,
        ),
    }
    rows = []
    if len(dataset) < 30 or latest_features.empty:
        return [
            {
                "Ticker": asset,
                "Horizon_Months": horizon,
                "Model": name,
                "Forecast_Return": np.nan,
                "Status": "insufficient_history",
                "Task_Type": "regression",
            }
            for name in models
        ]
    x = dataset.drop(columns=["target"]).to_numpy(dtype=float)
    y = dataset["target"].to_numpy(dtype=float)
    latest = latest_features.to_numpy(dtype=float)
    for name, model in models.items():
        model.fit(x, y)
        rows.append(
            {
                "Ticker": asset,
                "Horizon_Months": horizon,
                "Model": name,
                "Forecast_Return": float(model.predict(latest)[0]),
                "Status": "diagnostic_only_unvalidated",
                "Task_Type": "regression",
            }
        )
    return rows


def _forward_compound_return(series: pd.Series, horizon_days: int) -> pd.Series:
    """Return the simple return from t+1 through t+h at each decision date t."""
    horizon = max(int(horizon_days), 1)
    return (1.0 + series).rolling(horizon).apply(np.prod, raw=True).shift(
        -horizon
    ) - 1.0


def _trailing_compound_return(series: pd.Series, horizon_days: int) -> pd.Series:
    horizon = max(int(horizon_days), 1)
    return (1.0 + series).rolling(horizon).apply(np.prod, raw=True) - 1.0
