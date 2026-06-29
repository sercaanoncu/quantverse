"""Global master portfolio research allocator."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from project.optimization.black_litterman import black_litterman_weights
from project.projection.portfolio_projection import (
    correlation_diagnostics,
    estimator_comparison,
    monte_carlo_projection,
    stress_test_portfolio,
)
from project.research.global_stock_selection import (
    build_equal_weight_portfolio,
    build_inverse_volatility_portfolio,
    build_min_cvar_portfolio,
    build_shrinkage_max_sharpe_portfolio,
    build_stock_selection_promotion_gate,
    cluster_assets_by_correlation,
    compare_candidate_to_equal_weight_and_random,
    evaluate_portfolio_return_series,
    score_assets_for_selection,
    select_assets_by_cluster,
    simulate_random_portfolios,
)


def run_master_portfolio_research(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    min_holdings: int = 10,
    max_holdings: int = 40,
    max_weight: float = 0.10,
    n_random_portfolios: int = 10000,
    random_state: int = 42,
) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Run the first-pass global master portfolio research layer."""
    clean = returns.apply(pd.to_numeric, errors="coerce").dropna(how="all").fillna(0.0)
    available = [ticker for ticker in metadata["ticker"].astype(str) if ticker in clean]
    if not available:
        raise ValueError("No metadata tickers overlap the returns matrix.")
    clean = clean[available]
    selected = select_assets_by_cluster(
        clean,
        min_holdings=min_holdings,
        max_holdings=max_holdings,
        random_state=random_state,
    )
    selected_returns = clean[selected]
    selected_metadata = metadata.loc[
        metadata["ticker"].astype(str).isin(selected)
    ].copy()
    candidates = _candidate_weights(selected_returns, selected_metadata, max_weight)
    model_comparison = _compare_models(selected_returns, candidates)
    equal_weight_metrics = model_comparison.loc[
        model_comparison["Model"].eq("Equal Weight")
    ].iloc[0]
    best_row = _best_promotable_candidate(model_comparison)
    final_weights = candidates.get(
        str(best_row["Model"]),
        candidates["Equal Weight"],
    )
    randoms = simulate_random_portfolios(
        selected_returns,
        n_portfolios=n_random_portfolios,
        max_weight=max_weight,
        random_state=random_state,
    )
    candidate_returns = selected_returns @ final_weights
    ew_returns = selected_returns @ candidates["Equal Weight"]
    comparison = compare_candidate_to_equal_weight_and_random(
        evaluate_portfolio_return_series(candidate_returns),
        evaluate_portfolio_return_series(ew_returns),
        randoms,
    )
    comparison.update(
        {
            "Turnover": 1.0,
            "Transaction_Cost_Bps": 10.0,
            "Transaction_Cost_Drag": 0.001,
        }
    )
    gate = build_stock_selection_promotion_gate(comparison)
    if not gate["Promoted"]:
        final_model = "Equal Weight"
        final_weights = candidates["Equal Weight"]
    else:
        final_model = str(best_row["Model"])
    weights_long = _weights_long(candidates)
    risk_report = _risk_report(selected_returns, candidates)
    projection = monte_carlo_projection(
        selected_returns,
        final_weights,
        n_simulations=min(1000, max(100, n_random_portfolios)),
        random_state=random_state,
    )
    stress = stress_test_portfolio(final_weights, selected_metadata)
    diagnostics = correlation_diagnostics(selected_returns)
    decision = {
        "selected_holdings": int(len(selected)),
        "final_model": final_model,
        "promotion_decision": gate["Promotion_Decision"],
        "reason": gate["Reason"],
        "selected_assets": selected,
    }
    return {
        "selected_assets": selected_metadata,
        "candidate_weights": weights_long,
        "model_comparison": model_comparison,
        "random_portfolio_benchmark": randoms,
        "promotion_gate": pd.DataFrame([{**comparison, **gate}]),
        "risk_report": risk_report,
        "projection_summary": projection,
        "stress_tests": stress,
        "correlation_matrix": diagnostics["correlation_matrix"],
        "high_correlation_pairs": diagnostics["high_correlation_pairs"],
        "cluster_diagnostics": diagnostics["cluster_diagnostics"],
        "estimator_comparison": estimator_comparison(selected_returns),
        "decision_summary": decision,
    }


def write_master_portfolio_outputs(
    result: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: str | Path,
) -> None:
    """Write master portfolio outputs to CSV/JSON."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    file_map = {
        "selected_assets": "global_master_selected_assets.csv",
        "candidate_weights": "global_master_candidate_weights.csv",
        "model_comparison": "global_master_model_comparison.csv",
        "random_portfolio_benchmark": "global_master_random_portfolio_benchmark.csv",
        "promotion_gate": "global_master_promotion_gate.csv",
        "risk_report": "global_master_risk_report.csv",
        "projection_summary": "global_master_projection_summary.csv",
        "stress_tests": "global_stress_test_results.csv",
        "correlation_matrix": "global_correlation_matrix.csv",
        "high_correlation_pairs": "global_high_correlation_pairs.csv",
        "cluster_diagnostics": "global_cluster_diagnostics.csv",
        "estimator_comparison": "global_estimator_comparison.csv",
    }
    for key, filename in file_map.items():
        value = result[key]
        if isinstance(value, pd.DataFrame):
            value.to_csv(path / filename, index=key != "correlation_matrix")
    (path / "global_monte_carlo_projection.csv").write_text(
        result["projection_summary"].to_csv(index=False),
        encoding="utf-8",
    )
    (path / "global_master_decision_summary.json").write_text(
        json.dumps(result["decision_summary"], indent=2),
        encoding="utf-8",
    )


def _candidate_weights(
    returns: pd.DataFrame,
    metadata: pd.DataFrame,
    max_weight: float,
) -> dict[str, pd.Series]:
    candidates = {
        "Equal Weight": build_equal_weight_portfolio(returns, returns.columns),
        "Inverse Volatility": build_inverse_volatility_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "Min Variance": _min_variance_weights(returns, max_weight=max_weight),
        "Max Sharpe": build_shrinkage_max_sharpe_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "Min CVaR": build_min_cvar_portfolio(
            returns,
            returns.columns,
            max_weight=max_weight,
        ),
        "Cluster Balanced": _cluster_balanced_weights(returns, max_weight=max_weight),
    }
    caps = (
        pd.to_numeric(metadata.set_index("ticker")["market_cap_usd"], errors="coerce")
        if "market_cap_usd" in metadata
        else pd.Series(dtype=float)
    )
    caps = caps.reindex(returns.columns)
    if caps.notna().all() and (caps > 0).all():
        candidates["Black-Litterman"] = black_litterman_weights(
            returns.cov() * 252,
            caps,
            max_weight=max_weight,
        )
    return candidates


def _compare_models(
    returns: pd.DataFrame,
    candidates: dict[str, pd.Series],
) -> pd.DataFrame:
    rows = []
    for name, weights in candidates.items():
        metrics = evaluate_portfolio_return_series(returns @ weights)
        rows.append({"Model": name, "Status": "computed", **metrics})
    if "Black-Litterman" not in candidates:
        rows.append(
            {
                "Model": "Black-Litterman",
                "Status": "missing_market_caps",
                "CAGR": np.nan,
                "Annual_Return": np.nan,
                "Volatility": np.nan,
                "Sharpe": np.nan,
                "Sortino": np.nan,
                "Max_Drawdown": np.nan,
                "CVaR_95": np.nan,
                "Total_Return": np.nan,
            }
        )
    for name in [
        "HRP",
        "Risk Parity",
        "Forecast-enhanced Max Sharpe",
        "Forecast-enhanced Min CVaR",
    ]:
        rows.append({"Model": name, "Status": "not_available_in_this_run"})
    return pd.DataFrame(rows)


def _best_promotable_candidate(model_comparison: pd.DataFrame) -> pd.Series:
    computed = model_comparison.loc[model_comparison["Status"].eq("computed")].copy()
    computed = computed.sort_values(["Sharpe", "CAGR"], ascending=False)
    return computed.iloc[0]


def _weights_long(candidates: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for model, weights in candidates.items():
        rows.extend(
            {"Model": model, "Ticker": ticker, "Weight": float(weight)}
            for ticker, weight in weights.items()
        )
    return pd.DataFrame(rows)


def _risk_report(
    returns: pd.DataFrame,
    candidates: dict[str, pd.Series],
) -> pd.DataFrame:
    rows = []
    for model, weights in candidates.items():
        portfolio_returns = returns @ weights
        metrics = evaluate_portfolio_return_series(portfolio_returns)
        rows.append(
            {
                "Model": model,
                "Volatility": metrics["Volatility"],
                "Max_Drawdown": metrics["Max_Drawdown"],
                "CVaR_95": metrics["CVaR_95"],
                "Weight_Concentration_HHI": float((weights**2).sum()),
            }
        )
    return pd.DataFrame(rows)


def _min_variance_weights(returns: pd.DataFrame, max_weight: float) -> pd.Series:
    assets = list(returns.columns)
    cov = returns.cov().to_numpy(dtype=float)
    x0 = np.repeat(1.0 / len(assets), len(assets))

    def objective(weights: np.ndarray) -> float:
        return float(weights @ cov @ weights)

    result = minimize(
        objective,
        x0=x0,
        bounds=[(0.0, float(max_weight)) for _ in assets],
        constraints={"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
        method="SLSQP",
    )
    if not result.success:
        return build_inverse_volatility_portfolio(returns, assets, max_weight)
    weights = pd.Series(result.x, index=assets, name="Weight")
    return weights / weights.sum()


def _cluster_balanced_weights(returns: pd.DataFrame, max_weight: float) -> pd.Series:
    clusters = cluster_assets_by_correlation(returns)
    weights = pd.Series(0.0, index=returns.columns, dtype=float)
    for _, tickers in clusters.groupby(clusters).groups.items():
        cluster_weight = 1.0 / clusters.nunique()
        per_asset = cluster_weight / len(tickers)
        weights.loc[list(tickers)] = min(per_asset, max_weight)
    weights = weights / weights.sum()
    weights.name = "Weight"
    return weights
