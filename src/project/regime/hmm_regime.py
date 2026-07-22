"""
Hidden Markov Model Regime Detection
======================================
Identify latent market regimes (bull/bear/sideways) using
Gaussian Hidden Markov Models on portfolio/market returns.

Regimes are characterized by different means and volatilities.
"""

import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class HMMRegimeDetector:
    """
    Gaussian HMM-based regime detection.

    Identifies hidden states in return data where each state
    has its own mean return and volatility.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        n_regimes: int = 3,
        features: Optional[List[str]] = None,
    ):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Daily asset returns
        n_regimes : int
            Number of hidden states (2=bull/bear, 3=bull/bear/sideways)
        features : list, optional
            Which features to use for regime detection.
            If None, uses portfolio return + rolling vol + rolling skew.
        """
        self.returns = returns.dropna()
        self.n_regimes = n_regimes
        self.tickers = list(returns.columns)
        self.model = None
        self.states = None
        self.regime_stats = None

    def _build_features(
        self, port_returns: pd.Series, window: int = 21
    ) -> pd.DataFrame:
        """Build feature matrix for HMM from portfolio returns."""
        features = pd.DataFrame(index=port_returns.index)
        features["return"] = port_returns
        features["vol_21d"] = port_returns.rolling(window).std() * np.sqrt(252)
        features["skew_21d"] = port_returns.rolling(window).skew()
        features["momentum_63d"] = port_returns.rolling(63).mean() * 252
        features["vol_change"] = features["vol_21d"].pct_change(window)
        return features.dropna()

    def fit(
        self, port_returns: pd.Series, n_iter: int = 200, random_state: int = 42
    ) -> "HMMRegimeDetector":
        """
        Fit Gaussian HMM to return features.

        Parameters
        ----------
        port_returns : pd.Series
            Portfolio or market return series
        """
        features = self._build_features(port_returns)
        self.feature_dates = features.index
        X = features.values

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Fit HMM
        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=n_iter,
            random_state=random_state,
            tol=1e-4,
        )
        self.model.fit(X_scaled)

        # Predict states
        self.states = self.model.predict(X_scaled)
        self.state_probs = self.model.predict_proba(X_scaled)

        # Log-likelihood and convergence
        self.log_likelihood = self.model.score(X_scaled)
        self.aic = -2 * self.log_likelihood + 2 * self._n_params()
        self.bic = -2 * self.log_likelihood + np.log(len(X_scaled)) * self._n_params()

        # Compute regime statistics
        self._compute_regime_stats(port_returns)

        logger.info(
            f"HMM fitted: {self.n_regimes} regimes, "
            f"LL={self.log_likelihood:.1f}, BIC={self.bic:.1f}"
        )
        return self

    def _n_params(self) -> int:
        """Number of free parameters in the HMM."""
        k = self.n_regimes
        n_feat = len(self.scaler.mean_)
        # Means + covariances + transition matrix + initial probs
        return k * n_feat + k * n_feat * (n_feat + 1) // 2 + k * (k - 1) + (k - 1)

    def _compute_regime_stats(self, port_returns: pd.Series):
        """Compute return and risk statistics per regime."""
        aligned = port_returns.reindex(self.feature_dates)
        stats = {}

        for i in range(self.n_regimes):
            mask = self.states == i
            regime_ret = aligned[mask]
            stats[i] = {
                "mean_return_ann": regime_ret.mean() * 252,
                "volatility_ann": regime_ret.std() * np.sqrt(252),
                "sharpe": (
                    regime_ret.mean() / regime_ret.std() * np.sqrt(252)
                    if regime_ret.std() > 0
                    else 0
                ),
                "n_days": mask.sum(),
                "pct_time": mask.mean() * 100,
                "avg_duration": self._avg_duration(mask),
                "skewness": float(regime_ret.skew()) if len(regime_ret) > 2 else 0,
                "max_drawdown": self._max_dd(regime_ret),
            }

        # Sort by volatility: low vol = "bull", high vol = "bear"
        sorted_regimes = sorted(stats.items(), key=lambda x: x[1]["volatility_ann"])
        self.regime_labels = {}
        # Dynamic label generation for any n_regimes
        if self.n_regimes == 2:
            labels = ["Low Vol (Bull)", "High Vol (Bear)"]
        elif self.n_regimes == 3:
            labels = ["Low Vol (Bull)", "Medium Vol (Sideways)", "High Vol (Bear)"]
        else:
            labels = [
                f"Regime {i+1} (Vol Rank {i+1}/{self.n_regimes})"
                for i in range(self.n_regimes)
            ]
            labels[0] = "Low Vol (Bull)"
            labels[-1] = "High Vol (Bear)"
        for idx, (regime_id, _) in enumerate(sorted_regimes):
            self.regime_labels[regime_id] = labels[idx]

        self.regime_stats = {self.regime_labels[k]: v for k, v in stats.items()}

    def _avg_duration(self, mask: np.ndarray) -> float:
        """Average number of consecutive days in a regime."""
        changes = np.diff(mask.astype(int))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        if len(starts) == 0 or len(ends) == 0:
            return mask.sum()
        if ends[0] < starts[0]:
            ends = ends[1:]
        n = min(len(starts), len(ends))
        if n == 0:
            return mask.sum()
        durations = ends[:n] - starts[:n]
        return durations.mean()

    def _max_dd(self, returns: pd.Series) -> float:
        if len(returns) < 2:
            return 0
        cum = (1 + returns).cumprod()
        return (cum / cum.cummax().clip(lower=1.0) - 1).min()

    # ------------------------------------------------------------------
    # Outputs
    # ------------------------------------------------------------------
    def get_regime_series(self) -> pd.Series:
        """Return regime labels as a time series."""
        labels = [self.regime_labels[s] for s in self.states]
        return pd.Series(labels, index=self.feature_dates, name="Regime")

    def get_regime_probabilities(self) -> pd.DataFrame:
        """Return regime probabilities over time."""
        cols = [self.regime_labels[i] for i in range(self.n_regimes)]
        return pd.DataFrame(self.state_probs, index=self.feature_dates, columns=cols)

    def get_transition_matrix(self) -> pd.DataFrame:
        """Return regime transition probability matrix."""
        labels = [self.regime_labels[i] for i in range(self.n_regimes)]
        return pd.DataFrame(self.model.transmat_, index=labels, columns=labels)

    def get_regime_summary(self) -> pd.DataFrame:
        """Return summary statistics per regime."""
        return pd.DataFrame(self.regime_stats).T

    def current_regime(self) -> str:
        """Return the current (last) regime."""
        return self.regime_labels[self.states[-1]]

    def current_probabilities(self) -> Dict[str, float]:
        """Return current regime probabilities."""
        probs = self.state_probs[-1]
        return {self.regime_labels[i]: probs[i] for i in range(self.n_regimes)}

    # ------------------------------------------------------------------
    # Optimal Number of Regimes
    # ------------------------------------------------------------------
    def select_n_regimes(
        self, port_returns: pd.Series, max_regimes: int = 5
    ) -> pd.DataFrame:
        """
        Compare BIC/AIC across different numbers of regimes
        to help select the optimal model.
        """
        results = []
        for n in range(2, max_regimes + 1):
            try:
                det = HMMRegimeDetector(self.returns, n_regimes=n)
                det.fit(port_returns)
                results.append(
                    {
                        "N_Regimes": n,
                        "Log_Likelihood": det.log_likelihood,
                        "AIC": det.aic,
                        "BIC": det.bic,
                    }
                )
            except Exception as e:
                logger.warning(f"HMM with {n} regimes failed: {e}")

        return pd.DataFrame(results).set_index("N_Regimes")
