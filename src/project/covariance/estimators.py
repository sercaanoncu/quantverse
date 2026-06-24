"""
Covariance Matrix Estimation Methods
======================================
Multiple approaches from naive sample covariance to advanced
shrinkage, denoising, and dynamic conditional correlation.
"""

import pandas as pd
import numpy as np
from sklearn.covariance import LedoitWolf, OAS, EmpiricalCovariance
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class CovarianceEstimator:
    """
    Unified interface for multiple covariance estimation methods.

    Each method returns a tuple: (covariance_matrix, correlation_matrix)
    as pd.DataFrames with asset tickers as index/columns.
    """

    def __init__(self, returns: pd.DataFrame):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Daily simple returns (assets as columns), NaN-free
        """
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)
        self.n_obs = len(self.returns)

    def _to_df(self, matrix: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(matrix, index=self.tickers, columns=self.tickers)

    def _cov_to_corr(self, cov: np.ndarray) -> np.ndarray:
        std = np.sqrt(np.diag(cov))
        std_outer = np.outer(std, std)
        std_outer[std_outer == 0] = 1e-10
        return cov / std_outer

    # ------------------------------------------------------------------
    # 1. Sample Covariance
    # ------------------------------------------------------------------
    def sample(self) -> Dict[str, pd.DataFrame]:
        """
        Standard sample covariance matrix.
        Simple but noisy — especially when n_assets / n_obs is high.
        Eigenvalues are distorted (Marchenko-Pastur law).
        """
        cov = self.returns.cov().values
        corr = self._cov_to_corr(cov)
        logger.info(
            f"Sample covariance: {self.n_assets} assets, {self.n_obs} obs, "
            f"ratio = {self.n_assets/self.n_obs:.3f}"
        )
        return {
            "covariance": self._to_df(cov),
            "correlation": self._to_df(corr),
            "method": "Sample",
        }

    # ------------------------------------------------------------------
    # 2. Ledoit-Wolf Shrinkage
    # ------------------------------------------------------------------
    def ledoit_wolf(self) -> Dict[str, pd.DataFrame]:
        """
        Ledoit-Wolf linear shrinkage toward a structured target.
        Optimal shrinkage intensity is estimated analytically.

        Shrinks sample covariance toward scaled identity:
        Σ_LW = α·F + (1-α)·S
        where F = target, S = sample, α = shrinkage intensity
        """
        lw = LedoitWolf().fit(self.returns.values)
        cov = lw.covariance_
        corr = self._cov_to_corr(cov)
        shrinkage = lw.shrinkage_

        logger.info(f"Ledoit-Wolf shrinkage intensity: {shrinkage:.4f}")
        return {
            "covariance": self._to_df(cov),
            "correlation": self._to_df(corr),
            "method": "Ledoit-Wolf",
            "shrinkage": shrinkage,
        }

    # ------------------------------------------------------------------
    # 3. Oracle Approximating Shrinkage (OAS)
    # ------------------------------------------------------------------
    def oracle_approximating(self) -> Dict[str, pd.DataFrame]:
        """
        OAS — better shrinkage formula when n_assets is large relative to n_obs.
        Assumes the covariance has a spiked population model.
        """
        oas = OAS().fit(self.returns.values)
        cov = oas.covariance_
        corr = self._cov_to_corr(cov)
        shrinkage = oas.shrinkage_

        logger.info(f"OAS shrinkage intensity: {shrinkage:.4f}")
        return {
            "covariance": self._to_df(cov),
            "correlation": self._to_df(corr),
            "method": "OAS",
            "shrinkage": shrinkage,
        }

    # ------------------------------------------------------------------
    # 4. Exponentially Weighted (EWMA)
    # ------------------------------------------------------------------
    def ewma(
        self, halflife: int = 63, min_periods: int = 30
    ) -> Dict[str, pd.DataFrame]:
        """
        Exponentially Weighted Moving Average covariance.
        Recent observations get more weight — captures regime changes faster.

        Parameters
        ----------
        halflife : int
            Half-life in trading days (63 ≈ 3 months, RiskMetrics uses ~74)
        """
        span = 2 * halflife  # approximate span from halflife
        ewm_cov = self.returns.ewm(halflife=halflife, min_periods=min_periods).cov()

        # Extract the last date's covariance matrix
        last_date = self.returns.index[-1]
        cov_last = ewm_cov.loc[last_date].values
        corr = self._cov_to_corr(cov_last)

        logger.info(f"EWMA covariance: halflife={halflife} days")
        return {
            "covariance": self._to_df(cov_last),
            "correlation": self._to_df(corr),
            "method": f"EWMA (hl={halflife})",
            "halflife": halflife,
        }

    # ------------------------------------------------------------------
    # 5. Constant Correlation Model
    # ------------------------------------------------------------------
    def constant_correlation(self) -> Dict[str, pd.DataFrame]:
        """
        Elton & Gruber (1973) constant correlation model.
        All pairwise correlations are set to the average correlation.
        Simple but surprisingly robust — often used as shrinkage target.
        """
        sample_corr = self.returns.corr().values
        n = self.n_assets

        # Average off-diagonal correlation
        mask = ~np.eye(n, dtype=bool)
        avg_corr = sample_corr[mask].mean()

        # Construct constant correlation matrix
        const_corr = np.full((n, n), avg_corr)
        np.fill_diagonal(const_corr, 1.0)

        # Convert to covariance using sample standard deviations
        std = self.returns.std().values
        cov = const_corr * np.outer(std, std)

        logger.info(f"Constant correlation: ρ̄ = {avg_corr:.4f}")
        return {
            "covariance": self._to_df(cov),
            "correlation": self._to_df(const_corr),
            "method": "Constant Correlation",
            "avg_correlation": avg_corr,
        }

    # ------------------------------------------------------------------
    # 6. Denoised Covariance (Random Matrix Theory)
    # ------------------------------------------------------------------
    def denoised(self, method: str = "constant_residual") -> Dict[str, pd.DataFrame]:
        """
        Denoise correlation matrix using Random Matrix Theory.

        Based on Marchenko-Pastur distribution: eigenvalues below the
        theoretical maximum for random matrices are replaced.

        Methods:
        - 'constant_residual': replace noise eigenvalues with their average
        - 'targeted_shrinkage': shrink noise eigenvalues toward identity

        Reference: López de Prado (2020) "Machine Learning for Asset Managers"
        """
        corr = self.returns.corr().values
        n = self.n_assets
        t = self.n_obs
        q = n / t  # ratio

        # Eigendecomposition
        eigenvalues, eigenvectors = np.linalg.eigh(corr)
        # Sort descending
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Marchenko-Pastur bounds
        lambda_plus = (1 + np.sqrt(q)) ** 2
        lambda_minus = (1 - np.sqrt(q)) ** 2

        # Identify signal vs noise eigenvalues
        n_signal = np.sum(eigenvalues > lambda_plus)
        n_noise = n - n_signal

        logger.info(
            f"Denoised: {n_signal} signal eigenvalues, {n_noise} noise "
            f"(MP upper bound: {lambda_plus:.3f})"
        )

        if method == "constant_residual":
            # Replace noise eigenvalues with their average
            if n_noise > 0:
                noise_avg = eigenvalues[n_signal:].mean()
                eigenvalues_clean = eigenvalues.copy()
                eigenvalues_clean[n_signal:] = noise_avg
            else:
                eigenvalues_clean = eigenvalues.copy()
        elif method == "targeted_shrinkage":
            # Shrink noise eigenvalues toward 1 (identity)
            eigenvalues_clean = eigenvalues.copy()
            for i in range(n_signal, n):
                eigenvalues_clean[i] = 1.0
        else:
            raise ValueError(f"Unknown method: {method}")

        # Reconstruct correlation matrix and rescale to preserve PSD property
        corr_clean = eigenvectors @ np.diag(eigenvalues_clean) @ eigenvectors.T
        diag_sqrt = np.sqrt(np.diag(corr_clean))
        diag_sqrt[diag_sqrt == 0] = 1e-10
        corr_clean = corr_clean / np.outer(diag_sqrt, diag_sqrt)
        corr_clean = np.clip(corr_clean, -1, 1)

        # Convert to covariance
        std = self.returns.std().values
        cov_clean = corr_clean * np.outer(std, std)

        return {
            "covariance": self._to_df(cov_clean),
            "correlation": self._to_df(corr_clean),
            "method": f"Denoised ({method})",
            "n_signal": n_signal,
            "n_noise": n_noise,
            "mp_upper_bound": lambda_plus,
            "eigenvalues_original": eigenvalues,
            "eigenvalues_denoised": eigenvalues_clean,
        }

    # ------------------------------------------------------------------
    # 7. Gerber Statistic Covariance
    # ------------------------------------------------------------------
    def gerber(self, threshold: float = 0.5) -> Dict[str, pd.DataFrame]:
        """
        Gerber statistic — a robust co-movement measure that focuses on
        concordant/discordant moves beyond a threshold.

        Only counts days where both assets move beyond their threshold
        (measured in standard deviations). Ignores noise-level moves.

        Reference: Gerber, Markowitz, et al. (2022)
        """
        data = self.returns.values
        n = self.n_assets
        t = self.n_obs

        # Standardize (using ddof=1 for sample std, consistent with pandas)
        stds = data.std(axis=0, ddof=1)
        thresholds = threshold * stds

        # Classify: +1 (up), -1 (down), 0 (noise)
        signs = np.zeros_like(data)
        for j in range(n):
            signs[data[:, j] > thresholds[j], j] = 1
            signs[data[:, j] < -thresholds[j], j] = -1

        # Gerber statistic
        gerber_corr = np.zeros((n, n))
        for i in range(n):
            for j in range(i, n):
                both_significant = (signs[:, i] != 0) & (signs[:, j] != 0)
                if both_significant.sum() == 0:
                    gerber_corr[i, j] = 0
                else:
                    concordant = (
                        signs[both_significant, i] == signs[both_significant, j]
                    ).sum()
                    discordant = (
                        signs[both_significant, i] != signs[both_significant, j]
                    ).sum()
                    total = concordant + discordant
                    gerber_corr[i, j] = (
                        (concordant - discordant) / total if total > 0 else 0
                    )
                gerber_corr[j, i] = gerber_corr[i, j]

        np.fill_diagonal(gerber_corr, 1.0)

        # Convert to covariance
        std_vec = self.returns.std().values
        cov = gerber_corr * np.outer(std_vec, std_vec)

        logger.info(f"Gerber statistic: threshold = {threshold}σ")
        return {
            "covariance": self._to_df(cov),
            "correlation": self._to_df(gerber_corr),
            "method": f"Gerber (θ={threshold})",
            "threshold": threshold,
        }

    # ------------------------------------------------------------------
    # 8. All Estimators
    # ------------------------------------------------------------------
    def estimate_all(self, ewma_halflife: int = 63) -> Dict[str, Dict]:
        """Run all covariance estimation methods and return results."""
        results = {}

        for name, func in [
            ("Sample", self.sample),
            ("Ledoit-Wolf", self.ledoit_wolf),
            ("OAS", self.oracle_approximating),
            ("Constant Corr", self.constant_correlation),
            ("Denoised (RMT)", self.denoised),
            ("Gerber", self.gerber),
        ]:
            try:
                results[name] = func()
            except Exception as e:
                logger.warning(f"Failed: {name} — {e}")

        try:
            results[f"EWMA (hl={ewma_halflife})"] = self.ewma(halflife=ewma_halflife)
        except Exception as e:
            logger.warning(f"Failed: EWMA — {e}")

        logger.info(f"Computed {len(results)} covariance estimators")
        return results
