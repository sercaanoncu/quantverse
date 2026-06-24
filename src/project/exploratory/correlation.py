"""
Correlation Analysis & Structure Detection
============================================
Rolling correlations, regime-dependent correlation,
PCA-based structure analysis, and correlation stability.
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Advanced correlation analysis for multi-asset portfolio construction."""

    def __init__(self, returns: pd.DataFrame, asset_class_map: Optional[Dict] = None):
        self.returns = returns.dropna(how="all")
        self.asset_class_map = asset_class_map or {}
        self.tickers = list(returns.columns)

    # ------------------------------------------------------------------
    # 1. Rolling Correlation
    # ------------------------------------------------------------------
    def rolling_correlation(
        self, ticker_a: str, ticker_b: str, window: int = 63
    ) -> pd.Series:
        """Compute rolling pairwise correlation between two assets."""
        return self.returns[ticker_a].rolling(window).corr(self.returns[ticker_b])

    def rolling_correlation_matrix(
        self, window: int = 63, step: int = 21
    ) -> Dict[str, pd.DataFrame]:
        """
        Compute rolling correlation matrices at regular intervals.

        Parameters
        ----------
        window : int
            Rolling window in trading days
        step : int
            Step size between snapshots (default 21 ≈ 1 month)

        Returns
        -------
        dict mapping date_str -> correlation DataFrame
        """
        dates = self.returns.index[window::step]
        snapshots = {}
        for date in dates:
            start = self.returns.index[self.returns.index.get_loc(date) - window]
            subset = self.returns.loc[start:date]
            snapshots[str(date.date())] = subset.corr()

        logger.info(f"Computed {len(snapshots)} rolling correlation snapshots")
        return snapshots

    def average_rolling_correlation(self, window: int = 63) -> pd.Series:
        """
        Compute the rolling average pairwise correlation across all assets.
        This is a market-wide "correlation regime" indicator.
        """
        corr_ts = []
        for i in range(window, len(self.returns)):
            subset = self.returns.iloc[i - window : i]
            corr_matrix = subset.corr()
            # Average of off-diagonal elements
            mask = np.ones(corr_matrix.shape, dtype=bool)
            np.fill_diagonal(mask, False)
            avg_corr = corr_matrix.values[mask].mean()
            corr_ts.append({"Date": self.returns.index[i], "Avg_Correlation": avg_corr})

        return pd.DataFrame(corr_ts).set_index("Date")["Avg_Correlation"]

    # ------------------------------------------------------------------
    # 2. Regime-Dependent Correlation
    # ------------------------------------------------------------------
    def crisis_vs_calm_correlation(
        self, market_proxy: str = "XLK", threshold_pct: float = 10.0
    ) -> Dict[str, pd.DataFrame]:
        """
        Compare correlations during crisis periods vs calm periods.

        Crisis: days when market_proxy has worst `threshold_pct`% returns
        Calm: remaining days

        This demonstrates that correlations increase during market stress
        (a critical risk management insight).
        """
        if market_proxy not in self.returns.columns:
            # Fallback: use average of all returns
            proxy = self.returns.mean(axis=1)
        else:
            proxy = self.returns[market_proxy]

        cutoff = proxy.quantile(threshold_pct / 100)

        crisis_mask = proxy <= cutoff
        calm_mask = ~crisis_mask

        crisis_corr = self.returns[crisis_mask].corr()
        calm_corr = self.returns[calm_mask].corr()

        diff = crisis_corr - calm_corr

        n_crisis = crisis_mask.sum()
        n_calm = calm_mask.sum()
        logger.info(f"Crisis/Calm split: {n_crisis} crisis days, {n_calm} calm days")

        return {
            "crisis": crisis_corr,
            "calm": calm_corr,
            "difference": diff,
            "n_crisis": n_crisis,
            "n_calm": n_calm,
        }

    def tail_dependence(self, threshold_pct: float = 5.0) -> pd.DataFrame:
        """
        Estimate lower tail dependence between asset pairs.
        Measures how likely two assets are to crash simultaneously.

        Uses empirical exceedance approach: P(Y < q_y | X < q_x)
        """
        n = len(self.tickers)
        result = pd.DataFrame(
            np.zeros((n, n)), index=self.tickers, columns=self.tickers
        )

        for i in range(n):
            for j in range(i + 1, n):
                r_i = self.returns[self.tickers[i]].dropna()
                r_j = self.returns[self.tickers[j]].dropna()

                common = r_i.index.intersection(r_j.index)
                r_i, r_j = r_i[common], r_j[common]

                q_i = r_i.quantile(threshold_pct / 100)
                q_j = r_j.quantile(threshold_pct / 100)

                joint_exceedance = ((r_i <= q_i) & (r_j <= q_j)).sum()
                marginal_exceedance = (r_i <= q_i).sum()

                td = (
                    joint_exceedance / marginal_exceedance
                    if marginal_exceedance > 0
                    else 0
                )
                result.iloc[i, j] = td
                result.iloc[j, i] = td

        np.fill_diagonal(result.values, 1.0)
        return result

    # ------------------------------------------------------------------
    # 3. PCA - Principal Component Analysis
    # ------------------------------------------------------------------
    def pca_analysis(self, n_components: Optional[int] = None) -> Dict:
        """
        Perform PCA on return correlations to identify dominant risk factors.

        Returns
        -------
        dict with:
        - explained_variance_ratio: variance explained per component
        - cumulative_variance: cumulative variance explained
        - loadings: asset loadings on each component
        - n_components_90pct: components needed to explain 90% variance
        """
        clean = self.returns.dropna()
        if n_components is None:
            n_components = min(len(self.tickers), len(clean))

        # Standardize so PCA operates on correlation structure, not covariance
        # (prevents high-volatility assets from dominating principal components)
        scaler = StandardScaler()
        clean_scaled = scaler.fit_transform(clean)

        pca = PCA(n_components=n_components)
        pca.fit(clean_scaled)

        loadings = pd.DataFrame(
            pca.components_.T,
            index=self.tickers,
            columns=[f"PC{i + 1}" for i in range(n_components)],
        )

        cumvar = np.cumsum(pca.explained_variance_ratio_)
        n90 = np.argmax(cumvar >= 0.90) + 1

        logger.info(
            f"PCA: {n90} components explain 90% variance. PC1 = {pca.explained_variance_ratio_[0]:.1%}"
        )

        return {
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_variance": cumvar,
            "loadings": loadings,
            "n_components_90pct": n90,
            "pca_model": pca,
        }

    # ------------------------------------------------------------------
    # 4. Correlation Clusters
    # ------------------------------------------------------------------
    def correlation_clusters(self, n_clusters: int = 4) -> pd.DataFrame:
        """
        Cluster assets based on correlation structure using K-Means on
        the correlation matrix.
        """
        corr = self.returns.corr()
        # Use correlation matrix as feature space
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(corr)

        result = pd.DataFrame(
            {
                "Ticker": self.tickers,
                "Cluster": labels,
                "Asset_Class": [
                    self.asset_class_map.get(t, "unknown") for t in self.tickers
                ],
            }
        ).set_index("Ticker")

        return result

    # ------------------------------------------------------------------
    # 5. Correlation Stability
    # ------------------------------------------------------------------
    def correlation_stability(self, window: int = 126, step: int = 21) -> pd.DataFrame:
        """
        Measure how stable pairwise correlations are over time.
        Returns the standard deviation of rolling correlations for each pair.

        High instability → correlation is regime-dependent → dangerous for
        static portfolio optimization.
        """
        pairs = []
        for i in range(len(self.tickers)):
            for j in range(i + 1, len(self.tickers)):
                t_a, t_b = self.tickers[i], self.tickers[j]
                rolling_corr = self.rolling_correlation(t_a, t_b, window=window)
                pairs.append(
                    {
                        "Asset_A": t_a,
                        "Asset_B": t_b,
                        "Mean_Corr": rolling_corr.mean(),
                        "Std_Corr": rolling_corr.std(),
                        "Min_Corr": rolling_corr.min(),
                        "Max_Corr": rolling_corr.max(),
                        "Range_Corr": rolling_corr.max() - rolling_corr.min(),
                    }
                )

        df = pd.DataFrame(pairs)
        df = df.sort_values("Std_Corr", ascending=False)
        return df

    # ------------------------------------------------------------------
    # 6. Dendrogram / Distance Matrix
    # ------------------------------------------------------------------
    def distance_matrix(self, method: str = "angular") -> pd.DataFrame:
        """
        Convert correlation matrix to a distance matrix.

        Methods:
        - 'angular': d = sqrt(0.5 * (1 - corr))  (used in HRP)
        - 'abs_angular': d = sqrt(0.5 * (1 - |corr|))
        - 'squared': d = sqrt(1 - corr²)
        """
        corr = self.returns.corr()

        if method == "angular":
            dist = np.sqrt(0.5 * (1 - corr))
        elif method == "abs_angular":
            dist = np.sqrt(0.5 * (1 - corr.abs()))
        elif method == "squared":
            dist = np.sqrt(1 - corr**2)
        else:
            raise ValueError(f"Unknown method: {method}")

        return dist
