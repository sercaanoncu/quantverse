"""Sensitivity and robustness analysis for the QuantVerse v2 model league."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
    build_random_percentile_report,
    simulate_constrained_random_distribution,
)
from project.research.global_portfolio_league import build_portfolio_league

SENSITIVITY_COLUMNS = [
    "scenario_id",
    "max_assets",
    "max_weight",
    "train_window_days",
    "test_window_days",
    "transaction_cost_bps",
    "random_seed",
    "final_model",
    "final_model_selection_score",
    "gross_annualized_return",
    "transaction_cost_drag",
    "net_annualized_return",
    "sharpe",
    "max_drawdown",
    "cvar_95",
    "selected_holdings_count",
    "selected_holdings_overlap_with_base",
    "top10_overlap_with_base",
    "weight_turnover_vs_base",
    "random_sharpe_percentile",
    "equal_weight_return_gate",
    "equal_weight_sharpe_gate",
    "stability_interpretation",
]

MODEL_STABILITY_COLUMNS = [
    "final_model",
    "scenario_count",
    "scenario_share",
    "mean_selection_score",
    "mean_net_annualized_return",
    "mean_sharpe",
    "mean_max_drawdown",
    "mean_cvar_95",
]

WEIGHT_STABILITY_COLUMNS = [
    "ticker",
    "appearances",
    "appearance_share",
    "mean_weight",
    "weight_std",
    "min_weight",
    "max_weight",
]


def run_robustness_sensitivity(
    returns: pd.DataFrame,
    scores: pd.DataFrame,
    forecasts: pd.DataFrame | None = None,
    metadata: pd.DataFrame | None = None,
    *,
    max_assets_values: list[int] | None = None,
    max_weight_values: list[float] | None = None,
    train_window_days_values: list[int] | None = None,
    test_window_days_values: list[int] | None = None,
    transaction_cost_bps_values: list[float] | None = None,
    random_seeds: list[int] | None = None,
    random_portfolios: int = 150,
    max_scenarios: int = 48,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run a practical bounded sensitivity grid over existing v2 models."""
    clean = _clean_returns(returns)
    if clean.empty:
        empty = pd.DataFrame(columns=SENSITIVITY_COLUMNS)
        return {
            "sensitivity": empty,
            "model_stability": pd.DataFrame(columns=MODEL_STABILITY_COLUMNS),
            "weight_stability": pd.DataFrame(columns=WEIGHT_STABILITY_COLUMNS),
            "summary": {"robustness_status": "not_run", "reason": "Missing returns."},
        }

    max_assets_grid = max_assets_values or [20, 30, 40]
    max_weight_grid = max_weight_values or [0.05, 0.10, 0.15]
    train_grid = train_window_days_values or [126, 252]
    test_grid = test_window_days_values or [21, 63]
    cost_grid = transaction_cost_bps_values or [0.0, 10.0, 25.0, 50.0]
    seed_grid = random_seeds or [42, 43, 44]

    scenario_rows: list[dict[str, object]] = []
    weight_rows: list[pd.DataFrame] = []
    base_tickers: set[str] | None = None
    base_top10: set[str] | None = None
    base_weights: pd.Series | None = None
    scenario_id = 0
    for max_assets in max_assets_grid:
        for max_weight in max_weight_grid:
            if float(max_weight) * int(max_assets) < 1.0 - 1e-12:
                continue
            for train_window_days in train_grid:
                if clean.shape[0] < int(train_window_days):
                    continue
                for test_window_days in test_grid:
                    for cost_bps in cost_grid:
                        for seed in seed_grid:
                            if scenario_id >= max_scenarios:
                                break
                            result = _one_scenario(
                                clean,
                                scores,
                                forecasts,
                                metadata,
                                scenario_id=scenario_id,
                                max_assets=int(max_assets),
                                max_weight=float(max_weight),
                                train_window_days=int(train_window_days),
                                test_window_days=int(test_window_days),
                                transaction_cost_bps=float(cost_bps),
                                random_seed=int(seed),
                                random_portfolios=int(random_portfolios),
                            )
                            tickers = set(result["weights"].index)
                            top10 = set(
                                result["weights"]
                                .sort_values(ascending=False)
                                .head(10)
                                .index
                            )
                            if base_tickers is None:
                                base_tickers = tickers
                                base_top10 = top10
                                base_weights = result["weights"]
                            overlap = _jaccard(tickers, base_tickers or set())
                            top_overlap = _jaccard(top10, base_top10 or set())
                            turnover = _weight_turnover(
                                result["weights"],
                                (
                                    base_weights
                                    if base_weights is not None
                                    else result["weights"]
                                ),
                            )
                            row = result["row"]
                            row["selected_holdings_overlap_with_base"] = overlap
                            row["top10_overlap_with_base"] = top_overlap
                            row["weight_turnover_vs_base"] = turnover
                            scenario_rows.append(row)
                            scenario_weights = (
                                result["weights"].rename("weight").reset_index()
                            )
                            scenario_weights.columns = ["ticker", "weight"]
                            scenario_weights["scenario_id"] = scenario_id
                            weight_rows.append(scenario_weights)
                            scenario_id += 1
                        if scenario_id >= max_scenarios:
                            break
                    if scenario_id >= max_scenarios:
                        break
                if scenario_id >= max_scenarios:
                    break
            if scenario_id >= max_scenarios:
                break
        if scenario_id >= max_scenarios:
            break

    sensitivity = pd.DataFrame(scenario_rows, columns=SENSITIVITY_COLUMNS)
    all_weights = (
        pd.concat(weight_rows, ignore_index=True) if weight_rows else pd.DataFrame()
    )
    model_stability = _model_stability(sensitivity)
    weight_stability = _weight_stability(all_weights, max(int(scenario_id), 1))
    summary = _summary(sensitivity, model_stability, weight_stability)
    return {
        "sensitivity": sensitivity,
        "model_stability": model_stability,
        "weight_stability": weight_stability,
        "summary": summary,
    }


def write_robustness_outputs(
    result: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: str | Path,
) -> None:
    """Write robustness sensitivity outputs."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    result["sensitivity"].to_csv(
        path / "global_robustness_sensitivity.csv", index=False
    )
    result["model_stability"].to_csv(
        path / "global_model_stability_report.csv", index=False
    )
    result["weight_stability"].to_csv(
        path / "global_weight_stability_report.csv", index=False
    )
    (path / "global_parameter_sensitivity_summary.json").write_text(
        json.dumps(result["summary"], indent=2, default=str), encoding="utf-8"
    )


def _one_scenario(
    returns: pd.DataFrame,
    scores: pd.DataFrame,
    forecasts: pd.DataFrame | None,
    metadata: pd.DataFrame | None,
    *,
    scenario_id: int,
    max_assets: int,
    max_weight: float,
    train_window_days: int,
    test_window_days: int,
    transaction_cost_bps: float,
    random_seed: int,
    random_portfolios: int,
) -> dict[str, object]:
    league, weights, _status = build_portfolio_league(
        returns.tail(train_window_days),
        scores,
        forecasts=forecasts,
        metadata=metadata,
        max_assets=max_assets,
        max_weight=max_weight,
        random_state=random_seed,
    )
    selected_tickers = _selected_tickers(weights, returns)
    random_distribution = simulate_constrained_random_distribution(
        returns[selected_tickers].tail(train_window_days),
        n_portfolios=random_portfolios,
        max_weight=max_weight,
        random_state=random_seed,
    )
    percentiles = build_random_percentile_report(league, random_distribution)
    selection = build_model_selection_report(
        league,
        walk_forward=None,
        risk_report=None,
        turnover=None,
        random_percentiles=percentiles,
    )
    decision = build_final_model_decision(selection)
    final_model = str(decision["final_selected_model"])
    final_row = selection.loc[selection["model_name"].astype(str).eq(final_model)]
    final_row = final_row.iloc[0] if not final_row.empty else selection.iloc[0]
    final_weights = _weights_for_model(weights, final_model, returns[selected_tickers])
    turnover_proxy = _weight_turnover(
        final_weights,
        pd.Series(1.0 / len(final_weights), index=final_weights.index),
    )
    transaction_cost_drag = turnover_proxy * transaction_cost_bps / 10000.0
    gross_return = float(final_row["walk_forward_annualized_return"])
    net_return = gross_return - transaction_cost_drag
    return {
        "row": {
            "scenario_id": scenario_id,
            "max_assets": max_assets,
            "max_weight": max_weight,
            "train_window_days": train_window_days,
            "test_window_days": test_window_days,
            "transaction_cost_bps": transaction_cost_bps,
            "random_seed": random_seed,
            "final_model": final_model,
            "final_model_selection_score": float(
                decision["final_model_selection_score"]
            ),
            "gross_annualized_return": gross_return,
            "transaction_cost_drag": transaction_cost_drag,
            "net_annualized_return": net_return,
            "sharpe": float(final_row["walk_forward_sharpe"]),
            "max_drawdown": float(final_row["walk_forward_max_drawdown"]),
            "cvar_95": float(final_row["walk_forward_cvar_95"]),
            "selected_holdings_count": int((final_weights.abs() > 1e-10).sum()),
            "selected_holdings_overlap_with_base": np.nan,
            "top10_overlap_with_base": np.nan,
            "weight_turnover_vs_base": np.nan,
            "random_sharpe_percentile": float(final_row["random_sharpe_percentile"]),
            "equal_weight_return_gate": bool(
                final_row["beats_equal_weight_return_after_costs"]
            ),
            "equal_weight_sharpe_gate": bool(final_row["beats_equal_weight_sharpe"]),
            "stability_interpretation": (
                "Scenario evidence; not a guarantee of future stability."
            ),
        },
        "weights": final_weights,
    }


def _selected_tickers(weights: pd.DataFrame, returns: pd.DataFrame) -> list[str]:
    if weights.empty or "ticker" not in weights:
        return list(returns.columns)
    selected = weights["ticker"].drop_duplicates().astype(str).tolist()
    selected = [ticker for ticker in selected if ticker in returns.columns]
    return selected or list(returns.columns)


def _weights_for_model(
    weights: pd.DataFrame,
    model: str,
    returns: pd.DataFrame,
) -> pd.Series:
    if not weights.empty and {"model_name", "ticker", "weight"}.issubset(weights):
        frame = weights.loc[weights["model_name"].astype(str).eq(model)]
        if not frame.empty:
            series = frame.set_index("ticker")["weight"].astype(float)
            return series.reindex(returns.columns).fillna(0.0)
    return pd.Series(1.0 / returns.shape[1], index=returns.columns)


def _model_stability(sensitivity: pd.DataFrame) -> pd.DataFrame:
    if sensitivity.empty:
        return pd.DataFrame(columns=MODEL_STABILITY_COLUMNS)
    grouped = sensitivity.groupby("final_model", as_index=False).agg(
        scenario_count=("scenario_id", "count"),
        mean_selection_score=("final_model_selection_score", "mean"),
        mean_net_annualized_return=("net_annualized_return", "mean"),
        mean_sharpe=("sharpe", "mean"),
        mean_max_drawdown=("max_drawdown", "mean"),
        mean_cvar_95=("cvar_95", "mean"),
    )
    total = max(float(len(sensitivity)), 1.0)
    grouped["scenario_share"] = grouped["scenario_count"] / total
    return grouped[MODEL_STABILITY_COLUMNS].sort_values(
        ["scenario_share", "mean_selection_score"], ascending=False
    )


def _weight_stability(weights: pd.DataFrame, scenario_count: int) -> pd.DataFrame:
    if weights.empty:
        return pd.DataFrame(columns=WEIGHT_STABILITY_COLUMNS)
    grouped = weights.groupby("ticker", as_index=False).agg(
        appearances=("scenario_id", "nunique"),
        mean_weight=("weight", "mean"),
        weight_std=("weight", "std"),
        min_weight=("weight", "min"),
        max_weight=("weight", "max"),
    )
    grouped["weight_std"] = grouped["weight_std"].fillna(0.0)
    grouped["appearance_share"] = grouped["appearances"] / max(
        float(scenario_count), 1.0
    )
    return grouped[WEIGHT_STABILITY_COLUMNS].sort_values(
        ["mean_weight", "appearance_share"], ascending=False
    )


def _summary(
    sensitivity: pd.DataFrame,
    model_stability: pd.DataFrame,
    weight_stability: pd.DataFrame,
) -> dict[str, object]:
    if sensitivity.empty:
        return {"robustness_status": "not_run", "reason": "No scenarios generated."}
    top_share = (
        float(model_stability["scenario_share"].iloc[0])
        if not model_stability.empty
        else 0.0
    )
    max_weight_std = (
        float(weight_stability["weight_std"].max())
        if not weight_stability.empty
        else 0.0
    )
    status = "stable" if top_share >= 0.67 and max_weight_std <= 0.05 else "fragile"
    return {
        "robustness_status": status,
        "scenario_count": int(len(sensitivity)),
        "dominant_final_model": (
            str(model_stability["final_model"].iloc[0])
            if not model_stability.empty
            else "missing"
        ),
        "dominant_model_scenario_share": top_share,
        "max_weight_standard_deviation": max_weight_std,
        "sensitivity_status": (
            "Model choice is relatively stable across bounded sensitivity scenarios."
            if status == "stable"
            else "Model choice or weights are fragile across bounded sensitivity scenarios."
        ),
    }


def _clean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    clean = returns.copy()
    if not isinstance(clean.index, pd.DatetimeIndex):
        first = str(clean.columns[0]).lower() if len(clean.columns) else ""
        if first in {"date", "datetime", "timestamp"}:
            clean = clean.set_index(first)
        clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[clean.index.notna()]
    clean = clean.apply(pd.to_numeric, errors="coerce")
    return clean.dropna(axis=1, how="all").dropna(how="all")


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return float(len(left & right) / len(union)) if union else 0.0


def _weight_turnover(current: pd.Series, base: pd.Series) -> float:
    idx = current.index.union(base.index)
    return float(
        (current.reindex(idx).fillna(0.0) - base.reindex(idx).fillna(0.0)).abs().sum()
    )
