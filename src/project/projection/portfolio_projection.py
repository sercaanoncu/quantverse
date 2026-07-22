"""Portfolio projection and quantitative diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf
from sklearn.metrics import silhouette_score

from project.constants import TRADING_DAYS_PER_YEAR
from project.research.global_stock_selection import cluster_assets_by_correlation

HORIZON_TO_DAYS = {1: 21, 3: 63, 6: 126, 12: 252}


def monte_carlo_projection(
    returns: pd.DataFrame,
    weights: pd.Series,
    horizons_months: list[int] | None = None,
    n_simulations: int = 1000,
    random_state: int = 42,
) -> pd.DataFrame:
    """Simulate portfolio return distributions for configured horizons."""
    clean, aligned_weights = _align_returns_weights(returns, weights)
    rng = np.random.default_rng(random_state)
    if (clean <= -1.0).any().any():
        raise ValueError(
            "Monte Carlo input contains simple returns at or below -100%, "
            "which cannot be transformed into finite log returns."
        )
    log_returns = np.log1p(clean)
    mu = log_returns.mean().to_numpy(dtype=float)
    cov = LedoitWolf().fit(log_returns.to_numpy(dtype=float)).covariance_
    horizons = horizons_months or [1, 3, 6, 12]
    rows = []
    for horizon in horizons:
        days = HORIZON_TO_DAYS[int(horizon)]
        simulated_log_returns = rng.multivariate_normal(
            mu, cov, size=(n_simulations, days)
        )
        simulated_simple_returns = np.expm1(simulated_log_returns)
        portfolio_daily_returns = simulated_simple_returns @ aligned_weights.to_numpy()
        path_returns = (1.0 + portfolio_daily_returns).prod(axis=1) - 1.0
        var_5 = float(np.quantile(path_returns, 0.05))
        cvar_5 = float(path_returns[path_returns <= var_5].mean())
        rows.append(
            {
                "Horizon_Months": int(horizon),
                "Mean_Return": float(path_returns.mean()),
                "Median_Return": float(np.median(path_returns)),
                "P05_Return": var_5,
                "P95_Return": float(np.quantile(path_returns, 0.95)),
                "VaR_95": var_5,
                "CVaR_95": cvar_5,
                "Probability_Of_Loss": float((path_returns < 0).mean()),
                "N_Simulations": int(n_simulations),
                "Covariance_Estimator": "Ledoit-Wolf shrinkage",
                "Simulation_Assumption": (
                    "parametric multivariate-normal daily log-return diagnostic "
                    "transformed to simple returns with daily fixed-weight rebalancing"
                ),
            }
        )
    return pd.DataFrame(rows)


def correlation_diagnostics(returns: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Produce correlation matrix, high-correlation pairs and cluster diagnostics."""
    clean = _complete_case_returns(returns)
    if clean.empty:
        return {
            "correlation_matrix": pd.DataFrame(),
            "high_correlation_pairs": pd.DataFrame(
                columns=["asset_1", "asset_2", "correlation"]
            ),
            "cluster_diagnostics": pd.DataFrame(
                columns=["k", "within_cluster_distance", "silhouette_score", "selected"]
            ),
        }
    corr = clean.corr()
    finite_columns = corr.columns[corr.notna().all(axis=0)]
    clean = clean.loc[:, finite_columns]
    corr = clean.corr()
    if clean.shape[1] < 2:
        return {
            "correlation_matrix": corr,
            "high_correlation_pairs": pd.DataFrame(
                columns=["asset_1", "asset_2", "correlation"]
            ),
            "cluster_diagnostics": pd.DataFrame(
                columns=["k", "within_cluster_distance", "silhouette_score", "selected"]
            ),
        }
    pairs = []
    for idx, left in enumerate(corr.columns):
        for right in corr.columns[idx + 1 :]:
            value = float(corr.loc[left, right])
            if abs(value) >= 0.80:
                pairs.append({"asset_1": left, "asset_2": right, "correlation": value})
    diagnostics = []
    max_k = min(8, clean.shape[1])
    corr_array = corr.to_numpy(dtype=float, copy=True)
    distance = np.sqrt(0.5 * np.clip(1.0 - corr_array, 0.0, 2.0))
    for k in range(2, max_k + 1):
        labels = cluster_assets_by_correlation(clean, max_clusters=k)
        within = _within_cluster_distance(distance, labels.to_numpy())
        silhouette = np.nan
        if labels.nunique() > 1 and labels.nunique() < len(labels):
            silhouette = float(silhouette_score(distance, labels, metric="precomputed"))
        diagnostics.append(
            {
                "k": k,
                "within_cluster_distance": within,
                "silhouette_score": silhouette,
                "selected": False,
            }
        )
    diagnostics_frame = pd.DataFrame(diagnostics)
    if not diagnostics_frame.empty:
        valid = diagnostics_frame["silhouette_score"].replace([np.inf, -np.inf], np.nan)
        selected_index = (
            valid.idxmax() if valid.notna().any() else diagnostics_frame["k"].idxmin()
        )
        diagnostics_frame.loc[selected_index, "selected"] = True
    return {
        "correlation_matrix": corr,
        "high_correlation_pairs": pd.DataFrame(pairs),
        "cluster_diagnostics": diagnostics_frame,
    }


def estimator_comparison(returns: pd.DataFrame) -> pd.DataFrame:
    """Compare covariance estimators without changing portfolio decisions."""
    clean = _complete_case_returns(returns)
    if clean.empty:
        return pd.DataFrame(
            columns=[
                "Estimator",
                "Average_Variance",
                "Average_Correlation",
                "Status",
            ]
        )
    sample = clean.cov() * TRADING_DAYS_PER_YEAR
    mle = clean.cov(ddof=0) * TRADING_DAYS_PER_YEAR
    lw = pd.DataFrame(
        LedoitWolf().fit(clean.to_numpy(dtype=float)).covariance_
        * TRADING_DAYS_PER_YEAR,
        index=clean.columns,
        columns=clean.columns,
    )
    ewma = clean.ewm(span=63, adjust=False).cov().groupby(level=1).tail(1)
    ewma = ewma.droplevel(0) * TRADING_DAYS_PER_YEAR
    rows = []
    for name, cov in {
        "sample_covariance": sample,
        "mle_normal": mle,
        "ledoit_wolf": lw,
        "ewma_covariance": ewma,
    }.items():
        rows.append(
            {
                "Estimator": name,
                "Average_Variance": float(np.diag(cov.to_numpy()).mean()),
                "Average_Correlation": float(
                    clean.corr()
                    .where(~np.eye(clean.shape[1], dtype=bool))
                    .stack()
                    .mean()
                ),
                "Status": "computed",
            }
        )
    return pd.DataFrame(rows)


def stress_test_portfolio(weights: pd.Series, metadata: pd.DataFrame) -> pd.DataFrame:
    """Apply stylized sleeve-level shocks to a global portfolio."""
    scenarios = {
        "equity_crash": {"global_equity": -0.25, "crypto": -0.35, "defensive": 0.04},
        "rate_shock": {"defensive": -0.08, "global_equity": -0.08},
        "commodity_shock": {"commodity": -0.15, "global_equity": -0.03},
        "fx_shock": {"non_usd": -0.10},
        "crypto_crash": {"crypto": -0.50},
    }
    meta = metadata.set_index("ticker") if "ticker" in metadata else pd.DataFrame()
    rows = []
    for scenario, shocks in scenarios.items():
        impact = 0.0
        for ticker, weight in weights.items():
            sleeve = str(meta.loc[ticker, "sleeve"]) if ticker in meta.index else ""
            currency = str(meta.loc[ticker, "currency"]) if ticker in meta.index else ""
            shock = 0.0
            if sleeve.startswith("global_equity"):
                shock += shocks.get("global_equity", 0.0)
            if "crypto" in sleeve.lower():
                shock += shocks.get("crypto", 0.0)
            if sleeve == "commodity_real_assets":
                shock += shocks.get("commodity", 0.0)
            if sleeve == "defensive_bonds_cash":
                shock += shocks.get("defensive", 0.0)
            if currency and currency.upper() != "USD":
                shock += shocks.get("non_usd", 0.0)
            impact += float(weight) * shock
        rows.append({"Scenario": scenario, "Portfolio_Impact": float(impact)})
    return pd.DataFrame(rows)


def _align_returns_weights(
    returns: pd.DataFrame,
    weights: pd.Series,
) -> tuple[pd.DataFrame, pd.Series]:
    selected = [asset for asset in weights.index if asset in returns]
    if not selected:
        raise ValueError("No weight tickers overlap the returns matrix.")
    clean = returns[selected].apply(pd.to_numeric, errors="coerce").dropna(how="any")
    if clean.shape[0] < 2:
        raise ValueError(
            "At least two complete common return observations are required; "
            "missing returns are not imputed as zero."
        )
    aligned = pd.Series(weights.loc[selected], dtype=float)
    aligned = aligned / aligned.sum()
    return clean, aligned


def _complete_case_returns(returns: pd.DataFrame) -> pd.DataFrame:
    clean = (
        returns.apply(pd.to_numeric, errors="coerce")
        .dropna(axis=1, how="all")
        .dropna(how="any")
    )
    return clean if clean.shape[0] >= 2 else clean.iloc[0:0]


def _within_cluster_distance(distance: np.ndarray, labels: np.ndarray) -> float:
    distances: list[float] = []
    for label in sorted(set(labels)):
        idx = np.where(labels == label)[0]
        if len(idx) > 1:
            subset = distance[np.ix_(idx, idx)]
            distances.extend(subset[np.triu_indices(len(idx), k=1)].tolist())
    return float(np.mean(distances)) if distances else 0.0
