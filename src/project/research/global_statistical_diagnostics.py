"""Global return-distribution and clustering diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.covariance import LedoitWolf
from sklearn.decomposition import PCA

from project.constants import TRADING_DAYS_PER_YEAR
from project.projection.portfolio_projection import correlation_diagnostics
from project.research.global_stock_selection import cluster_assets_by_correlation


def clean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Return numeric returns without converting missing observations to zero."""
    return (
        returns.apply(pd.to_numeric, errors="coerce")
        .dropna(axis=0, how="all")
        .dropna(axis=1, how="all")
    )


def summary_statistics(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute asset-level summary statistics."""
    clean = clean_returns(returns)
    rows = []
    for ticker, series in clean.items():
        series = series.dropna().astype(float)
        rows.append(
            {
                "ticker": ticker,
                "observations": int(series.count()),
                "mean_daily": float(series.mean()),
                "annualized_return": float(series.mean() * TRADING_DAYS_PER_YEAR),
                "annualized_volatility": float(
                    series.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
                ),
                "skewness": float(stats.skew(series, nan_policy="omit")),
                "kurtosis": float(stats.kurtosis(series, nan_policy="omit")),
                "min_return": float(series.min()),
                "max_return": float(series.max()),
            }
        )
    return pd.DataFrame(rows)


def normality_tests(returns: pd.DataFrame) -> pd.DataFrame:
    """Run Jarque-Bera normality tests per asset."""
    clean = clean_returns(returns)
    rows = []
    for ticker, series in clean.items():
        series = series.dropna().astype(float)
        if series.count() < 8:
            rows.append(
                {
                    "ticker": ticker,
                    "test": "jarque_bera",
                    "statistic": np.nan,
                    "p_value": np.nan,
                    "normality_result": "insufficient_observations",
                    "robust_method_required": True,
                }
            )
            continue
        statistic, p_value = stats.jarque_bera(series)
        rows.append(
            {
                "ticker": ticker,
                "test": "jarque_bera",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "normality_result": (
                    "reject_normality_5pct"
                    if float(p_value) < 0.05
                    else "do_not_reject_5pct"
                ),
                "robust_method_required": bool(float(p_value) < 0.05),
            }
        )
    return pd.DataFrame(rows)


def stationarity_tests(returns: pd.DataFrame) -> pd.DataFrame:
    """Run optional ADF stationarity tests when statsmodels is installed."""
    clean = clean_returns(returns)
    rows = []
    try:
        from statsmodels.tsa.stattools import adfuller
    except Exception:
        return pd.DataFrame(
            [
                {
                    "ticker": ticker,
                    "test": "adf",
                    "statistic": np.nan,
                    "p_value": np.nan,
                    "stationarity_result": "statsmodels_not_available",
                }
                for ticker in clean.columns
            ]
        )
    for ticker, series in clean.items():
        series = series.dropna().astype(float)
        if series.count() < 30:
            rows.append(
                {
                    "ticker": ticker,
                    "test": "adf",
                    "statistic": np.nan,
                    "p_value": np.nan,
                    "stationarity_result": "insufficient_observations",
                }
            )
            continue
        try:
            result = adfuller(series)
        except (ValueError, np.linalg.LinAlgError) as exc:
            rows.append(
                {
                    "ticker": ticker,
                    "test": "adf",
                    "statistic": np.nan,
                    "p_value": np.nan,
                    "stationarity_result": (
                        f"not_computable_{type(exc).__name__.lower()}"
                    ),
                }
            )
            continue
        rows.append(
            {
                "ticker": ticker,
                "test": "adf",
                "statistic": float(result[0]),
                "p_value": float(result[1]),
                "stationarity_result": (
                    "reject_unit_root_5pct"
                    if float(result[1]) < 0.05
                    else "do_not_reject_unit_root_5pct"
                ),
            }
        )
    return pd.DataFrame(rows)


def pca_summary(returns: pd.DataFrame, max_components: int = 10) -> pd.DataFrame:
    """Summarize PCA explained variance."""
    clean = _complete_case_returns(returns)
    columns = [
        "component",
        "explained_variance_ratio",
        "cumulative_explained_variance",
        "status",
    ]
    if clean.empty:
        return pd.DataFrame(columns=columns)
    if float(clean.var(ddof=1).sum()) <= 1e-15:
        return pd.DataFrame(
            [
                {
                    "component": 1,
                    "explained_variance_ratio": np.nan,
                    "cumulative_explained_variance": np.nan,
                    "status": "not_computable_zero_total_variance",
                }
            ],
            columns=columns,
        )
    n_components = min(max_components, clean.shape[1], clean.shape[0])
    pca = PCA(n_components=n_components, random_state=42)
    pca.fit(clean.to_numpy(dtype=float))
    cumulative = np.cumsum(pca.explained_variance_ratio_)
    return pd.DataFrame(
        {
            "component": range(1, n_components + 1),
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_explained_variance": cumulative,
            "status": "computed",
        }
    ).reindex(columns=columns)


def covariance_estimator_comparison(returns: pd.DataFrame) -> pd.DataFrame:
    """Compare covariance estimators for diagnostics."""
    clean = _complete_case_returns(returns)
    if clean.empty:
        return pd.DataFrame()
    sample = clean.cov() * TRADING_DAYS_PER_YEAR
    mle = clean.cov(ddof=0) * TRADING_DAYS_PER_YEAR
    lw = pd.DataFrame(
        LedoitWolf().fit(clean.to_numpy(dtype=float)).covariance_
        * TRADING_DAYS_PER_YEAR,
        index=clean.columns,
        columns=clean.columns,
    )
    ewma = clean.ewm(span=63, adjust=False).cov().groupby(level=1).tail(1)
    ewma = (
        ewma.droplevel(0).reindex(index=clean.columns, columns=clean.columns)
        * TRADING_DAYS_PER_YEAR
    )
    rows = []
    for name, cov in {
        "sample_covariance": sample,
        "mle_normal_covariance": mle,
        "ledoit_wolf_shrinkage": lw,
        "ewma_covariance": ewma,
    }.items():
        values = cov.to_numpy(dtype=float)
        finite = bool(np.isfinite(values).all())
        eigvals = (
            np.linalg.eigvalsh(0.5 * (values + values.T))
            if finite
            else np.array([np.nan])
        )
        condition_number = float(np.linalg.cond(values)) if finite else np.inf
        psd = bool(finite and np.nanmin(eigvals) >= -1e-10)
        status = (
            "invalid_non_finite"
            if not finite
            else (
                "invalid_non_psd"
                if not psd
                else (
                    "computed_ill_conditioned"
                    if not np.isfinite(condition_number) or condition_number > 1e12
                    else "computed"
                )
            )
        )
        rows.append(
            {
                "estimator": name,
                "average_variance": (
                    float(np.diag(values).mean()) if finite else np.nan
                ),
                "condition_number": condition_number,
                "min_eigenvalue": float(np.nanmin(eigvals)),
                "psd_check": psd,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def cluster_membership(
    returns: pd.DataFrame, max_clusters: int | None = None
) -> pd.DataFrame:
    """Return selected correlation-cluster membership."""
    clean = _complete_case_returns(returns)
    if clean.empty:
        return pd.DataFrame(columns=["ticker", "cluster"])
    clusters = cluster_assets_by_correlation(clean, max_clusters=max_clusters)
    return pd.DataFrame({"ticker": clusters.index, "cluster": clusters.values})


def diagnostics_bundle(returns: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build the full diagnostics output bundle."""
    clean = clean_returns(returns)
    corr_bundle = correlation_diagnostics(clean)
    correlation_columns = list(corr_bundle["correlation_matrix"].columns)
    selected_rows = corr_bundle["cluster_diagnostics"].loc[
        corr_bundle["cluster_diagnostics"]
        .get(
            "selected",
            pd.Series(False, index=corr_bundle["cluster_diagnostics"].index),
        )
        .fillna(False)
        .astype(bool)
    ]
    selected_clusters = (
        int(selected_rows["k"].iloc[0]) if not selected_rows.empty else None
    )
    return {
        "summary_statistics": summary_statistics(clean),
        "normality_tests": normality_tests(clean),
        "stationarity_tests": stationarity_tests(clean),
        "correlation_matrix": corr_bundle["correlation_matrix"],
        "high_correlation_pairs": corr_bundle["high_correlation_pairs"],
        "pca_summary": pca_summary(clean),
        "covariance_estimator_comparison": covariance_estimator_comparison(clean),
        "cluster_diagnostics": corr_bundle["cluster_diagnostics"],
        "cluster_membership": cluster_membership(
            clean[correlation_columns] if correlation_columns else pd.DataFrame(),
            max_clusters=selected_clusters,
        ),
    }


def _complete_case_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Return a common multivariate sample for matrix estimators."""
    clean = clean_returns(returns).dropna(how="any")
    if clean.shape[0] < 2:
        return clean.iloc[0:0]
    return clean
