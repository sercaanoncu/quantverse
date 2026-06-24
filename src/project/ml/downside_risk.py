"""Time-series validated downside-risk diagnostic model.

The module does not claim to forecast returns. It estimates whether recent
market state contains information about next-day downside events, using only
features observable before the predicted day and chronological validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass
class DownsideRiskResult:
    """Container for ML diagnostic outputs."""

    metrics: pd.DataFrame
    predictions: pd.DataFrame
    feature_importance: pd.DataFrame
    status: str
    reason: Optional[str] = None


def evaluate_downside_risk_model(
    returns: pd.DataFrame,
    market_signals: Optional[pd.DataFrame] = None,
    n_splits: int = 5,
    event_quantile: float = 0.10,
    event_lookback: int = 252,
    min_train_size: int = 504,
    random_seed: int = 42,
) -> DownsideRiskResult:
    """Evaluate a downside-risk classifier with chronological validation."""
    dataset = _build_dataset(
        returns=returns,
        market_signals=market_signals,
        event_quantile=event_quantile,
        event_lookback=event_lookback,
    )
    if dataset.empty:
        return DownsideRiskResult(
            metrics=_status_table("skipped", "no valid ML rows"),
            predictions=pd.DataFrame(),
            feature_importance=pd.DataFrame(),
            status="skipped",
            reason="no valid ML rows",
        )

    X = dataset.drop(columns=["target", "next_return", "event_threshold"])
    y = dataset["target"].astype(int)
    if len(dataset) < min_train_size + n_splits:
        reason = f"insufficient rows: {len(dataset)} < {min_train_size + n_splits}"
        return DownsideRiskResult(
            metrics=_status_table("skipped", reason),
            predictions=pd.DataFrame(),
            feature_importance=pd.DataFrame(),
            status="skipped",
            reason=reason,
        )
    if y.nunique() < 2:
        return DownsideRiskResult(
            metrics=_status_table("skipped", "only one target class"),
            predictions=pd.DataFrame(),
            feature_importance=pd.DataFrame(),
            status="skipped",
            reason="only one target class",
        )

    n_splits = min(n_splits, max(2, len(dataset) // min_train_size))
    splitter = TimeSeriesSplit(n_splits=n_splits)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=random_seed,
                ),
            ),
        ]
    )

    metrics_rows = []
    prediction_rows = []
    coef_rows = []

    for fold, (train_idx, test_idx) in enumerate(splitter.split(X), start=1):
        if len(train_idx) < min_train_size:
            continue
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue

        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.50).astype(int)

        fold_metrics = {
            "Fold": fold,
            "Train_Start": str(X_train.index[0].date()),
            "Train_End": str(X_train.index[-1].date()),
            "Test_Start": str(X_test.index[0].date()),
            "Test_End": str(X_test.index[-1].date()),
            "Train_Rows": int(len(X_train)),
            "Test_Rows": int(len(X_test)),
            "Positive_Rate": float(y_test.mean()),
            "Baseline_PR_AUC": float(y_test.mean()),
            "ROC_AUC": _safe_metric(roc_auc_score, y_test, proba),
            "PR_AUC": _safe_metric(average_precision_score, y_test, proba),
            "Brier": _safe_metric(brier_score_loss, y_test, proba),
            "Balanced_Accuracy": _safe_metric(balanced_accuracy_score, y_test, pred),
            "F1": _safe_metric(f1_score, y_test, pred),
        }
        metrics_rows.append(fold_metrics)

        prediction_rows.append(
            pd.DataFrame(
                {
                    "Fold": fold,
                    "Observed": y_test,
                    "Probability": proba,
                    "Prediction": pred,
                    "Next_Return": dataset.loc[X_test.index, "next_return"],
                    "Event_Threshold": dataset.loc[X_test.index, "event_threshold"],
                },
                index=X_test.index,
            )
        )

        coef = model.named_steps["model"].coef_[0]
        coef_rows.append(
            pd.DataFrame(
                {
                    "Fold": fold,
                    "Feature": X.columns,
                    "Coefficient": coef,
                    "Abs_Coefficient": np.abs(coef),
                }
            )
        )

    if not metrics_rows:
        reason = "no fold had both classes with the required training window"
        return DownsideRiskResult(
            metrics=_status_table("skipped", reason),
            predictions=pd.DataFrame(),
            feature_importance=pd.DataFrame(),
            status="skipped",
            reason=reason,
        )

    metrics = pd.DataFrame(metrics_rows)
    summary = metrics.select_dtypes("number").mean(numeric_only=True).to_dict()
    summary.update(
        {
            "Fold": "mean",
            "Train_Start": "",
            "Train_End": "",
            "Test_Start": str(dataset.index[0].date()),
            "Test_End": str(dataset.index[-1].date()),
            "Status": "evaluated",
            "Model": "balanced_logistic_regression",
        }
    )
    metrics["Status"] = "evaluated"
    metrics["Model"] = "balanced_logistic_regression"
    metrics = pd.concat([metrics, pd.DataFrame([summary])], ignore_index=True)
    metrics["Fold"] = metrics["Fold"].astype(str)
    predictions = pd.concat(prediction_rows).sort_index()
    importance = (
        pd.concat(coef_rows)
        .groupby("Feature", as_index=False)
        .agg(
            Coefficient=("Coefficient", "mean"),
            Abs_Coefficient=("Abs_Coefficient", "mean"),
        )
        .sort_values("Abs_Coefficient", ascending=False)
    )
    return DownsideRiskResult(
        metrics=metrics,
        predictions=predictions,
        feature_importance=importance,
        status="evaluated",
    )


def save_downside_risk_figures(
    result: DownsideRiskResult,
    figures_dir: str | Path,
) -> Dict[str, str]:
    """Save feature-importance and calibration-style diagnostic figures."""
    if result.status != "evaluated" or result.predictions.empty:
        return {}

    import matplotlib.pyplot as plt

    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}

    fig, ax = plt.subplots(figsize=(8, 4.5))
    top = result.feature_importance.head(12).sort_values("Abs_Coefficient")
    ax.barh(top["Feature"], top["Abs_Coefficient"], color="#2f6f8f")
    ax.set_title("Downside-risk diagnostic feature importance")
    ax.set_xlabel("Mean absolute logistic coefficient")
    fig.tight_layout()
    path = figures_dir / "ml_downside_feature_importance.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    paths["feature_importance"] = str(path)

    pred = result.predictions.copy()
    pred["Bucket"] = pd.qcut(pred["Probability"], q=5, duplicates="drop")
    calibration = pred.groupby("Bucket", observed=True).agg(
        Mean_Probability=("Probability", "mean"),
        Observed_Rate=("Observed", "mean"),
        Count=("Observed", "size"),
    )
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(
        calibration["Mean_Probability"],
        calibration["Observed_Rate"],
        marker="o",
        color="#7a3e2c",
    )
    ax.plot([0, 1], [0, 1], linestyle="--", color="#777777", linewidth=1)
    ax.set_xlim(0, max(0.5, calibration["Mean_Probability"].max() + 0.05))
    ax.set_ylim(0, max(0.5, calibration["Observed_Rate"].max() + 0.05))
    ax.set_title("Downside-risk probability calibration")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed event rate")
    fig.tight_layout()
    path = figures_dir / "ml_downside_calibration.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    paths["calibration"] = str(path)

    return paths


def _build_dataset(
    returns: pd.DataFrame,
    market_signals: Optional[pd.DataFrame],
    event_quantile: float,
    event_lookback: int,
) -> pd.DataFrame:
    returns = returns.sort_index().dropna(how="all")
    portfolio_returns = returns.mean(axis=1).dropna()
    cumulative = (1 + portfolio_returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1

    features = pd.DataFrame(index=portfolio_returns.index)
    features["ret_1d"] = portfolio_returns
    features["ret_5d"] = portfolio_returns.rolling(5).sum()
    features["ret_21d"] = portfolio_returns.rolling(21).sum()
    features["vol_21d"] = portfolio_returns.rolling(21).std() * np.sqrt(252)
    features["vol_63d"] = portfolio_returns.rolling(63).std() * np.sqrt(252)
    features["drawdown"] = drawdown
    features["cross_section_dispersion"] = returns.reindex(features.index).std(axis=1)
    features["positive_asset_share"] = (returns.reindex(features.index) > 0).mean(
        axis=1
    )

    if market_signals is not None and not market_signals.empty:
        signals = market_signals.sort_index().reindex(features.index).ffill()
        for col in signals.columns:
            safe_col = col.replace("^", "").replace("-", "_").replace(".", "_")
            features[f"signal_{safe_col}_level"] = signals[col]
            features[f"signal_{safe_col}_5d_change"] = signals[col].diff(5)

    threshold = (
        portfolio_returns.rolling(
            event_lookback, min_periods=max(63, event_lookback // 2)
        )
        .quantile(event_quantile)
        .shift(1)
    )
    next_return = portfolio_returns.shift(-1)
    target = (next_return <= threshold).astype(float)

    dataset = features.copy()
    dataset["target"] = target
    dataset["next_return"] = next_return
    dataset["event_threshold"] = threshold
    dataset = dataset.replace([np.inf, -np.inf], np.nan).dropna()
    return dataset


def _safe_metric(metric_fn, y_true, values) -> float:
    try:
        return float(metric_fn(y_true, values))
    except ValueError:
        return float("nan")


def _status_table(status: str, reason: str) -> pd.DataFrame:
    return pd.DataFrame([{"Status": status, "Reason": reason}])
