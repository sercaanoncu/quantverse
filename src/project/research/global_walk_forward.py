"""Public-data current-universe walk-forward validation for QuantVerse v2."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_portfolio_league import build_portfolio_league
from project.research.global_portfolio_risk import evaluate_return_series
from project.research.global_return_forecasting import build_return_forecasts
from project.research.global_stock_scoring import build_global_stock_scores


def run_public_data_walk_forward(
    returns: pd.DataFrame,
    universe: pd.DataFrame,
    *,
    train_window_days: int = 252,
    test_window_days: int = 21,
    step_days: int = 21,
    max_assets: int = 30,
    max_weight: float = 0.10,
    transaction_cost_bps: float = 10.0,
    random_state: int = 42,
    max_folds: int | None = 12,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run current-universe public-data walk-forward research validation."""
    clean = _clean_returns(returns)
    if clean.shape[0] < train_window_days + test_window_days:
        summary = {
            "walk_forward_status": "insufficient_history",
            "reason": "Not enough observations for configured train/test windows.",
        }
        empty = pd.DataFrame()
        return {
            "validation": empty,
            "returns": empty,
            "weights": empty,
            "turnover": empty,
            "model_comparison": empty,
            "summary": summary,
        }

    validation_rows: list[dict[str, object]] = []
    return_frames: list[pd.DataFrame] = []
    weight_rows: list[dict[str, object]] = []
    turnover_rows: list[dict[str, object]] = []
    previous_weights: dict[str, pd.Series] = {}
    fold = 0
    starts = list(
        range(0, clean.shape[0] - train_window_days - test_window_days + 1, step_days)
    )
    if max_folds is not None and max_folds > 0:
        starts = starts[-int(max_folds) :]
    for start in starts:
        train = clean.iloc[start : start + train_window_days]
        test = clean.iloc[
            start + train_window_days : start + train_window_days + test_window_days
        ]
        if train.empty or test.empty:
            continue
        as_of_date = train.index.max()
        scores = build_global_stock_scores(
            train,
            universe,
            as_of_date=as_of_date,
            max_selected=max_assets,
        )
        selected_for_fold = (
            scores.loc[scores["selection_flag"].astype(bool), "ticker"]
            .astype(str)
            .tolist()
        )
        selected_for_fold = [
            ticker for ticker in selected_for_fold if ticker in train.columns
        ][:max_assets]
        if not selected_for_fold:
            continue
        train_subset = train[selected_for_fold]
        universe_subset = universe.loc[
            universe["ticker"].astype(str).isin(selected_for_fold)
        ].copy()
        scores = scores.loc[scores["ticker"].astype(str).isin(selected_for_fold)].copy()
        forecasts = build_return_forecasts(
            train_subset,
            as_of_date=as_of_date,
            horizons={"12M": 252},
        )
        league, weights, status = build_portfolio_league(
            train_subset,
            scores,
            forecasts,
            universe_subset,
            max_assets=max_assets,
            max_weight=max_weight,
            random_state=random_state + fold,
        )
        run_models = status.loc[
            status["actual_status"].isin(
                ["actually_run", "benchmark_only", "diagnostic_only"]
            ),
            "model_name",
        ].astype(str)
        for model in run_models:
            model_weights = _weights_for_model(weights, model)
            if model_weights.empty:
                continue
            aligned = model_weights.reindex(test.columns).fillna(0.0)
            if aligned.sum() <= 0:
                continue
            aligned = aligned / aligned.sum()
            test_returns = test @ aligned
            net_returns = _apply_transaction_costs(
                test_returns,
                aligned,
                previous_weights.get(model),
                transaction_cost_bps=transaction_cost_bps,
            )
            previous = previous_weights.get(model, pd.Series(0.0, index=aligned.index))
            turnover = float(
                (aligned - previous.reindex(aligned.index).fillna(0.0)).abs().sum()
            )
            previous_weights[model] = aligned
            validation_rows.append(
                {
                    "fold": fold,
                    "model_name": model,
                    "train_start": train.index.min(),
                    "train_end": train.index.max(),
                    "test_start": test.index.min(),
                    "test_end": test.index.max(),
                    "train_observations": int(train.shape[0]),
                    "test_observations": int(test.shape[0]),
                    "turnover": turnover,
                    "transaction_cost_bps": transaction_cost_bps,
                    **evaluate_return_series(net_returns),
                    "limitation": "current-universe public-data walk-forward, not institutional PIT backtest",
                }
            )
            return_frames.append(
                pd.DataFrame(
                    {
                        "Date": net_returns.index,
                        "fold": fold,
                        "model_name": model,
                        "return": net_returns.values,
                    }
                )
            )
            weight_rows.extend(
                {
                    "fold": fold,
                    "rebalance_date": as_of_date,
                    "model_name": model,
                    "ticker": ticker,
                    "weight": float(weight),
                }
                for ticker, weight in aligned.items()
                if abs(weight) > 1e-12
            )
            turnover_rows.append(
                {
                    "fold": fold,
                    "model_name": model,
                    "rebalance_date": as_of_date,
                    "turnover": turnover,
                    "transaction_cost_bps": transaction_cost_bps,
                }
            )
        fold += 1
    validation = pd.DataFrame(validation_rows)
    returns_long = (
        pd.concat(return_frames, ignore_index=True) if return_frames else pd.DataFrame()
    )
    weights_long = pd.DataFrame(weight_rows)
    turnover = pd.DataFrame(turnover_rows)
    comparison = _comparison(validation)
    summary = _summary(comparison, validation)
    return {
        "validation": validation,
        "returns": returns_long,
        "weights": weights_long,
        "turnover": turnover,
        "model_comparison": comparison,
        "summary": summary,
    }


def write_walk_forward_outputs(
    result: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: str | Path,
) -> None:
    """Write walk-forward outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    result["validation"].to_csv(
        path / "global_walk_forward_validation.csv", index=False
    )
    result["returns"].to_csv(path / "global_walk_forward_returns.csv", index=False)
    result["weights"].to_csv(path / "global_walk_forward_weights.csv", index=False)
    result["turnover"].to_csv(path / "global_walk_forward_turnover.csv", index=False)
    result["model_comparison"].to_csv(
        path / "global_walk_forward_model_comparison.csv", index=False
    )
    (path / "global_walk_forward_summary.json").write_text(
        json.dumps(result["summary"], indent=2, default=str),
        encoding="utf-8",
    )


def _weights_for_model(weights: pd.DataFrame, model: str) -> pd.Series:
    if weights.empty:
        return pd.Series(dtype=float)
    frame = weights.loc[weights["model_name"].astype(str).eq(model)]
    if frame.empty:
        return pd.Series(dtype=float)
    return frame.set_index("ticker")["weight"].astype(float)


def _apply_transaction_costs(
    returns: pd.Series,
    weights: pd.Series,
    previous_weights: pd.Series | None,
    *,
    transaction_cost_bps: float,
) -> pd.Series:
    if previous_weights is None:
        previous = pd.Series(0.0, index=weights.index)
    else:
        previous = previous_weights.reindex(weights.index).fillna(0.0)
    turnover = float((weights - previous).abs().sum())
    cost = turnover * float(transaction_cost_bps) / 10000.0
    adjusted = returns.copy()
    if not adjusted.empty:
        adjusted.iloc[0] = adjusted.iloc[0] - cost
    return adjusted


def _comparison(validation: pd.DataFrame) -> pd.DataFrame:
    if validation.empty:
        return pd.DataFrame()
    grouped = validation.groupby("model_name", as_index=False).agg(
        folds=("fold", "nunique"),
        avg_cagr=("cagr", "mean"),
        avg_annualized_return=("annualized_return", "mean"),
        avg_volatility=("annualized_volatility", "mean"),
        avg_sharpe=("sharpe", "mean"),
        avg_sortino=("sortino", "mean"),
        avg_max_drawdown=("max_drawdown", "mean"),
        avg_cvar_95=("cvar_95", "mean"),
        avg_turnover=("turnover", "mean"),
    )
    ew = grouped.loc[grouped["model_name"].eq("Equal Weight")]
    if ew.empty:
        grouped["beats_equal_weight_avg_sharpe"] = False
        grouped["beats_equal_weight_avg_cagr"] = False
    else:
        ew_row = ew.iloc[0]
        grouped["beats_equal_weight_avg_sharpe"] = (
            grouped["avg_sharpe"] > ew_row["avg_sharpe"]
        )
        grouped["beats_equal_weight_avg_cagr"] = (
            grouped["avg_cagr"] > ew_row["avg_cagr"]
        )
    return grouped.sort_values(["avg_sharpe", "avg_cagr"], ascending=False)


def _summary(comparison: pd.DataFrame, validation: pd.DataFrame) -> dict[str, object]:
    if comparison.empty:
        return {
            "walk_forward_status": "not_run",
            "reason": "No valid walk-forward folds.",
        }
    best = comparison.iloc[0]
    return {
        "walk_forward_status": "completed_public_data_current_universe",
        "folds": int(validation["fold"].nunique()) if not validation.empty else 0,
        "best_model": str(best["model_name"]),
        "best_model_avg_sharpe": float(best["avg_sharpe"]),
        "equal_weight_comparison": {
            "beats_equal_weight_avg_sharpe": bool(
                best.get("beats_equal_weight_avg_sharpe", False)
            ),
            "beats_equal_weight_avg_cagr": bool(
                best.get("beats_equal_weight_avg_cagr", False)
            ),
        },
        "limitation": "Current public-provider universe only; not point-in-time institutional backtest.",
    }


def _clean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(clean.columns[0])
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.dropna(axis=1, how="all").dropna(how="all")
