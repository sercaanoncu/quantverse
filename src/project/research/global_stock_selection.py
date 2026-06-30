"""Deterministic research utilities for global stock-selection candidates.

This module works from an already-prepared returns matrix. It does not download
data, infer current market-cap rankings, or make buy/sell recommendations.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform
from sklearn.covariance import LedoitWolf

from project.constants import TRADING_DAYS_PER_YEAR


def compute_asset_statistics(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute per-asset return and risk statistics."""
    clean = _clean_returns(returns)
    rows = []
    for ticker, series in clean.items():
        asset_returns = series.dropna()
        volatility = asset_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        annual_return = asset_returns.mean() * TRADING_DAYS_PER_YEAR
        sharpe = annual_return / volatility if volatility > 0 else 0.0
        rows.append(
            {
                "Ticker": ticker,
                "Observations": int(asset_returns.shape[0]),
                "Annual_Return": float(annual_return),
                "Volatility": float(volatility),
                "Sharpe": float(sharpe),
                "Max_Drawdown": float(_max_drawdown(asset_returns)),
                "CVaR_95": float(_cvar_95(asset_returns)),
            }
        )
    return pd.DataFrame(rows)


def cluster_assets_by_correlation(
    returns: pd.DataFrame,
    max_clusters: int | None = None,
    random_state: int = 42,
) -> pd.Series:
    """Cluster assets by correlation distance.

    `random_state` is accepted for API stability; hierarchical clustering here
    is deterministic for a fixed returns matrix.
    """
    del random_state
    clean = _clean_returns(returns)
    tickers = list(clean.columns)
    n_assets = len(tickers)
    if n_assets == 0:
        return pd.Series(dtype=int)
    if n_assets == 1:
        return pd.Series([1], index=tickers, name="Cluster")

    if max_clusters is None:
        max_clusters = max(2, min(n_assets, int(np.sqrt(n_assets)) + 1))
    max_clusters = max(1, min(int(max_clusters), n_assets))

    corr = clean.corr().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    corr_array = corr.to_numpy(dtype=float, copy=True)
    np.fill_diagonal(corr_array, 1.0)
    distance_array = np.clip(1.0 - corr_array, 0.0, 2.0)
    condensed = squareform(distance_array, checks=False)
    labels = fcluster(linkage(condensed, method="average"), max_clusters, "maxclust")
    return pd.Series(labels.astype(int), index=tickers, name="Cluster")


def score_assets_for_selection(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.0,
) -> pd.DataFrame:
    """Score assets using return, risk and drawdown-aware diagnostics."""
    stats = compute_asset_statistics(returns)
    excess_return = stats["Annual_Return"] - float(risk_free_rate)
    volatility = stats["Volatility"].replace(0.0, np.nan)
    stats["Excess_Return"] = excess_return
    stats["Selection_Score"] = (
        excess_return / volatility
        + stats["CVaR_95"].clip(upper=0.0)
        + 0.25 * stats["Max_Drawdown"].clip(upper=0.0)
    ).fillna(-np.inf)
    return stats.sort_values("Selection_Score", ascending=False).reset_index(drop=True)


def select_assets_by_cluster(
    returns: pd.DataFrame,
    min_holdings: int = 10,
    max_holdings: int = 40,
    random_state: int = 42,
) -> list[str]:
    """Select scored assets while spreading choices across correlation clusters."""
    del random_state
    clean = _clean_returns(returns)
    if clean.empty:
        return []
    max_holdings = max(1, min(int(max_holdings), clean.shape[1]))
    min_holdings = max(1, min(int(min_holdings), max_holdings))

    scores = score_assets_for_selection(clean).set_index("Ticker")
    clusters = cluster_assets_by_correlation(clean)
    ranked = scores.join(clusters)
    selected: list[str] = []

    grouped = {
        cluster: frame.sort_values("Selection_Score", ascending=False).index.tolist()
        for cluster, frame in ranked.groupby("Cluster", sort=True)
    }
    while len(selected) < max_holdings:
        added = False
        for cluster in sorted(grouped):
            candidates = grouped[cluster]
            if candidates:
                selected.append(candidates.pop(0))
                added = True
                if len(selected) >= max_holdings:
                    break
        if not added or (
            len(selected) >= min_holdings and len(selected) == clean.shape[1]
        ):
            break
        if len(selected) >= min_holdings and not any(grouped.values()):
            break
    return selected[:max_holdings]


def build_equal_weight_portfolio(
    returns: pd.DataFrame,
    tickers: Iterable[str],
) -> pd.Series:
    """Build a long-only equal-weight portfolio."""
    selected = _validate_tickers(returns, tickers)
    return pd.Series(1.0 / len(selected), index=selected, name="Weight")


def build_inverse_volatility_portfolio(
    returns: pd.DataFrame,
    tickers: Iterable[str],
    max_weight: float = 0.10,
) -> pd.Series:
    """Build a capped inverse-volatility portfolio."""
    selected = _validate_tickers(returns, tickers)
    vol = returns[selected].std(ddof=1).replace(0.0, np.nan)
    raw = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if raw.sum() <= 0:
        raw = pd.Series(1.0, index=selected)
    weights = _apply_max_weight_cap(raw, max_weight)
    weights.name = "Weight"
    return weights


def build_shrinkage_max_sharpe_portfolio(
    returns: pd.DataFrame,
    tickers: Iterable[str],
    max_weight: float = 0.10,
) -> pd.Series:
    """Build a capped long-only Max Sharpe candidate using shrinkage covariance."""
    selected = _validate_tickers(returns, tickers)
    matrix = _clean_returns(returns[selected])
    _check_cap_feasible(len(selected), max_weight)
    mu = matrix.mean().values * TRADING_DAYS_PER_YEAR
    cov = LedoitWolf().fit(matrix.values).covariance_ * TRADING_DAYS_PER_YEAR
    x0 = build_inverse_volatility_portfolio(matrix, selected, max_weight).values

    def objective(weights: np.ndarray) -> float:
        port_return = float(weights @ mu)
        port_vol = float(np.sqrt(weights @ cov @ weights))
        if port_vol <= 0:
            return 1e6
        return -port_return / port_vol

    result = minimize(
        objective,
        x0=x0,
        bounds=[(0.0, float(max_weight)) for _ in selected],
        constraints={"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
        method="SLSQP",
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        return build_inverse_volatility_portfolio(matrix, selected, max_weight)
    weights = pd.Series(result.x, index=selected)
    return _apply_max_weight_cap(weights, max_weight)


def build_min_cvar_portfolio(
    returns: pd.DataFrame,
    tickers: Iterable[str],
    max_weight: float = 0.10,
) -> pd.Series:
    """Build a capped long-only minimum empirical CVaR candidate."""
    selected = _validate_tickers(returns, tickers)
    matrix = _clean_returns(returns[selected])
    _check_cap_feasible(len(selected), max_weight)
    x0 = build_inverse_volatility_portfolio(matrix, selected, max_weight).values

    def objective(weights: np.ndarray) -> float:
        portfolio_returns = matrix.values @ weights
        return -_cvar_95(pd.Series(portfolio_returns))

    result = minimize(
        objective,
        x0=x0,
        bounds=[(0.0, float(max_weight)) for _ in selected],
        constraints={"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
        method="SLSQP",
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        return build_inverse_volatility_portfolio(matrix, selected, max_weight)
    weights = pd.Series(result.x, index=selected)
    return _apply_max_weight_cap(weights, max_weight)


def simulate_random_portfolios(
    returns: pd.DataFrame,
    n_portfolios: int = 10000,
    max_weight: float = 0.10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Simulate reproducible capped random long-only portfolios."""
    clean = _clean_returns(returns)
    tickers = list(clean.columns)
    _check_cap_feasible(len(tickers), max_weight)
    rng = np.random.default_rng(random_state)
    rows = []
    for portfolio_id in range(int(n_portfolios)):
        raw = pd.Series(rng.random(len(tickers)), index=tickers)
        weights = _apply_max_weight_cap(raw, max_weight)
        metrics = evaluate_portfolio_return_series(clean @ weights)
        row = {"portfolio_id": portfolio_id}
        row.update({f"weight_{ticker}": float(weights[ticker]) for ticker in tickers})
        row.update(metrics)
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_portfolio_return_series(portfolio_returns: pd.Series) -> dict[str, float]:
    """Evaluate a portfolio return series with return and downside metrics."""
    series = pd.Series(portfolio_returns).dropna().astype(float)
    if series.empty:
        return {
            "CAGR": 0.0,
            "Annual_Return": 0.0,
            "Volatility": 0.0,
            "Sharpe": 0.0,
            "Sortino": 0.0,
            "Max_Drawdown": 0.0,
            "CVaR_95": 0.0,
            "Total_Return": 0.0,
        }
    total_return = float((1.0 + series).prod() - 1.0)
    years = len(series) / TRADING_DAYS_PER_YEAR
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else total_return
    annual_return = float(series.mean() * TRADING_DAYS_PER_YEAR)
    volatility = float(series.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    downside = series[series < 0].std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = annual_return / volatility if volatility > 0 else 0.0
    sortino = annual_return / downside if downside and downside > 0 else 0.0
    return {
        "CAGR": float(cagr),
        "Annual_Return": annual_return,
        "Volatility": volatility,
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "Max_Drawdown": float(_max_drawdown(series)),
        "CVaR_95": float(_cvar_95(series)),
        "Total_Return": total_return,
    }


def compare_candidate_to_equal_weight_and_random(
    candidate: pd.Series | dict[str, float],
    equal_weight: pd.Series | dict[str, float],
    random_portfolios: pd.DataFrame,
) -> dict[str, float | bool]:
    """Compare a candidate with Equal Weight and simulated random portfolios."""
    candidate_metrics = _as_metrics(candidate)
    equal_weight_metrics = _as_metrics(equal_weight)
    random_sharpe = random_portfolios["Sharpe"].astype(float)
    percentile = float((random_sharpe <= candidate_metrics["Sharpe"]).mean())
    return {
        **{f"Candidate_{key}": value for key, value in candidate_metrics.items()},
        **{f"Equal_Weight_{key}": value for key, value in equal_weight_metrics.items()},
        "CAGR_Diff_vs_Equal_Weight": candidate_metrics["CAGR"]
        - equal_weight_metrics["CAGR"],
        "Sharpe_Diff_vs_Equal_Weight": candidate_metrics["Sharpe"]
        - equal_weight_metrics["Sharpe"],
        "Volatility_Ratio_vs_Equal_Weight": _safe_ratio(
            candidate_metrics["Volatility"], equal_weight_metrics["Volatility"]
        ),
        "Max_Drawdown_Diff_vs_Equal_Weight": candidate_metrics["Max_Drawdown"]
        - equal_weight_metrics["Max_Drawdown"],
        "CVaR_Diff_vs_Equal_Weight": candidate_metrics["CVaR_95"]
        - equal_weight_metrics["CVaR_95"],
        "Random_Sharpe_Percentile": percentile,
        "Random_Sharpe_90th": float(random_sharpe.quantile(0.90)),
        "Random_Sharpe_95th": float(random_sharpe.quantile(0.95)),
        "Beats_Equal_Weight_CAGR": bool(
            candidate_metrics["CAGR"] > equal_weight_metrics["CAGR"]
        ),
        "Beats_Equal_Weight_Sharpe": bool(
            candidate_metrics["Sharpe"] > equal_weight_metrics["Sharpe"]
        ),
        "Beats_Random_90th_Sharpe": bool(
            candidate_metrics["Sharpe"] >= random_sharpe.quantile(0.90)
        ),
        "Beats_Random_95th_Sharpe": bool(
            candidate_metrics["Sharpe"] >= random_sharpe.quantile(0.95)
        ),
    }


def build_stock_selection_promotion_gate(
    metrics: dict[str, float | bool],
    *,
    random_percentile_threshold: float = 0.90,
    volatility_relative_limit: float = 1.25,
    max_drawdown_penalty: float = 0.05,
    cvar_penalty: float = 0.05,
    max_turnover: float = 1.00,
    max_transaction_cost_drag: float = 0.0025,
) -> dict[str, object]:
    """Apply a transparent evidence gate to a stock-selection candidate."""
    cagr_ok = bool(metrics.get("Beats_Equal_Weight_CAGR", False))
    sharpe_ok = bool(metrics.get("Beats_Equal_Weight_Sharpe", False))
    vol_ratio = float(metrics.get("Volatility_Ratio_vs_Equal_Weight", np.inf))
    drawdown_diff = float(metrics.get("Max_Drawdown_Diff_vs_Equal_Weight", -np.inf))
    cvar_diff = float(metrics.get("CVaR_Diff_vs_Equal_Weight", -np.inf))
    random_percentile = float(metrics.get("Random_Sharpe_Percentile", 0.0))
    turnover = float(metrics.get("Turnover", np.inf))
    transaction_cost_drag = float(metrics.get("Transaction_Cost_Drag", np.inf))
    volatility_ok = vol_ratio <= volatility_relative_limit or (
        float(metrics.get("CAGR_Diff_vs_Equal_Weight", 0.0)) > 0.10
    )
    drawdown_ok = drawdown_diff >= -max_drawdown_penalty
    cvar_ok = cvar_diff >= -cvar_penalty
    random_ok = random_percentile >= random_percentile_threshold
    turnover_ok = turnover <= max_turnover
    transaction_cost_ok = transaction_cost_drag <= max_transaction_cost_drag
    passed = all(
        [
            cagr_ok,
            sharpe_ok,
            volatility_ok,
            drawdown_ok,
            cvar_ok,
            random_ok,
            turnover_ok,
            transaction_cost_ok,
        ]
    )
    failed = [
        name
        for name, ok in [
            ("net CAGR is not greater than Equal Weight", cagr_ok),
            ("Sharpe is not greater than Equal Weight", sharpe_ok),
            ("volatility gate", volatility_ok),
            ("max drawdown gate", drawdown_ok),
            ("CVaR gate", cvar_ok),
            ("random portfolio percentile gate", random_ok),
            ("turnover gate", turnover_ok),
            ("transaction-cost gate", transaction_cost_ok),
        ]
        if not ok
    ]
    return {
        "Promotion_Decision": "promoted" if passed else "not promoted",
        "Promoted": bool(passed),
        "Random_Sharpe_Percentile": random_percentile,
        "Random_Percentile_Threshold": random_percentile_threshold,
        "Turnover": turnover,
        "Max_Turnover_Allowed": max_turnover,
        "Transaction_Cost_Drag": transaction_cost_drag,
        "Max_Transaction_Cost_Drag_Allowed": max_transaction_cost_drag,
        "Failed_Gates": "; ".join(failed) if failed else "None",
        "Reason": (
            "Candidate passed the configured return, risk and robustness gate."
            if passed
            else "Candidate is not promoted because: " + "; ".join(failed)
        ),
    }


def _clean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    clean = returns.copy()
    clean = clean.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    clean = clean.dropna(axis=1, how="all").fillna(0.0)
    return clean


def _validate_tickers(returns: pd.DataFrame, tickers: Iterable[str]) -> list[str]:
    selected = [str(ticker) for ticker in tickers]
    if not selected:
        raise ValueError("At least one ticker is required.")
    missing = [ticker for ticker in selected if ticker not in returns.columns]
    if missing:
        raise ValueError("Returns matrix is missing tickers: " + ", ".join(missing))
    return selected


def _apply_max_weight_cap(weights: pd.Series, max_weight: float) -> pd.Series:
    raw = pd.Series(weights, dtype=float).clip(lower=0.0)
    _check_cap_feasible(len(raw), max_weight)
    if raw.sum() <= 0:
        raw = pd.Series(1.0, index=raw.index)
    remaining = list(raw.index)
    capped = pd.Series(0.0, index=raw.index)
    remaining_total = 1.0
    while remaining:
        base = raw.loc[remaining]
        if base.sum() <= 0:
            provisional = pd.Series(remaining_total / len(remaining), index=remaining)
        else:
            provisional = base / base.sum() * remaining_total
        over = provisional[provisional > max_weight + 1e-12]
        if over.empty:
            capped.loc[remaining] = provisional
            break
        capped.loc[over.index] = max_weight
        remaining_total -= max_weight * len(over)
        remaining = [ticker for ticker in remaining if ticker not in set(over.index)]
    capped = capped / capped.sum()
    capped.name = "Weight"
    return capped


def _check_cap_feasible(n_assets: int, max_weight: float) -> None:
    if n_assets <= 0:
        raise ValueError("At least one asset is required.")
    if max_weight <= 0:
        raise ValueError("max_weight must be positive.")
    if max_weight * n_assets < 1.0 - 1e-12:
        raise ValueError("max_weight is infeasible for the number of assets.")


def _max_drawdown(series: pd.Series) -> float:
    wealth = (1.0 + series.fillna(0.0)).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(drawdown.min())


def _cvar_95(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.empty:
        return 0.0
    threshold = clean.quantile(0.05)
    tail = clean[clean <= threshold]
    return float(tail.mean()) if not tail.empty else float(threshold)


def _as_metrics(value: pd.Series | dict[str, float]) -> dict[str, float]:
    if isinstance(value, pd.Series):
        return evaluate_portfolio_return_series(value)
    return {key: float(metric) for key, metric in value.items()}


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("inf")
