"""
Clustering-Based Regime Detection
====================================
Use K-Means on market features to identify regimes
without parametric distributional assumptions.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class ClusteringRegimeDetector:
    """
    K-Means clustering on market features for regime identification.

    Features: rolling return, volatility, correlation, momentum, etc.
    Simpler and more robust than HMM in some cases.
    """

    def __init__(self, returns: pd.DataFrame, n_regimes: int = 3):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n_regimes = n_regimes

    def _build_features(
        self, port_returns: pd.Series, window: int = 21
    ) -> pd.DataFrame:
        """Build multi-scale feature matrix."""
        f = pd.DataFrame(index=port_returns.index)

        # Returns at multiple horizons
        f["ret_5d"] = port_returns.rolling(5).mean() * 252
        f["ret_21d"] = port_returns.rolling(21).mean() * 252
        f["ret_63d"] = port_returns.rolling(63).mean() * 252

        # Volatility
        f["vol_21d"] = port_returns.rolling(21).std() * np.sqrt(252)
        f["vol_63d"] = port_returns.rolling(63).std() * np.sqrt(252)
        f["vol_ratio"] = f["vol_21d"] / f["vol_63d"].replace(0, np.nan)

        # Momentum
        f["momentum"] = port_returns.rolling(63).sum()

        # Drawdown level
        cum = (1 + port_returns).cumprod()
        f["drawdown"] = cum / cum.cummax().clip(lower=1.0) - 1

        # Average cross-asset correlation (market stress indicator)
        rolling_corr = self.returns.rolling(window).corr()
        n = len(self.tickers)
        avg_corrs = []
        for date in self.returns.index:
            try:
                corr_mat = rolling_corr.loc[date].values
                mask = ~np.eye(n, dtype=bool)
                avg_corrs.append(corr_mat[mask].mean())
            except (KeyError, ValueError, IndexError):
                avg_corrs.append(np.nan)
        f["avg_correlation"] = avg_corrs

        return f.dropna()

    def fit(
        self, port_returns: pd.Series, random_state: int = 42
    ) -> "ClusteringRegimeDetector":
        """Fit K-Means on market features."""
        features = self._build_features(port_returns)
        self.feature_dates = features.index
        X = features.values

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = KMeans(
            n_clusters=self.n_regimes,
            random_state=random_state,
            n_init=20,
            max_iter=500,
        )
        self.labels = self.model.fit_predict(X_scaled)

        # Compute stats and assign labels
        self._compute_stats(port_returns)

        # Inertia for elbow method
        self.inertia = self.model.inertia_

        logger.info(f"Clustering regime detection: {self.n_regimes} regimes fitted")
        return self

    def _compute_stats(self, port_returns: pd.Series):
        """Compute per-regime stats and assign meaningful labels."""
        aligned = port_returns.reindex(self.feature_dates)

        stats = {}
        for i in range(self.n_regimes):
            mask = self.labels == i
            r = aligned[mask]
            stats[i] = {
                "mean_return_ann": r.mean() * 252,
                "volatility_ann": r.std() * np.sqrt(252),
                "sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0,
                "n_days": mask.sum(),
                "pct_time": mask.mean() * 100,
            }

        # Label by volatility
        sorted_regimes = sorted(stats.items(), key=lambda x: x[1]["volatility_ann"])
        if self.n_regimes == 2:
            labels_list = ["Low Vol", "High Vol"]
        elif self.n_regimes == 3:
            labels_list = ["Low Vol", "Medium Vol", "High Vol"]
        else:
            labels_list = [
                f"Regime {i + 1} (Vol Rank {i + 1}/{self.n_regimes})"
                for i in range(self.n_regimes)
            ]
            labels_list[0] = "Low Vol"
            labels_list[-1] = "High Vol"
        self.regime_labels = {}
        for idx, (rid, _) in enumerate(sorted_regimes):
            self.regime_labels[rid] = labels_list[idx]

        self.regime_stats = {self.regime_labels[k]: v for k, v in stats.items()}

    def get_regime_series(self) -> pd.Series:
        labels = [self.regime_labels[l] for l in self.labels]
        return pd.Series(labels, index=self.feature_dates, name="Regime")

    def get_regime_summary(self) -> pd.DataFrame:
        return pd.DataFrame(self.regime_stats).T

    def current_regime(self) -> str:
        return self.regime_labels[self.labels[-1]]

    def elbow_analysis(self, port_returns: pd.Series, max_k: int = 6) -> pd.DataFrame:
        """Run elbow method to find optimal number of clusters."""
        features = self._build_features(port_returns)
        X_scaled = StandardScaler().fit_transform(features.values)

        results = []
        for k in range(2, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=20)
            km.fit(X_scaled)
            results.append({"K": k, "Inertia": km.inertia_})

        return pd.DataFrame(results).set_index("K")
