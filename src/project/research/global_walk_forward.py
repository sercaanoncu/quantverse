"""Public-data current-universe walk-forward validation for QuantVerse v2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypedDict

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
from project.research.global_stock_scoring import build_global_stock_scores
from project.research.global_stock_selection import apply_max_weight_cap
from project.research.global_portfolio_core import (
    CanonicalPortfolioPolicy,
    sample_constraint_feasible_weights,
    select_canonical_securities,
)


class WalkForwardResult(TypedDict):
    """Typed walk-forward evidence package."""

    validation: pd.DataFrame
    returns: pd.DataFrame
    weights: pd.DataFrame
    turnover: pd.DataFrame
    leakage_audit: pd.DataFrame
    window_summary: pd.DataFrame
    fold_audit: pd.DataFrame
    model_comparison: pd.DataFrame
    random_distribution: pd.DataFrame
    random_returns: pd.DataFrame
    random_weights: pd.DataFrame
    random_benchmark_provenance: dict[str, object]
    uncertainty: pd.DataFrame
    summary: dict[str, object]


def run_public_data_walk_forward(
    returns: pd.DataFrame,
    universe: pd.DataFrame,
    *,
    train_window_days: int = 504,
    test_window_days: int = 21,
    step_days: int = 21,
    max_assets: int = 20,
    max_weight: float = 0.10,
    transaction_cost_bps: float = 10.0,
    random_state: int = 42,
    max_folds: int | None = None,
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
    security_metadata: pd.DataFrame | None = None,
    constraint_policy: CanonicalPortfolioPolicy | None = None,
    risk_free_daily: pd.Series | None = None,
) -> WalkForwardResult:
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
        summary: dict[str, object] = {
            "walk_forward_status": "insufficient_history",
            "reason": "Not enough observations for configured train/test windows.",
        }
        random_provenance: dict[str, object] = {
            "benchmark_scope": "not_available",
            "provenance_status": "insufficient_history",
        }
        empty = pd.DataFrame()
        return {
            "validation": empty,
            "returns": empty,
            "weights": empty,
            "turnover": empty,
            "leakage_audit": empty,
            "window_summary": empty,
            "fold_audit": empty,
            "model_comparison": empty,
            "random_distribution": empty,
            "random_returns": empty,
            "random_weights": empty,
            "random_benchmark_provenance": random_provenance,
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
    random_weight_rows: list[dict[str, object]] = []
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
        if security_metadata is not None and constraint_policy is not None:
            fold_selected, _ = select_canonical_securities(
                scores,
                security_metadata,
                constraint_policy,
            )
            selected_for_fold = fold_selected["ticker"].astype(str).tolist()
            scores["selection_flag"] = (
                scores["ticker"].astype(str).isin(selected_for_fold)
            )
        else:
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
        metadata_source = (
            security_metadata if security_metadata is not None else universe
        )
        universe_subset = metadata_source.loc[
            metadata_source["ticker"].astype(str).isin(selected_for_fold)
        ].copy()
        scores = scores.loc[scores["ticker"].astype(str).isin(selected_for_fold)].copy()
        league, weights, status = build_portfolio_league(
            train_subset,
            scores,
            None,
            universe_subset,
            max_assets=max_assets,
            max_weight=max_weight,
            random_state=random_state + fold,
            risk_free_rate_annual=risk_free_rate_annual,
            risk_free_policy=risk_free_policy,
            risk_free_daily=(
                risk_free_daily.reindex(train_subset.index)
                if risk_free_daily is not None
                else None
            ),
            constraint_policy=constraint_policy,
            primary_only=True,
        )
        _append_random_oos_fold(
            test,
            selected_for_fold,
            fold=fold,
            max_weight=max_weight,
            transaction_cost_bps=transaction_cost_bps,
            random_state=random_state,
            portfolio_count=random_benchmark_portfolios,
            rebalance_date=as_of_date,
            previous_weights=previous_random_weights,
            return_frames=random_return_frames,
            turnover_rows=random_turnover_rows,
            weight_rows=random_weight_rows,
            security_metadata=universe_subset,
            constraint_policy=constraint_policy,
        )
        run_models = status.loc[
            status["actual_status"].isin(["actually_run", "benchmark_only"]),
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
            previous_weights[model] = _drift_weights_through_returns(aligned, test)
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
                        risk_free_daily=(
                            risk_free_daily.reindex(net_returns.index)
                            if risk_free_daily is not None
                            else None
                        ),
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
    fold_audit = _build_fold_audit(
        window_summary,
        validation,
        weights_long,
        turnover,
        leakage_audit,
        security_metadata=security_metadata,
        risk_free_daily=risk_free_daily,
        transaction_cost_bps=transaction_cost_bps,
    )
    comparison = _comparison(
        validation,
        returns_long,
        expected_dates=clean.index,
        risk_free_daily=risk_free_daily,
    )
    uncertainty = _paired_block_bootstrap_uncertainty(
        returns_long,
        risk_free_rate_annual=risk_free_rate_annual,
        samples=uncertainty_bootstrap_samples,
        block_length=uncertainty_block_length,
        confidence_level=uncertainty_confidence_level,
        random_state=random_state,
        risk_free_daily=risk_free_daily,
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
    random_weights_long = pd.DataFrame(random_weight_rows)
    random_distribution = _random_oos_distribution(
        random_returns_long,
        pd.DataFrame(random_turnover_rows),
        risk_free_rate_annual=risk_free_rate_annual,
        risk_free_daily=risk_free_daily,
    )
    random_provenance = _build_random_benchmark_provenance(
        model_returns=returns_long,
        random_returns=random_returns_long,
        random_weights=random_weights_long,
        window_summary=window_summary,
        train_window_days=train_window_days,
        test_window_days=test_window_days,
        step_days=step_days,
        max_assets=max_assets,
        max_weight=max_weight,
        transaction_cost_bps=transaction_cost_bps,
        random_state=random_state,
        risk_free_rate_annual=risk_free_rate_annual,
        risk_free_policy=risk_free_policy,
    )
    random_distribution = _attach_random_benchmark_protocol(
        random_distribution,
        random_provenance,
    )
    random_returns_long = _attach_random_benchmark_protocol(
        random_returns_long,
        random_provenance,
    )
    random_weights_long = _attach_random_benchmark_protocol(
        random_weights_long,
        random_provenance,
    )
    summary = _summary(comparison, validation, leakage_audit)
    summary["random_benchmark_status"] = str(random_provenance["provenance_status"])
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
        "fold_audit": fold_audit,
        "model_comparison": comparison,
        "random_distribution": random_distribution,
        "random_returns": random_returns_long,
        "random_weights": random_weights_long,
        "random_benchmark_provenance": random_provenance,
        "uncertainty": uncertainty,
        "summary": summary,
    }


def write_walk_forward_outputs(
    result: WalkForwardResult,
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
    result["fold_audit"].to_csv(
        path / "global_walk_forward_fold_audit.csv", index=False
    )
    result["model_comparison"].to_csv(
        path / "global_walk_forward_model_comparison.csv", index=False
    )
    result["random_distribution"].to_csv(
        path / "global_walk_forward_random_distribution.csv", index=False
    )
    result["random_returns"].to_csv(
        path / "global_walk_forward_random_returns.csv", index=False
    )
    result["random_weights"].to_csv(
        path / "global_walk_forward_random_weights.csv", index=False
    )
    (path / "global_walk_forward_random_benchmark_provenance.json").write_text(
        json.dumps(result["random_benchmark_provenance"], indent=2, default=str),
        encoding="utf-8",
    )
    result["uncertainty"].to_csv(
        path / "global_walk_forward_uncertainty.csv", index=False
    )
    (path / "global_walk_forward_summary.json").write_text(
        json.dumps(result["summary"], indent=2, default=str),
        encoding="utf-8",
    )


def _build_fold_audit(
    window_summary: pd.DataFrame,
    validation: pd.DataFrame,
    weights: pd.DataFrame,
    turnover: pd.DataFrame,
    leakage_audit: pd.DataFrame,
    *,
    security_metadata: pd.DataFrame | None,
    risk_free_daily: pd.Series | None,
    transaction_cost_bps: float,
) -> pd.DataFrame:
    columns = [
        "fold_id",
        "train_start",
        "train_end",
        "decision_date",
        "test_start",
        "test_end",
        "test_observations",
        "selected_issuer_count",
        "duplicate_issuer_count",
        "model_count",
        "risk_free_coverage",
        "risk_free_coverage_ratio",
        "cost_applied",
        "transaction_cost_bps",
        "leakage_status",
    ]
    if window_summary.empty:
        return pd.DataFrame(columns=columns)
    issuer_by_ticker: dict[str, str] = {}
    if (
        security_metadata is not None
        and not security_metadata.empty
        and {"ticker", "issuer_key"}.issubset(security_metadata.columns)
    ):
        metadata = security_metadata.drop_duplicates("ticker").copy()
        metadata["ticker"] = metadata["ticker"].astype(str)
        issuer_by_ticker = {
            str(ticker): str(issuer)
            for ticker, issuer in metadata.set_index("ticker")["issuer_key"].items()
        }
    rows: list[dict[str, object]] = []
    for _, window in window_summary.sort_values("fold").iterrows():
        fold = _integer(window["fold"])
        test_observations = _integer(window["test_observations"])
        selected_tickers = [
            ticker
            for ticker in str(window["selected_tickers"]).split(";")
            if ticker.strip()
        ]
        issuer_keys = [
            issuer_by_ticker.get(ticker, f"ticker:{ticker}")
            for ticker in selected_tickers
        ]
        fold_validation = validation.loc[validation["fold"].eq(fold)]
        fold_turnover = turnover.loc[turnover["fold"].eq(fold)]
        fold_leakage = leakage_audit.loc[leakage_audit["fold"].eq(fold)]
        test_dates = pd.date_range(
            pd.Timestamp(str(window["test_start"])),
            pd.Timestamp(str(window["test_end"])),
            freq="B",
        )
        if risk_free_daily is None:
            rf_count = 0
            rf_ratio = 0.0
        else:
            expected_dates = risk_free_daily.index.intersection(test_dates)
            rf_values = pd.to_numeric(
                risk_free_daily.reindex(expected_dates), errors="coerce"
            )
            rf_count = int(rf_values.notna().sum())
            rf_ratio = (
                float(rf_count / test_observations) if test_observations > 0 else 0.0
            )
        costs_valid = bool(
            not fold_turnover.empty
            and pd.to_numeric(fold_turnover["transaction_cost_bps"], errors="coerce")
            .eq(float(transaction_cost_bps))
            .all()
            and pd.to_numeric(
                fold_turnover["transaction_cost_decimal"], errors="coerce"
            )
            .ge(0.0)
            .all()
        )
        leakage_pass = bool(
            not fold_leakage.empty and fold_leakage["passed"].map(_truthy).all()
        )
        rows.append(
            {
                "fold_id": fold,
                "train_start": window["train_start"],
                "train_end": window["train_end"],
                "decision_date": window["train_end"],
                "test_start": window["test_start"],
                "test_end": window["test_end"],
                "test_observations": test_observations,
                "selected_issuer_count": int(len(set(issuer_keys))),
                "duplicate_issuer_count": int(len(issuer_keys) - len(set(issuer_keys))),
                "model_count": int(fold_validation["model_name"].nunique()),
                "risk_free_coverage": f"{rf_count}/{test_observations}",
                "risk_free_coverage_ratio": rf_ratio,
                "cost_applied": costs_valid,
                "transaction_cost_bps": float(transaction_cost_bps),
                "leakage_status": "passed" if leakage_pass else "failed",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_transaction_cost_sensitivity(
    returns_long: pd.DataFrame,
    turnover: pd.DataFrame,
    *,
    primary_cost_bps: float,
    cost_scenarios_bps: list[float],
    risk_free_daily: pd.Series,
) -> pd.DataFrame:
    """Reprice the stitched OOS path under alternative rebalance costs."""
    if returns_long.empty or turnover.empty:
        return pd.DataFrame()
    frame = returns_long.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["return"] = pd.to_numeric(frame["return"], errors="coerce")
    costs = turnover[["fold", "model_name", "turnover"]].copy()
    costs["turnover"] = pd.to_numeric(costs["turnover"], errors="coerce")
    if frame[["Date", "return"]].isna().any().any() or costs["turnover"].isna().any():
        raise ValueError("Cost sensitivity requires complete OOS returns and turnover.")
    first_dates = (
        frame.groupby(["fold", "model_name"])["Date"]
        .min()
        .rename("first_test_date")
        .reset_index()
    )
    frame = frame.merge(first_dates, on=["fold", "model_name"], validate="many_to_one")
    frame = frame.merge(costs, on=["fold", "model_name"], validate="many_to_one")
    first = frame["Date"].eq(frame["first_test_date"]).astype(float)
    gross = (
        frame["return"] + first * frame["turnover"] * float(primary_cost_bps) / 10000.0
    )
    rows: list[dict[str, object]] = []
    for cost_bps in cost_scenarios_bps:
        scenario = frame.copy()
        scenario["scenario_return"] = (
            gross - first * frame["turnover"] * float(cost_bps) / 10000.0
        )
        for model, group in scenario.groupby("model_name", sort=True):
            series = group.sort_values("Date").set_index("Date")["scenario_return"]
            metrics = evaluate_return_series(
                series,
                risk_free_daily=risk_free_daily.reindex(series.index),
            )
            rows.append(
                {
                    "model_name": str(model),
                    "transaction_cost_bps": float(cost_bps),
                    "oos_observations": _integer(metrics["observations"]),
                    "cagr": _number(metrics["cagr"]),
                    "annualized_return": _number(metrics["annualized_return"]),
                    "volatility": _number(metrics["annualized_volatility"]),
                    "sharpe": _number(metrics["sharpe"]),
                    "sortino": _number(metrics["sortino"]),
                    "max_drawdown": _number(metrics["max_drawdown"]),
                    "var_95": _number(metrics["var_95"]),
                    "cvar_95": _number(metrics["cvar_95"]),
                    "average_turnover": float(
                        costs.loc[
                            costs["model_name"].astype(str).eq(str(model)), "turnover"
                        ].mean()
                    ),
                    "metric_method": "stitched_non_overlapping_net_oos_daily_returns",
                }
            )
    return pd.DataFrame(rows)


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


def _drift_weights_through_returns(
    weights: pd.Series,
    asset_returns: pd.DataFrame,
) -> pd.Series:
    """Return end-of-window weights after buy-and-hold asset return drift.

    The resulting weights are the economically relevant pre-trade weights for
    the next rebalance. Missing selected returns fail closed; they are never
    interpreted as zero returns or implicit cash.
    """
    current = pd.Series(weights, dtype=float)
    current = current.loc[current.abs() > 1e-12]
    if current.empty:
        raise ValueError("Cannot drift an empty portfolio.")
    missing_tickers = [
        str(ticker) for ticker in current.index if ticker not in asset_returns.columns
    ]
    if missing_tickers:
        raise ValueError(
            "Selected portfolio weights are missing from the drift return matrix: "
            + ", ".join(missing_tickers)
        )
    selected = asset_returns.reindex(columns=current.index).apply(
        pd.to_numeric,
        errors="coerce",
    )
    values = selected.to_numpy(dtype=float)
    if selected.empty or not np.isfinite(values).all():
        raise ValueError(
            "Selected asset returns must be complete and finite before weight drift."
        )
    if bool((values < -1.0 - 1e-12).any()):
        raise ValueError("A simple asset return below -100% is invalid.")
    growth = (1.0 + selected).prod(axis=0)
    terminal_values = current * growth
    total = float(terminal_values.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("Portfolio terminal value must remain positive and finite.")
    drifted = terminal_values / total
    if not np.isfinite(drifted.to_numpy(dtype=float)).all():
        raise ValueError("Drifted portfolio weights must be finite.")
    return drifted.astype(float)


def _append_random_oos_fold(
    test: pd.DataFrame,
    selected_tickers: list[str],
    *,
    fold: int,
    max_weight: float,
    transaction_cost_bps: float,
    random_state: int,
    portfolio_count: int,
    rebalance_date: pd.Timestamp,
    previous_weights: dict[int, pd.Series],
    return_frames: list[pd.DataFrame],
    turnover_rows: list[dict[str, object]],
    weight_rows: list[dict[str, object]],
    security_metadata: pd.DataFrame | None = None,
    constraint_policy: CanonicalPortfolioPolicy | None = None,
) -> None:
    if portfolio_count <= 0 or not selected_tickers:
        return
    if float(max_weight) * len(selected_tickers) < 1.0 - 1e-12:
        return
    rng = np.random.default_rng(int(random_state) + 100_000 + int(fold))
    metadata_for_sampling = (
        security_metadata.loc[
            security_metadata["ticker"].astype(str).isin(selected_tickers)
        ].copy()
        if security_metadata is not None
        else pd.DataFrame()
    )
    for portfolio_id in range(int(portfolio_count)):
        if constraint_policy is not None and security_metadata is not None:
            target = sample_constraint_feasible_weights(
                metadata_for_sampling,
                constraint_policy,
                rng,
            )
        else:
            raw = pd.Series(
                rng.random(len(selected_tickers)),
                index=selected_tickers,
                dtype=float,
            )
            target = apply_max_weight_cap(raw, max_weight)
        aligned = target.astype(float)
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
        post_test = _drift_weights_through_returns(aligned, test)
        previous_weights[portfolio_id] = post_test
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
                "transaction_cost_decimal": turnover
                * float(transaction_cost_bps)
                / 10000.0,
            }
        )
        prior = pd.Series(dtype=float) if previous is None else previous.astype(float)
        union = aligned.index.union(prior.index).union(post_test.index)
        weight_rows.extend(
            {
                "fold": fold,
                "rebalance_date": rebalance_date,
                "portfolio_id": portfolio_id,
                "ticker": str(ticker),
                "target_weight": float(aligned.get(ticker, 0.0)),
                "pre_trade_weight": float(prior.get(ticker, 0.0)),
                "post_test_weight": float(post_test.get(ticker, 0.0)),
            }
            for ticker in union
        )


def _random_oos_distribution(
    returns_long: pd.DataFrame,
    turnover: pd.DataFrame,
    *,
    risk_free_rate_annual: float,
    risk_free_daily: pd.Series | None = None,
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
            risk_free_daily=(
                risk_free_daily.reindex(series.index)
                if risk_free_daily is not None
                else None
            ),
        )
        rows.append(
            {
                "portfolio_id": _integer(portfolio_id),
                "folds": _integer(group["fold"].nunique()),
                "avg_turnover": _number(turnover_map.get(portfolio_id, np.nan)),
                "benchmark_scope": "walk_forward_oos_net",
                "sampling_method": (
                    "iid_uniform_raw_scores_projected_to_capped_simplex"
                ),
                "cagr": _number(metrics["cagr"]),
                "annualized_return": _number(metrics["annualized_return"]),
                "volatility": _number(metrics["annualized_volatility"]),
                "sharpe": _number(metrics["sharpe"]),
                "sortino": _number(metrics["sortino"]),
                "max_drawdown": _number(metrics["max_drawdown"]),
                "var_95": _number(metrics["var_95"]),
                "cvar_95": _number(metrics["cvar_95"]),
                "calmar": _number(metrics["calmar"]),
                "total_return": _number(metrics["total_return"]),
            }
        )
    return pd.DataFrame(rows)


def _build_random_benchmark_provenance(
    *,
    model_returns: pd.DataFrame,
    random_returns: pd.DataFrame,
    random_weights: pd.DataFrame,
    window_summary: pd.DataFrame,
    train_window_days: int,
    test_window_days: int,
    step_days: int,
    max_assets: int,
    max_weight: float,
    transaction_cost_bps: float,
    random_state: int,
    risk_free_rate_annual: float,
    risk_free_policy: str,
) -> dict[str, object]:
    """Build auditable same-protocol evidence from actual OOS return rows."""
    model_hashes = _date_hashes_by_group(model_returns, "model_name")
    random_hashes = _date_hashes_by_group(random_returns, "portfolio_id")
    equal_weight_hash = model_hashes.get("Equal Weight", "missing")
    model_dates_match = bool(
        equal_weight_hash != "missing"
        and model_hashes
        and all(value == equal_weight_hash for value in model_hashes.values())
    )
    random_dates_match = bool(
        equal_weight_hash != "missing"
        and random_hashes
        and all(value == equal_weight_hash for value in random_hashes.values())
    )
    oos_dates_match = bool(model_dates_match and random_dates_match)
    fold_schedule_hash = _stable_frame_hash(
        window_summary,
        [
            "fold",
            "train_start",
            "train_end",
            "test_start",
            "test_end",
        ],
    )
    selected_universe_hash = _stable_frame_hash(
        window_summary,
        ["fold", "selected_count", "selected_tickers"],
    )
    random_weights_hash = _stable_frame_hash(
        random_weights,
        [
            "fold",
            "portfolio_id",
            "ticker",
            "target_weight",
            "pre_trade_weight",
            "post_test_weight",
        ],
    )
    protocol = {
        "benchmark_scope": "walk_forward_oos_net",
        "selection_protocol": "training_window_only_per_fold",
        "constraint_policy": "long_only_capped_simplex",
        "rebalance_schedule": "fixed_step_chronological_walk_forward",
        "transaction_cost_convention": (
            "gross_traded_notional_l1_applied_to_first_oos_day"
        ),
        "train_window_days": int(train_window_days),
        "test_window_days": int(test_window_days),
        "step_days": int(step_days),
        "max_assets": int(max_assets),
        "max_weight": float(max_weight),
        "transaction_cost_bps": float(transaction_cost_bps),
        "random_state": int(random_state),
        "risk_free_rate_annual": float(risk_free_rate_annual),
        "risk_free_policy": str(risk_free_policy),
        "fold_count": (
            int(window_summary["fold"].nunique())
            if not window_summary.empty and "fold" in window_summary
            else 0
        ),
        "random_portfolio_count": int(len(random_hashes)),
        "fold_schedule_hash": fold_schedule_hash,
        "selected_universe_by_fold_hash": selected_universe_hash,
        "model_oos_dates_hash": equal_weight_hash,
        "random_oos_dates_hash": (
            next(iter(random_hashes.values()))
            if random_hashes and random_dates_match
            else "inconsistent_or_missing"
        ),
        "random_weights_hash": random_weights_hash,
        "oos_dates_match": oos_dates_match,
        "model_date_sets_match": model_dates_match,
        "random_date_sets_match": random_dates_match,
    }
    protocol_payload = json.dumps(
        protocol,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    protocol_hash = f"wf-random-{hashlib.sha256(protocol_payload).hexdigest()[:24]}"
    return {
        **protocol,
        "protocol_hash": protocol_hash,
        "provenance_status": (
            "verified_same_protocol"
            if oos_dates_match
            and protocol["fold_count"] > 0
            and protocol["random_portfolio_count"] > 0
            and random_weights_hash != "missing"
            else "failed_protocol_reconciliation"
        ),
        "limitation": (
            "Current-universe public-data walk-forward benchmark; the protocol "
            "match does not create institutional point-in-time evidence."
        ),
    }


def _attach_random_benchmark_protocol(
    frame: pd.DataFrame,
    provenance: dict[str, object],
) -> pd.DataFrame:
    output = frame.copy()
    if output.empty:
        return output
    output["benchmark_scope"] = str(provenance["benchmark_scope"])
    output["benchmark_provenance_status"] = str(provenance["provenance_status"])
    output["protocol_hash"] = str(provenance["protocol_hash"])
    output["fold_schedule_hash"] = str(provenance["fold_schedule_hash"])
    output["selected_universe_by_fold_hash"] = str(
        provenance["selected_universe_by_fold_hash"]
    )
    output["model_oos_dates_hash"] = str(provenance["model_oos_dates_hash"])
    output["random_oos_dates_hash"] = str(provenance["random_oos_dates_hash"])
    output["random_weights_hash"] = str(provenance["random_weights_hash"])
    output["transaction_cost_bps"] = _number(provenance["transaction_cost_bps"])
    output["max_weight"] = _number(provenance["max_weight"])
    return output


def _date_hashes_by_group(
    frame: pd.DataFrame,
    group_column: str,
) -> dict[object, str]:
    if frame.empty or not {group_column, "Date"}.issubset(frame.columns):
        return {}
    hashes: dict[object, str] = {}
    for key, group in frame.groupby(group_column, sort=True):
        dates = (
            pd.to_datetime(group["Date"], errors="coerce")
            .dropna()
            .drop_duplicates()
            .sort_values()
        )
        payload = "\n".join(dates.dt.strftime("%Y-%m-%d")).encode("utf-8")
        hashes[key] = f"dates-{hashlib.sha256(payload).hexdigest()[:24]}"
    return hashes


def _stable_frame_hash(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty or not set(columns).issubset(frame.columns):
        return "missing"
    normalized = frame[columns].copy()
    for column in columns:
        if "date" in column or column.endswith("_start") or column.endswith("_end"):
            normalized[column] = pd.to_datetime(
                normalized[column], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_numeric_dtype(normalized[column]):
            numeric = pd.to_numeric(normalized[column], errors="coerce")
            normalized[column] = numeric.map(
                lambda value: (
                    f"{float(value):.12g}" if np.isfinite(value) else "missing"
                )
            )
        else:
            normalized[column] = normalized[column].fillna("").astype(str)
    normalized = normalized.sort_values(columns, kind="stable")
    payload = normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return f"frame-{hashlib.sha256(payload).hexdigest()[:24]}"


def _paired_block_bootstrap_uncertainty(
    returns_long: pd.DataFrame,
    *,
    risk_free_rate_annual: float,
    samples: int,
    block_length: int,
    confidence_level: float,
    random_state: int,
    risk_free_daily: pd.Series | None = None,
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
        "random_state",
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
    if risk_free_daily is None:
        hurdle_series = pd.Series(
            (1.0 + float(risk_free_rate_annual)) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0,
            index=pivot.index,
        )
    else:
        hurdle_series = pd.Series(risk_free_daily, dtype=float).reindex(pivot.index)
        if hurdle_series.isna().any():
            raise ValueError("Risk-free hurdle is incomplete for OOS bootstrap dates.")
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
                    "random_state": int(random_state),
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
                    "random_state": int(random_state) + 200_000 + model_number * 1009,
                }
            )
            continue
        model_returns = paired[model].to_numpy(dtype=float)
        benchmark_returns = paired["Equal Weight"].to_numpy(dtype=float)
        paired_hurdle = hurdle_series.reindex(paired.index).to_numpy(dtype=float)
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
        hurdle_samples = paired_hurdle[indices]
        annual_return_diff = (
            model_samples.mean(axis=1) - benchmark_samples.mean(axis=1)
        ) * TRADING_DAYS_PER_YEAR
        model_sharpe = _bootstrap_sharpe(model_samples, hurdle_samples)
        benchmark_sharpe = _bootstrap_sharpe(benchmark_samples, hurdle_samples)
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
                "random_state": int(random_state) + 200_000 + model_number * 1009,
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


def _bootstrap_sharpe(samples: np.ndarray, daily_hurdle: np.ndarray) -> np.ndarray:
    annualized_excess = (samples - daily_hurdle).mean(axis=1) * TRADING_DAYS_PER_YEAR
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
    *,
    expected_dates: pd.Index | None = None,
    risk_free_daily: pd.Series | None = None,
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
    clean_returns["fold"] = pd.to_numeric(clean_returns["fold"], errors="coerce")
    clean_returns["model_name"] = clean_returns["model_name"].astype(str).str.strip()
    return_values = clean_returns["return"].to_numpy(dtype=float)
    fold_values = clean_returns["fold"].to_numpy(dtype=float)
    finite_folds = np.isfinite(fold_values)
    invalid_rows = (
        clean_returns["Date"].isna()
        | clean_returns["model_name"].eq("")
        | ~np.isfinite(return_values)
        | ~finite_folds
        | ~(finite_folds & np.isclose(fold_values, np.round(fold_values)))
    )
    if invalid_rows.any():
        raise ValueError(
            "Walk-forward OOS returns contain invalid dates, folds, model names "
            "or non-finite returns; rows must never be silently removed."
        )
    clean_returns["fold"] = clean_returns["fold"].astype(int)
    _validate_oos_path_completeness(
        validation_for_summary,
        clean_returns,
        expected_dates=expected_dates,
    )
    duplicate_dates = clean_returns.duplicated(
        subset=["model_name", "Date"], keep=False
    )
    if duplicate_dates.any():
        duplicate_count = int(duplicate_dates.sum())
        raise ValueError(
            "Walk-forward test windows overlap; concatenated OOS metrics would "
            f"double-count {duplicate_count} model-date rows."
        )
    _validate_common_model_oos_dates(validation_for_summary, clean_returns)

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
            _number(model_fold_summary["risk_free_rate_annual"].iloc[0])
            if not model_fold_summary.empty
            else 0.0
        )
        metrics = evaluate_return_series(
            series,
            risk_free_rate_annual=risk_free_rate,
            risk_free_daily=(
                risk_free_daily.reindex(series.index)
                if risk_free_daily is not None
                else None
            ),
        )
        metric_rows.append(
            {
                "model_name": str(model),
                "oos_observations": _integer(metrics["observations"]),
                "oos_cagr": _number(metrics["cagr"]),
                "oos_annualized_return": _number(metrics["annualized_return"]),
                "oos_volatility": _number(metrics["annualized_volatility"]),
                "oos_sharpe": _number(metrics["sharpe"]),
                "oos_sortino": _number(metrics["sortino"]),
                "oos_max_drawdown": _number(metrics["max_drawdown"]),
                "oos_cvar_95": _number(metrics["cvar_95"]),
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


def _validate_oos_path_completeness(
    validation: pd.DataFrame,
    returns_long: pd.DataFrame,
    *,
    expected_dates: pd.Index | None,
) -> None:
    required = {
        "fold",
        "model_name",
        "test_start",
        "test_end",
        "test_observations",
    }
    if not required.issubset(validation.columns):
        raise ValueError(
            "Walk-forward validation requires fold, model_name, test_start, "
            "test_end and test_observations to prove OOS path completeness."
        )
    schedule = validation[
        ["fold", "model_name", "test_start", "test_end", "test_observations"]
    ].copy()
    schedule["fold"] = pd.to_numeric(schedule["fold"], errors="coerce")
    schedule["test_observations"] = pd.to_numeric(
        schedule["test_observations"],
        errors="coerce",
    )
    schedule["test_start"] = pd.to_datetime(schedule["test_start"], errors="coerce")
    schedule["test_end"] = pd.to_datetime(schedule["test_end"], errors="coerce")
    schedule["model_name"] = schedule["model_name"].astype(str).str.strip()
    fold_values = schedule["fold"].to_numpy(dtype=float)
    observation_values = schedule["test_observations"].to_numpy(dtype=float)
    invalid_schedule = (
        schedule["test_start"].isna()
        | schedule["test_end"].isna()
        | schedule["model_name"].eq("")
        | ~np.isfinite(fold_values)
        | ~np.isclose(fold_values, np.round(fold_values))
        | ~np.isfinite(observation_values)
        | ~np.isclose(observation_values, np.round(observation_values))
        | schedule["test_observations"].le(0)
    )
    if invalid_schedule.any() or schedule.duplicated(["fold", "model_name"]).any():
        raise ValueError("Walk-forward fold/model schedule is invalid or duplicated.")
    schedule["fold"] = schedule["fold"].astype(int)
    schedule["test_observations"] = schedule["test_observations"].astype(int)

    expected_index: pd.DatetimeIndex | None = None
    if expected_dates is not None:
        expected_index = pd.DatetimeIndex(
            pd.to_datetime(expected_dates, errors="coerce")
        )
        expected_index = expected_index[expected_index.notna()].unique().sort_values()

    expected_groups = set(
        schedule[["fold", "model_name"]].itertuples(index=False, name=None)
    )
    observed_groups = set(
        returns_long[["fold", "model_name"]].itertuples(index=False, name=None)
    )
    if expected_groups != observed_groups:
        raise ValueError(
            "Walk-forward OOS return groups do not exactly match the validation "
            "fold/model schedule."
        )

    for row in schedule.itertuples(index=False):
        test_start = pd.Timestamp(str(row.test_start))
        test_end = pd.Timestamp(str(row.test_end))
        actual = returns_long.loc[
            returns_long["fold"].eq(row.fold)
            & returns_long["model_name"].eq(row.model_name),
            "Date",
        ]
        actual_dates = pd.DatetimeIndex(actual).unique().sort_values()
        if expected_index is None:
            dates_complete = bool(
                len(actual_dates) == row.test_observations
                and len(actual_dates) > 0
                and actual_dates.min() == test_start
                and actual_dates.max() == test_end
            )
        else:
            scheduled_dates = expected_index[
                (expected_index >= test_start) & (expected_index <= test_end)
            ]
            dates_complete = bool(
                len(scheduled_dates) == row.test_observations
                and actual_dates.equals(scheduled_dates)
            )
        if not dates_complete:
            raise ValueError(
                "Walk-forward OOS dates are incomplete or inconsistent for "
                f"fold={row.fold}, model={row.model_name}."
            )


def _validate_common_model_oos_dates(
    validation: pd.DataFrame,
    returns_long: pd.DataFrame,
) -> None:
    """Fail comparison unless every executable model has one common OOS path."""
    date_paths: dict[str, tuple[tuple[int, str], ...]] = {}
    for model, group in returns_long.groupby("model_name", sort=True):
        ordered = group.sort_values(["Date", "fold"])
        date_paths[str(model)] = tuple(
            (int(fold), pd.Timestamp(date).isoformat())
            for fold, date in ordered[["fold", "Date"]].itertuples(
                index=False, name=None
            )
        )
    if len(set(date_paths.values())) > 1:
        raise ValueError(
            "All comparable models must use identical OOS dates and fold IDs."
        )

    schedule_paths: dict[str, tuple[tuple[int, str, str, int], ...]] = {}
    for model, group in validation.groupby("model_name", sort=True):
        schedule = group.sort_values("fold")
        schedule_paths[str(model)] = tuple(
            (
                int(fold),
                pd.Timestamp(test_start).isoformat(),
                pd.Timestamp(test_end).isoformat(),
                int(observations),
            )
            for fold, test_start, test_end, observations in schedule[
                ["fold", "test_start", "test_end", "test_observations"]
            ].itertuples(index=False, name=None)
        )
    if len(set(schedule_paths.values())) > 1:
        raise ValueError(
            "All comparable models must use an identical OOS fold schedule."
        )


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
        "leakage_audit_status": (
            "passed_with_current_universe_survivorship_limitation"
            if not leakage_audit.empty and bool(leakage_audit["passed"].all())
            else "failed_or_missing"
        ),
        "institutional_point_in_time_supported": False,
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
    rows = [
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
    for row in rows:
        row.update(
            {
                "audit_status": (
                    "passed_with_current_universe_survivorship_limitation"
                    if bool(row["passed"])
                    else "failed"
                ),
                "evidence_scope": "current_universe_not_point_in_time",
                "institutional_point_in_time_supported": False,
                "survivorship_bias_limitation": (
                    "Current constituents are not historical point-in-time membership."
                ),
            }
        )
    return rows


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


def _number(value: object, *, default: float = np.nan) -> float:
    """Convert scalar evidence to float while rejecting array-like values."""
    try:
        if value is None or value is pd.NA or value is pd.NaT:
            return float(default)
        if isinstance(value, (int, float, np.integer, np.floating)):
            return float(value)
        return float(str(value))
    except (TypeError, ValueError):
        return float(default)


def _integer(value: object, *, default: int = 0) -> int:
    """Convert scalar evidence to integer through the reviewed numeric contract."""
    number = _number(value, default=float(default))
    return int(number) if np.isfinite(number) else int(default)
