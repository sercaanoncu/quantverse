"""Global forecast helpers for research reporting."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)

from project.projection.return_forecasting import (
    downside_roc,
    forecast_asset_returns,
    forecast_model_league,
)


def run_global_forecasts(
    returns: pd.DataFrame,
    horizons_months: list[int],
    random_state: int = 42,
) -> dict[str, pd.DataFrame]:
    """Run lightweight deterministic forecast outputs."""
    forecasts = forecast_asset_returns(
        returns,
        horizons_months=horizons_months,
        random_state=random_state,
    )
    return {
        "model_league": forecast_model_league(forecasts),
        "regression_metrics": _regression_metrics(returns),
        "classification_metrics": _classification_metrics(returns),
        "time_series_metrics": _time_series_metrics(returns),
        "confusion_matrix": _confusion_matrix(returns),
        "roc_auc": _roc_auc(returns),
        "downside_roc_points": downside_roc(returns),
    }


def _regression_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    portfolio = _portfolio_return_series(returns)
    target = portfolio.shift(-1).dropna()
    prediction = (
        portfolio.rolling(21, min_periods=5).mean().shift(1).reindex(target.index)
    )
    dataset = pd.concat(
        [target.rename("target"), prediction.rename("prediction")], axis=1
    ).dropna()
    if dataset.empty:
        return pd.DataFrame(columns=["Model", "RMSE", "MAE", "R2", "Status"])
    y = dataset["target"]
    yhat = dataset["prediction"]
    return pd.DataFrame(
        [
            {
                "Model": "rolling_mean_past_only_baseline",
                "RMSE": float(np.sqrt(mean_squared_error(y, yhat))),
                "MAE": float(mean_absolute_error(y, yhat)),
                "R2": float(r2_score(y, yhat)),
                "Status": "historical_past_only_diagnostic",
            }
        ]
    )


def _classification_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    train_labels, train_scores, labels, scores = _downside_holdout(returns)
    if labels.nunique() < 2 or train_scores.empty:
        return pd.DataFrame(columns=["Model", "ROC_AUC", "F1", "Accuracy", "Status"])
    threshold = float(train_scores.median())
    predicted = (scores >= threshold).astype(int)
    return pd.DataFrame(
        [
            {
                "Model": "rolling_downside_score",
                "ROC_AUC": float(roc_auc_score(labels, scores)),
                "F1": float(f1_score(labels, predicted)),
                "Accuracy": float(accuracy_score(labels, predicted)),
                "Status": "chronological_holdout_diagnostic_only",
            }
        ]
    )


def _time_series_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Model": "random_walk_baseline",
                "Task_Type": "time_series_baseline",
                "AIC": np.nan,
                "BIC": np.nan,
                "Status": "computed_no_aic_bic_for_baseline",
            },
            {
                "Model": "ARIMA/GARCH",
                "Task_Type": "time_series_optional",
                "AIC": np.nan,
                "BIC": np.nan,
                "Status": "not_run_optional_dependency_and_model_selection_required",
            },
        ]
    )


def _confusion_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    _train_labels, train_scores, labels, scores = _downside_holdout(returns)
    if labels.nunique() < 2 or train_scores.empty:
        return pd.DataFrame(columns=["Actual", "Predicted", "Count"])
    predicted = (scores >= float(train_scores.median())).astype(int)
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    rows = []
    for actual in [0, 1]:
        for pred in [0, 1]:
            rows.append(
                {
                    "Actual": actual,
                    "Predicted": pred,
                    "Count": int(matrix[actual, pred]),
                }
            )
    return pd.DataFrame(rows)


def _roc_auc(returns: pd.DataFrame) -> pd.DataFrame:
    _train_labels, _train_scores, labels, scores = _downside_holdout(returns)
    if labels.nunique() < 2:
        auc = np.nan
        status = "insufficient_class_balance"
    else:
        auc = float(roc_auc_score(labels, scores))
        status = "chronological_holdout_diagnostic_only"
    return pd.DataFrame(
        [{"Model": "rolling_downside_score", "ROC_AUC": auc, "Status": status}]
    )


def _downside_labels_scores(returns: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    portfolio = _portfolio_return_series(returns)
    future = (1.0 + portfolio).rolling(21).apply(np.prod, raw=True).shift(-21) - 1.0
    trailing = (1.0 + portfolio).rolling(21).apply(np.prod, raw=True) - 1.0
    score = -trailing
    dataset = pd.concat(
        [future.rename("future"), score.rename("score")], axis=1
    ).dropna()
    return dataset["future"].lt(0).astype(int), dataset["score"].astype(float)


def _downside_holdout(
    returns: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    labels, scores = _downside_labels_scores(returns)
    split = int(len(labels) * 0.70)
    return (
        labels.iloc[:split],
        scores.iloc[:split],
        labels.iloc[split:],
        scores.iloc[split:],
    )


def _portfolio_return_series(returns: pd.DataFrame) -> pd.Series:
    clean = returns.apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if clean.empty:
        return pd.Series(dtype=float)
    return clean.mean(axis=1)
