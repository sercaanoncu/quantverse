"""
Hierarchical Risk Parity (HRP)
================================
Machine learning-based portfolio allocation that doesn't
require covariance matrix inversion.

Reference: López de Prado (2016), "Building Diversified Portfolios
that Outperform Out-of-Sample"
"""

import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
import logging
from typing import Dict, Optional

from .constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


class HRPOptimizer:
    """
    Hierarchical Risk Parity portfolio construction.

    Steps:
    1. Tree Clustering: hierarchical clustering on correlation distance
    2. Quasi-Diagonalization: reorder assets so similar ones are adjacent
    3. Recursive Bisection: allocate weights by splitting variance

    Key advantage: does NOT invert the covariance matrix,
    making it robust to estimation error.
    """

    def __init__(
        self, returns: pd.DataFrame, cov_matrix: Optional[pd.DataFrame] = None
    ):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Daily returns for computing correlations
        cov_matrix : pd.DataFrame, optional
            Pre-computed covariance. If None, computed from returns.
        """
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n = len(self.tickers)

        if cov_matrix is not None:
            if (
                list(cov_matrix.index) != self.tickers
                or list(cov_matrix.columns) != self.tickers
            ):
                raise ValueError(
                    "Covariance matrix labels must match returns columns in the same order"
                )
            self.cov = cov_matrix
        else:
            self.cov = self.returns.cov() * 252  # annualize

        self.corr = self.returns.corr()

    def _correlation_distance(self) -> np.ndarray:
        """Convert correlation to distance: d = sqrt(0.5 * (1 - ρ))"""
        dist = np.sqrt(0.5 * (1 - self.corr.values))
        np.fill_diagonal(dist, 0)
        return dist

    def _tree_clustering(self, method: str = "single") -> np.ndarray:
        """
        Step 1: Hierarchical clustering on correlation distance.

        Methods: 'single', 'complete', 'average', 'ward'
        """
        dist = self._correlation_distance()
        condensed = squareform(dist)
        link = linkage(condensed, method=method)
        return link

    def _quasi_diagonalize(self, link: np.ndarray) -> list:
        """
        Step 2: Reorder assets so correlated ones are adjacent.
        This is the seriation step.
        """
        return list(leaves_list(link))

    def _recursive_bisection(self, sorted_idx: list) -> pd.Series:
        """
        Step 3: Recursive bisection to allocate weights.

        Split the sorted assets into two clusters, then allocate
        proportional to inverse cluster variance. Recurse.
        """
        weights = pd.Series(1.0, index=self.tickers)
        cluster_items = [sorted_idx]

        while cluster_items:
            new_clusters = []
            for items in cluster_items:
                if len(items) <= 1:
                    continue

                # Split in half
                mid = len(items) // 2
                left = items[:mid]
                right = items[mid:]

                # Cluster variance = w_ivp' Σ w_ivp (inverse variance portfolio within cluster)
                left_var = self._cluster_variance(left)
                right_var = self._cluster_variance(right)

                # Allocation factor
                alpha = 1 - left_var / (left_var + right_var)

                # Update weights
                left_tickers = [self.tickers[i] for i in left]
                right_tickers = [self.tickers[i] for i in right]

                weights[left_tickers] *= alpha
                weights[right_tickers] *= 1 - alpha

                new_clusters.append(left)
                new_clusters.append(right)

            cluster_items = [c for c in new_clusters if len(c) > 1]

        return weights

    def _cluster_variance(self, indices: list) -> float:
        """
        Compute the variance of the inverse-variance portfolio
        within a cluster of assets.
        """
        tickers = [self.tickers[i] for i in indices]
        cov_sub = self.cov.loc[tickers, tickers].values

        # Inverse variance weights
        ivp_w = 1 / np.diag(cov_sub)
        ivp_w = ivp_w / ivp_w.sum()

        return ivp_w @ cov_sub @ ivp_w

    def _project_to_constraints(
        self,
        weights: pd.Series,
        constraints: PortfolioConstraints,
    ) -> pd.Series:
        """Project long-only HRP weights onto the sum-one box-constrained simplex."""
        constraints.check_feasible(self.n)
        bounds = constraints.get_bounds(self.n)
        lb = np.array([b[0] for b in bounds], dtype=float)
        ub = np.array([b[1] for b in bounds], dtype=float)
        aligned = weights.reindex(self.tickers)
        if aligned.isna().any():
            raise ValueError("HRP produced missing or non-finite asset weights.")
        raw = aligned.to_numpy(dtype=float)
        raw = np.maximum(raw, 0.0) if constraints.long_only else raw
        raw = raw / raw.sum() if abs(raw.sum()) > 1e-12 else np.ones(self.n) / self.n

        lo = np.min(raw - ub)
        hi = np.max(raw - lb)
        for _ in range(100):
            mid = (lo + hi) / 2
            projected = np.clip(raw - mid, lb, ub)
            if projected.sum() > 1.0:
                lo = mid
            else:
                hi = mid
        projected = np.clip(raw - hi, lb, ub)
        projected = projected / projected.sum()
        constraints.assert_valid_weights(projected)
        return pd.Series(projected, index=self.tickers)

    def optimize(
        self,
        method: str = "single",
        constraints: Optional[PortfolioConstraints] = None,
    ) -> Dict:
        """
        Run the full HRP pipeline.

        Parameters
        ----------
        method : str
            Linkage method ('single', 'complete', 'average', 'ward')
        """
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()

        # Step 1: Clustering
        link = self._tree_clustering(method=method)

        # Step 2: Quasi-diagonalization
        sorted_idx = self._quasi_diagonalize(link)

        # Step 3: Recursive bisection
        weights = self._recursive_bisection(sorted_idx)

        # Normalize and enforce portfolio constraints
        weights = weights / weights.sum()
        natural_weights = weights.copy()
        weights = self._project_to_constraints(weights, constraints)

        # Portfolio metrics
        w = weights.values
        ret = w @ (self.returns.mean().values * 252)
        vol = np.sqrt(w @ self.cov.values @ w)
        sharpe = ret / vol if vol > 0 else 0

        logger.info(
            f"HRP: {(weights > 1e-4).sum()} active assets, "
            f"vol={vol*100:.1f}%, sharpe={sharpe:.2f}"
        )

        return {
            "name": f"HRP ({method})",
            "weights": weights,
            "return": ret,
            "volatility": vol,
            "sharpe": sharpe,
            "n_assets": (weights > 1e-4).sum(),
            "max_weight": weights.max(),
            "min_weight": weights.min(),
            "concentration": (weights**2).sum(),
            "linkage": link,
            "sort_order": sorted_idx,
            "natural_weights": natural_weights,
            "constraint_projection": not np.allclose(
                weights.values, natural_weights.values, atol=1e-10
            ),
        }
