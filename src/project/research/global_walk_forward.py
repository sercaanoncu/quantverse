"""Public-data current-universe walk-forward validation for QuantVerse v2."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR
from project.data_pipeline.security_identity import (
    build_feature_history_eligibility,
    resolve_security_master_rows,
)
from project.research.global_numerical_integrity import portfolio_return_series
from project.research.global_portfolio_league import build_portfolio_league
from project.research.global_portfolio_risk import evaluate_return_series
from project.research.global_return_forecasting import build_return_forecasts
from project.research.global_stock_scoring import build_global_stock_scores
from project.research.global_stock_selection import apply_max_weight_cap


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
    default_scope: str = "equity_only",
    include_crypto: bool = False,
    security_identity_audit: pd.DataFrame | None = None,
    minimum_standard_observations: int = 252,
    risk_free_rate_annual: float = 0.0,
    risk_free_policy: str = "zero_rate_labeled_research_assumption",
    random_benchmark_portfolios: int = 250,
    uncertainty_bootstrap_samples: int = 500,
    uncertainty_block_length: int = 21,
    uncertainty_confidence_level: float = 0.95,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run current-universe public-data walk-forward research validation."""
    clean = _clean_returns(returns)
    scoped_tickers = _scope_tickers(
        universe,
        default_scope=default_scope,
        include_crypto=include_crypto,
    )
    available_scoped = [ticker for ticker in scoped_tickers if ticker in clean]
    if available_scoped:
        clean = clean[available_scoped].dropna(how="all")
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
            "leakage_audit": empty,
            "window_summary": empty,
            "model_comparison": empty,
            "random_distribution": empty,
            "uncertainty": empty,
            "summary": summary,
        }

    validation_rows: list[dict[str, object]] = []
    return_frames: list[pd.DataFrame] = []
    weight_rows: list[dict[str, object]] = []
    turnover_rows: list[dict[str, object]] = []
    leakage_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []
    previous_weights: dict[str, pd.Series] = {}
    previous_random_weights: dict[int, pd.Series] = {}
    random_return_frames: list[pd.DataFrame] = []
    random_turnover_rows: list[dict[str, object]] = []
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
        feature_eligibility = build_feature_history_eligibility(
            train,
            security_identity_audit,
            minimum_standard_observations=minimum_standard_observations,
        )
        scores = build_global_stock_scores(
            train,
            universe,
            as_of_date=as_of_date,
            max_selected=max_assets,
            default_scope=default_scope,
            include_crypto=include_crypto,
            feature_history_eligibility=feature_eligibility,
            minimum_standard_observations=minimum_standard_observations,
        )
        selected_for_fold = (
            scores.loc[scores["selection_flag"].map(_truthy), "ticker"]
            .astype(str)
            .tolist()
        )
        selected_for_fold = [
            ticker for ticker in selected_for_fold if ticker in train.columns
        ][:max_assets]
        if not selected_for_fold:
            continue
        window_rows.append(
            {
                "fold": fold,
                "train_start": train.index.min(),
                "train_end": train.index.max(),
                "test_start": test.index.min(),
                "test_end": test.index.max(),
                "train_observations": int(train.shape[0]),
                "test_observations": int(test.shape[0]),
                "selected_count": int(len(selected_for_fold)),
                "selected_tickers": ";".join(selected_for_fold),
                "standard_scoring_eligible_count": int(
                    scores["standard_composite_score_eligible"].map(_truthy).sum()
                ),
                "short_history_diagnostic_count": int(
                    scores["eligibility_status"]
                    .astype(str)
                    .eq("diagnostic_short_history")
                    .sum()
                ),
            }
        )
        leakage_rows.extend(
            _leakage_audit_rows(
                fold=fold,
                train=train,
                test=test,
                scores=scores,
                selected_tickers=selected_for_fold,
            )
        )
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
            risk_free_rate_annual=risk_free_rate_annual,
            risk_free_policy=risk_free_policy,
        )
        _append_random_oos_fold(
            test,
            selected_for_fold,
            fold=fold,
            max_weight=max_weight,
            transaction_cost_bps=transaction_cost_bps,
            random_state=random_state,
            portfolio_count=random_benchmark_portfolios,
            previous_weights=previous_random_weights,
            return_frames=random_return_frames,
            turnover_rows=random_turnover_rows,
        )
        run_models = status.loc[
            status["actual_status"].isin(
                ["actually_run", "benchmark_only", "diagnostic_only"]
            ),
            "model_name",
        ].astype(str)
        for model in run_models:
            status_row = status.loc[status["model_name"].astype(str).eq(model)]
            model_status = (
                str(status_row["actual_status"].iloc[0])
                if not status_row.empty
                else "not_available"
            )
            model_weights = _weights_for_model(weights, model)
            if model_weights.empty:
                continue
            test_returns = portfolio_return_series(test, model_weights)
            aligned = model_weights.reindex(test.columns).fillna(0.0)
            if aligned.sum() <= 0:
                continue
            aligned = aligned / aligned.sum()
            if test_returns.empty:
                continue
            net_returns = _apply_transaction_costs(
                test_returns,
                aligned,
                previous_weights.get(model),
                transaction_cost_bps=transaction_cost_bps,
            )
            turnover = _two_way_turnover(aligned, previous_weights.get(model))
            previous_weights[model] = aligned
            validation_rows.append(
                {
                    "fold": fold,
                    "model_name": model,
                    "model_status": model_status,
                    "train_start": train.index.min(),
                    "train_end": train.index.max(),
                    "test_start": test.index.min(),
                    "test_end": test.index.max(),
                    "train_observations": int(train.shape[0]),
                    "test_observations": int(test.shape[0]),
                    "turnover": turnover,
                    "transaction_cost_bps": transaction_cost_bps,
                    "risk_free_rate_annual": float(risk_free_rate_annual),
                    "risk_free_policy": str(risk_free_policy),
                    **evaluate_return_series(
                        net_returns,
                        risk_free_rate_annual=risk_free_rate_annual,
                    ),
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
                    "transaction_cost_decimal": turnover
                    * float(transaction_cost_bps)
                    / 10000.0,
                }
            )
        fold += 1
    validation = pd.DataFrame(validation_rows)
    returns_long = (
        pd.concat(return_frames, ignore_index=True) if return_frames else pd.DataFrame()
    )
    weights_long = pd.DataFrame(weight_rows)
    turnover = pd.DataFrame(turnover_rows)
    leakage_audit = pd.DataFrame(leakage_rows)
    window_summary = pd.DataFrame(window_rows)
    comparison = _comparison(validation, returns_long)
    uncertainty = _paired_block_bootstrap_uncertainty(
        returns_long,
        risk_free_rate_annual=risk_free_rate_annual,
        samples=uncertainty_bootstrap_samples,
        block_length=uncertainty_block_length,
        confidence_level=uncertainty_confidence_level,
        random_state=random_state,
    )
    if not comparison.empty and not uncertainty.empty:
        comparison = comparison.merge(
            uncertainty,
            on="model_name",
            how="left",
            validate="one_to_one",
        )
    random_returns_long = (
        pd.concat(random_return_frames, ignore_index=True)
        if random_return_frames
        else pd.DataFrame()
    )
    random_distribution = _random_oos_distribution(
        random_returns_long,
        pd.DataFrame(random_turnover_rows),
        risk_free_rate_annual=risk_free_rate_annual,
    )
    summary = _summary(comparison, validation, leakage_audit)
    summary["random_benchmark_status"] = (
        "walk_forward_oos_net" if not random_distribution.empty else "not_available"
    )
    summary["random_benchmark_portfolios"] = int(len(random_distribution))
    summary["uncertainty_status"] = (
        "paired_circular_block_bootstrap" if not uncertainty.empty else "not_available"
    )
    summary["uncertainty_bootstrap_samples"] = int(uncertainty_bootstrap_samples)
    summary["uncertainty_block_length"] = int(uncertainty_block_length)
    return {
        "validation": validation,
        "returns": returns_long,
        "weights": weights_long,
        "turnover": turnover,
        "leakage_audit": leakage_audit,
        "window_summary": window_summary,
        "model_comparison": comparison,
        "random_distribution": random_distribution,
        "uncertainty": uncertainty,
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
    result["leakage_audit"].to_csv(
        path / "global_walk_forward_leakage_audit.csv", index=False
    )
    result["window_summary"].to_csv(
        path / "global_walk_forward_window_summary.csv", index=False
    )
    result["model_comparison"].to_csv(
        path / "global_walk_forward_model_comparison.csv", index=False
    )
    result["random_distribution"].to_csv(
        path / "global_walk_forward_random_distribution.csv", index=False
    )
    result["uncertainty"].to_csv(
        path / "global_walk_forward_uncertainty.csv", index=False
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
    turnover = _two_way_turnover(weights, previous_weights)
    cost = turnover * float(transaction_cost_bps) / 10000.0
    adjusted = returns.copy()
    if not adjusted.empty:
        adjusted.iloc[0] = adjusted.iloc[0] - cost
    return adjusted


def _two_way_turnover(
    weights: pd.Series,
    previous_weights: pd.Series | None,
) -> float:
    """Return L1 rebalance turnover, including purchases and exited positions."""
    current = weights.astype(float)
    previous = (
        pd.Series(dtype=float)
        if previous_weights is None
        else previous_weights.astype(float)
    )
    union = current.index.union(previous.index)
    return float(
        (
            current.reindex(union, fill_value=0.0)
            - previous.reindex(union, fill_value=0.0)
        )
        .abs()
        .sum()
    )


def _append_random_oos_fold(
    test: pd.DataFrame,
    selected_tickers: list[str],
    *,
    fold: int,
    max_weight: float,
    transaction_cost_bps: float,
    random_state: int,
    portfolio_count: int,
    previous_weights: dict[int, pd.Series],
    return_frames: list[pd.DataFrame],
    turnover_rows: list[dict[str, object]],
) -> None:
    if portfolio_count <= 0 or not selected_tickers:
        return
    if float(max_weight) * len(selected_tickers) < 1.0 - 1e-12:
        return
    rng = np.random.default_rng(int(random_state) + 100_000 + int(fold))
    for portfolio_id in range(int(portfolio_count)):
        raw = pd.Series(
            rng.random(len(selected_tickers)),
            index=selected_tickers,
            dtype=float,
        )
        target = apply_max_weight_cap(raw, max_weight)
        aligned = target.reindex(test.columns).fillna(0.0)
        gross_returns = portfolio_return_series(test, aligned)
        if gross_returns.empty:
            continue
        previous = previous_weights.get(portfolio_id)
        net_returns = _apply_transaction_costs(
            gross_returns,
            aligned,
            previous,
            transaction_cost_bps=transaction_cost_bps,
        )
        turnover = _two_way_turnover(aligned, previous)
        previous_weights[portfolio_id] = aligned
        return_frames.append(
            pd.DataFrame(
                {
                    "Date": net_returns.index,
                    "fold": fold,
                    "portfolio_id": portfolio_id,
                    "return": net_returns.to_numpy(dtype=float),
                }
            )
        )
        turnover_rows.append(
            {
                "fold": fold,
                "portfolio_id": portfolio_id,
                "turnover": turnover,
                "transaction_cost_bps": float(transaction_cost_bps),
            }
        )


def _random_oos_distribution(
    returns_long: pd.DataFrame,
    turnover: pd.DataFrame,
    *,
    risk_free_rate_annual: float,
) -> pd.DataFrame:
    if returns_long.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    turnover_map = (
        turnover.groupby("portfolio_id")["turnover"].mean().to_dict()
        if not turnover.empty
        else {}
    )
    for portfolio_id, group in returns_long.groupby("portfolio_id", sort=True):
        ordered = group.sort_values(["Date", "fold"])
        dates = pd.to_datetime(ordered["Date"], errors="coerce")
        if dates.duplicated().any():
            raise ValueError(
                "Random walk-forward benchmark contains overlapping OOS dates."
            )
        series = pd.Series(
            pd.to_numeric(ordered["return"], errors="coerce").to_numpy(),
            index=dates,
            dtype=float,
        ).dropna()
        metrics = evaluate_return_series(
            series,
            risk_free_rate_annual=risk_free_rate_annual,
        )
        rows.append(
            {
                "portfolio_id": int(portfolio_id),
                "folds": int(group["fold"].nunique()),
                "avg_turnover": float(turnover_map.get(portfolio_id, np.nan)),
                "benchmark_scope": "walk_forward_oos_net",
                "sampling_method": (
                    "iid_uniform_raw_scores_projected_to_capped_simplex"
                ),
                "cagr": float(metrics["cagr"]),
                "annualized_return": float(metrics["annualized_return"]),
                "volatility": float(metrics["annualized_volatility"]),
                "sharpe": float(metrics["sharpe"]),
                "sortino": float(metrics["sortino"]),
                "max_drawdown": float(metrics["max_drawdown"]),
                "var_95": float(metrics["var_95"]),
                "cvar_95": float(metrics["cvar_95"]),
                "calmar": float(metrics["calmar"]),
                "total_return": float(metrics["total_return"]),
            }
        )
    return pd.DataFrame(rows)


def _paired_block_bootstrap_uncertainty(
    returns_long: pd.DataFrame,
    *,
    risk_free_rate_annual: float,
    samples: int,
    block_length: int,
    confidence_level: float,
    random_state: int,
) -> pd.DataFrame:
    """Estimate paired OOS model-minus-EW uncertainty with circular blocks."""
    columns = [
        "model_name",
        "uncertainty_status",
        "uncertainty_method",
        "paired_observations",
        "bootstrap_samples",
        "block_length",
        "confidence_level",
        "annual_return_diff_ci_lower",
        "annual_return_diff_ci_upper",
        "probability_annual_return_improvement",
        "sharpe_diff_ci_lower",
        "sharpe_diff_ci_upper",
        "probability_sharpe_improvement",
    ]
    if (
        returns_long.empty
        or int(samples) <= 0
        or int(block_length) <= 0
        or not 0.0 < float(confidence_level) < 1.0
    ):
        return pd.DataFrame(columns=columns)
    required = {"Date", "model_name", "return"}
    if not required.issubset(returns_long.columns):
        return pd.DataFrame(columns=columns)
    frame = returns_long[list(required)].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["return"] = pd.to_numeric(frame["return"], errors="coerce")
    frame = frame.dropna(subset=["Date", "model_name", "return"])
    pivot = frame.pivot(
        index="Date", columns="model_name", values="return"
    ).sort_index()
    if "Equal Weight" not in pivot:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    alpha = (1.0 - float(confidence_level)) / 2.0
    daily_hurdle = (1.0 + float(risk_free_rate_annual)) ** (
        1.0 / TRADING_DAYS_PER_YEAR
    ) - 1.0
    for model_number, model in enumerate(sorted(map(str, pivot.columns))):
        if model == "Equal Weight":
            rows.append(
                {
                    "model_name": model,
                    "uncertainty_status": ("benchmark_self_comparison_not_applicable"),
                    "uncertainty_method": "paired_circular_block_bootstrap",
                    "paired_observations": int(pivot[model].notna().sum()),
                    "bootstrap_samples": int(samples),
                    "block_length": int(block_length),
                    "confidence_level": float(confidence_level),
                }
            )
            continue
        paired = pivot[[model, "Equal Weight"]].dropna()
        n_observations = int(len(paired))
        if n_observations < max(20, int(block_length) * 2):
            rows.append(
                {
                    "model_name": model,
                    "uncertainty_status": "insufficient_paired_oos_history",
                    "uncertainty_method": "paired_circular_block_bootstrap",
                    "paired_observations": n_observations,
                    "bootstrap_samples": int(samples),
                    "block_length": int(block_length),
                    "confidence_level": float(confidence_level),
                }
            )
            continue
        model_returns = paired[model].to_numpy(dtype=float)
        benchmark_returns = paired["Equal Weight"].to_numpy(dtype=float)
        rng = np.random.default_rng(int(random_state) + 200_000 + model_number * 1009)
        n_blocks = int(np.ceil(n_observations / int(block_length)))
        starts = rng.integers(
            0,
            n_observations,
            size=(int(samples), n_blocks),
        )
        offsets = np.arange(int(block_length))
        indices = (
            (starts[:, :, None] + offsets[None, None, :]) % n_observations
        ).reshape(int(samples), -1)[:, :n_observations]
        model_samples = model_returns[indices]
        benchmark_samples = benchmark_returns[indices]
        annual_return_diff = (
            model_samples.mean(axis=1) - benchmark_samples.mean(axis=1)
        ) * TRADING_DAYS_PER_YEAR
        model_sharpe = _bootstrap_sharpe(model_samples, daily_hurdle)
        benchmark_sharpe = _bootstrap_sharpe(benchmark_samples, daily_hurdle)
        sharpe_diff = model_sharpe - benchmark_sharpe
        valid_sharpe = sharpe_diff[np.isfinite(sharpe_diff)]
        if valid_sharpe.size < max(30, int(samples) // 2):
            status = "insufficient_finite_bootstrap_statistics"
            sharpe_low = np.nan
            sharpe_high = np.nan
            sharpe_probability = np.nan
        else:
            status = "completed"
            sharpe_low, sharpe_high = np.quantile(
                valid_sharpe,
                [alpha, 1.0 - alpha],
            )
            sharpe_probability = float((valid_sharpe > 0.0).mean())
        annual_low, annual_high = np.quantile(
            annual_return_diff,
            [alpha, 1.0 - alpha],
        )
        rows.append(
            {
                "model_name": model,
                "uncertainty_status": status,
                "uncertainty_method": "paired_circular_block_bootstrap",
                "paired_observations": n_observations,
                "bootstrap_samples": int(samples),
                "block_length": int(block_length),
                "confidence_level": float(confidence_level),
                "annual_return_diff_ci_lower": float(annual_low),
                "annual_return_diff_ci_upper": float(annual_high),
                "probability_annual_return_improvement": float(
                    (annual_return_diff > 0.0).mean()
                ),
                "sharpe_diff_ci_lower": float(sharpe_low),
                "sharpe_diff_ci_upper": float(sharpe_high),
                "probability_sharpe_improvement": sharpe_probability,
            }
        )
    return pd.DataFrame(rows).reindex(columns=columns)


def _bootstrap_sharpe(samples: np.ndarray, daily_hurdle: float) -> np.ndarray:
    annualized_excess = (samples - float(daily_hurdle)).mean(
        axis=1
    ) * TRADING_DAYS_PER_YEAR
    volatility = samples.std(axis=1, ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
    return np.divide(
        annualized_excess,
        volatility,
        out=np.full_like(annualized_excess, np.nan, dtype=float),
        where=volatility > 1e-15,
    )


def _comparison(
    validation: pd.DataFrame,
    returns_long: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if validation.empty:
        return pd.DataFrame()
    validation_for_summary = validation.copy()
    if "model_status" not in validation_for_summary:
        validation_for_summary["model_status"] = np.where(
            validation_for_summary["model_name"].astype(str).eq("Equal Weight"),
            "benchmark_only",
            "actually_run",
        )
    if "risk_free_rate_annual" not in validation_for_summary:
        validation_for_summary["risk_free_rate_annual"] = 0.0
    if "risk_free_policy" not in validation_for_summary:
        validation_for_summary["risk_free_policy"] = (
            "zero_rate_labeled_research_assumption"
        )
    fold_summary = validation_for_summary.groupby("model_name", as_index=False).agg(
        model_status=("model_status", "first"),
        risk_free_rate_annual=("risk_free_rate_annual", "first"),
        risk_free_policy=("risk_free_policy", "first"),
        folds=("fold", "nunique"),
        mean_fold_cagr=("cagr", "mean"),
        mean_fold_annualized_return=("annualized_return", "mean"),
        mean_fold_volatility=("annualized_volatility", "mean"),
        mean_fold_sharpe=("sharpe", "mean"),
        mean_fold_sortino=("sortino", "mean"),
        mean_fold_max_drawdown=("max_drawdown", "mean"),
        mean_fold_cvar_95=("cvar_95", "mean"),
        avg_turnover=("turnover", "mean"),
    )
    if returns_long is None or returns_long.empty:
        return pd.DataFrame()
    required = {"Date", "fold", "model_name", "return"}
    if not required.issubset(returns_long.columns):
        raise ValueError(
            "Walk-forward OOS returns require Date, fold, model_name and return."
        )
    clean_returns = returns_long.copy()
    clean_returns["Date"] = pd.to_datetime(clean_returns["Date"], errors="coerce")
    clean_returns["return"] = pd.to_numeric(clean_returns["return"], errors="coerce")
    clean_returns = clean_returns.dropna(subset=["Date", "model_name", "return"])
    duplicate_dates = clean_returns.duplicated(
        subset=["model_name", "Date"], keep=False
    )
    if duplicate_dates.any():
        duplicate_count = int(duplicate_dates.sum())
        raise ValueError(
            "Walk-forward test windows overlap; concatenated OOS metrics would "
            f"double-count {duplicate_count} model-date rows."
        )

    metric_rows = []
    for model, group in clean_returns.groupby("model_name", sort=False):
        series = (
            group.sort_values(["Date", "fold"])
            .set_index("Date")["return"]
            .astype(float)
        )
        model_fold_summary = fold_summary.loc[
            fold_summary["model_name"].astype(str).eq(str(model))
        ]
        risk_free_rate = (
            float(model_fold_summary["risk_free_rate_annual"].iloc[0])
            if not model_fold_summary.empty
            else 0.0
        )
        metrics = evaluate_return_series(
            series,
            risk_free_rate_annual=risk_free_rate,
        )
        metric_rows.append(
            {
                "model_name": str(model),
                "oos_observations": int(metrics["observations"]),
                "oos_cagr": float(metrics["cagr"]),
                "oos_annualized_return": float(metrics["annualized_return"]),
                "oos_volatility": float(metrics["annualized_volatility"]),
                "oos_sharpe": float(metrics["sharpe"]),
                "oos_sortino": float(metrics["sortino"]),
                "oos_max_drawdown": float(metrics["max_drawdown"]),
                "oos_cvar_95": float(metrics["cvar_95"]),
                "metric_aggregation": (
                    "concatenated_non_overlapping_net_oos_daily_returns"
                ),
            }
        )
    grouped = fold_summary.merge(pd.DataFrame(metric_rows), on="model_name")
    # Legacy avg_* columns remain as aliases for downstream compatibility. They
    # now carry mathematically valid aggregate OOS metrics, not means of ratios.
    grouped["avg_cagr"] = grouped["oos_cagr"]
    grouped["avg_annualized_return"] = grouped["oos_annualized_return"]
    grouped["avg_volatility"] = grouped["oos_volatility"]
    grouped["avg_sharpe"] = grouped["oos_sharpe"]
    grouped["avg_sortino"] = grouped["oos_sortino"]
    grouped["avg_max_drawdown"] = grouped["oos_max_drawdown"]
    grouped["avg_cvar_95"] = grouped["oos_cvar_95"]

    ew = grouped.loc[grouped["model_name"].eq("Equal Weight")]
    if ew.empty:
        grouped["beats_equal_weight_avg_sharpe"] = False
        grouped["beats_equal_weight_avg_cagr"] = False
    else:
        ew_row = ew.iloc[0]
        grouped["beats_equal_weight_avg_sharpe"] = (
            grouped["oos_sharpe"] > ew_row["oos_sharpe"]
        )
        grouped["beats_equal_weight_avg_cagr"] = (
            grouped["oos_cagr"] > ew_row["oos_cagr"]
        )
    return grouped.sort_values(["oos_sharpe", "oos_cagr"], ascending=False)


def _summary(
    comparison: pd.DataFrame,
    validation: pd.DataFrame,
    leakage_audit: pd.DataFrame,
) -> dict[str, object]:
    if comparison.empty:
        return {
            "walk_forward_status": "not_run",
            "reason": "No valid walk-forward folds.",
        }
    best_metric = comparison.iloc[0]
    eligible = comparison.loc[
        comparison.get("model_status", pd.Series("", index=comparison.index))
        .astype(str)
        .isin(["actually_run", "benchmark_only"])
    ]
    best = eligible.iloc[0] if not eligible.empty else best_metric
    sharpe_column = "oos_sharpe" if "oos_sharpe" in comparison else "avg_sharpe"
    return {
        "walk_forward_status": "completed_public_data_current_universe",
        "folds": int(validation["fold"].nunique()) if not validation.empty else 0,
        "best_model": str(best["model_name"]),
        "best_model_oos_sharpe": float(best[sharpe_column]),
        "best_model_avg_sharpe": float(best[sharpe_column]),
        "best_metric_model": str(best_metric["model_name"]),
        "best_metric_model_status": str(
            best_metric.get("model_status", "not_available")
        ),
        "best_metric_model_oos_sharpe": float(best_metric[sharpe_column]),
        "metric_aggregation": str(
            best.get(
                "metric_aggregation",
                "legacy_fold_metric_average_not_recommended",
            )
        ),
        "leakage_audit_passed": (
            bool(leakage_audit["passed"].all()) if not leakage_audit.empty else False
        ),
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


def _leakage_audit_rows(
    *,
    fold: int,
    train: pd.DataFrame,
    test: pd.DataFrame,
    scores: pd.DataFrame,
    selected_tickers: list[str],
) -> list[dict[str, object]]:
    train_end = train.index.max()
    test_start = test.index.min()
    scoring_dates = (
        pd.to_datetime(scores["scoring_as_of_date"], errors="coerce")
        if "scoring_as_of_date" in scores
        else pd.Series([train_end])
    )
    return [
        {
            "fold": fold,
            "check": "train_end_before_test_start",
            "passed": bool(train_end < test_start),
            "evidence": f"train_end={train_end}; test_start={test_start}",
        },
        {
            "fold": fold,
            "check": "scores_as_of_not_after_train_end",
            "passed": bool((scoring_dates.dropna() <= train_end).all()),
            "evidence": f"max_scoring_as_of={scoring_dates.max()}; train_end={train_end}",
        },
        {
            "fold": fold,
            "check": "selected_tickers_available_in_train",
            "passed": bool(set(selected_tickers).issubset(set(train.columns))),
            "evidence": f"selected_count={len(selected_tickers)}",
        },
        {
            "fold": fold,
            "check": "scores_recomputed_inside_fold",
            "passed": True,
            "evidence": "build_global_stock_scores called on train window inside fold",
        },
    ]


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


def _scope_tickers(
    universe: pd.DataFrame,
    *,
    default_scope: str,
    include_crypto: bool,
) -> list[str]:
    if universe.empty or "ticker" not in universe:
        return []
    frame = resolve_security_master_rows(universe)
    for column, default in [
        ("include", True),
        ("investable", True),
        ("signal_only", False),
    ]:
        if column not in frame:
            frame[column] = default
    frame = frame.loc[
        frame["include"].map(_truthy)
        & frame["investable"].map(_truthy)
        & ~frame["signal_only"].map(_truthy)
    ]
    sleeve = frame.get("sleeve", pd.Series("", index=frame.index)).astype(str)
    scope = str(default_scope or "equity_only").strip().lower()
    if scope == "equity_only":
        frame = frame.loc[sleeve.str.startswith("global_equity", na=False)]
    elif scope == "multi_asset_no_crypto" or not include_crypto:
        frame = frame.loc[~sleeve.str.contains("crypto", case=False, na=False)]
    return frame["ticker"].dropna().astype(str).drop_duplicates().tolist()


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
