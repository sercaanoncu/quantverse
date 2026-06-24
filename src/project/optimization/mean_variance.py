"""
Mean-Variance Optimization (Markowitz)
========================================
Classic portfolio optimization with efficient frontier construction,
maximum Sharpe, minimum variance, and target return portfolios.
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import logging
from typing import Dict, Optional, List, Tuple

from project.constants import DEFAULT_RISK_FREE_RATE

from .constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


class MeanVarianceOptimizer:
    """
    Markowitz Mean-Variance Portfolio Optimization.

    Solves: min w'Σw  s.t.  w'μ = target, w'1 = 1, bounds
    """

    def __init__(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ):
        """
        Parameters
        ----------
        expected_returns : pd.Series
            Annualized expected returns per asset
        cov_matrix : pd.DataFrame
            Annualized covariance matrix
        risk_free_rate : float
            Risk-free rate (annualized)
        """
        self.mu = expected_returns
        self.cov = cov_matrix
        self.rf = risk_free_rate
        self.tickers = list(expected_returns.index)
        self.n = len(self.tickers)

        # Ensure alignment
        if list(self.mu.index) != list(self.cov.index) or list(self.mu.index) != list(
            self.cov.columns
        ):
            raise ValueError(
                "Return/covariance labels must match and be ordered identically"
            )

    def _finalize_weights(
        self,
        result,
        constraints: PortfolioConstraints,
        optimizer_name: str,
    ) -> pd.Series:
        """Validate optimizer output without silently altering feasibility."""
        if not result.success:
            raise RuntimeError(f"{optimizer_name} optimizer failed: {result.message}")

        weights = np.asarray(result.x, dtype=float)
        weights[np.abs(weights) < 1e-12] = 0.0
        if abs(weights.sum()) < 1e-12:
            raise RuntimeError(f"{optimizer_name} optimizer returned zero-sum weights")
        weights = weights / weights.sum()
        constraints.assert_valid_weights(weights)
        return pd.Series(weights, index=self.tickers)

    def _portfolio_return(self, w: np.ndarray) -> float:
        return w @ self.mu.values

    def _portfolio_volatility(self, w: np.ndarray) -> float:
        return np.sqrt(w @ self.cov.values @ w)

    def _portfolio_sharpe(self, w: np.ndarray) -> float:
        ret = self._portfolio_return(w)
        vol = self._portfolio_volatility(w)
        return (ret - self.rf) / vol if vol > 0 else 0

    # ------------------------------------------------------------------
    # Core Optimizations
    # ------------------------------------------------------------------
    def minimum_variance(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> Dict:
        """Find the portfolio with minimum variance."""
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        bounds = constraints.get_bounds(self.n)
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

        result = minimize(
            lambda w: self._portfolio_volatility(w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = self._finalize_weights(result, constraints, "Minimum variance")
        return self._build_result(weights, "Minimum Variance")

    def maximum_sharpe(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> Dict:
        """Find the tangency portfolio (maximum Sharpe ratio)."""
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        bounds = constraints.get_bounds(self.n)
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

        result = minimize(
            lambda w: -self._portfolio_sharpe(w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = self._finalize_weights(result, constraints, "Maximum Sharpe")
        return self._build_result(weights, "Maximum Sharpe")

    def target_return(
        self, target: float, constraints: Optional[PortfolioConstraints] = None
    ) -> Dict:
        """
        Find the minimum variance portfolio achieving a target return.

        Parameters
        ----------
        target : float
            Target annualized return
        """
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        bounds = constraints.get_bounds(self.n)
        cons = [
            {"type": "eq", "fun": lambda w: w.sum() - 1.0},
            {"type": "eq", "fun": lambda w: self._portfolio_return(w) - target},
        ]

        result = minimize(
            lambda w: self._portfolio_volatility(w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = self._finalize_weights(result, constraints, "Target return")
        return self._build_result(weights, f"Target Return ({target:.1%})")

    def maximum_return(
        self, constraints: Optional[PortfolioConstraints] = None
    ) -> Dict:
        """Find the portfolio maximizing expected return (corner portfolio)."""
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        bounds = constraints.get_bounds(self.n)
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

        result = minimize(
            lambda w: -self._portfolio_return(w),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = self._finalize_weights(result, constraints, "Maximum return")
        return self._build_result(weights, "Maximum Return")

    # ------------------------------------------------------------------
    # Efficient Frontier
    # ------------------------------------------------------------------
    def efficient_frontier(
        self, n_points: int = 50, constraints: Optional[PortfolioConstraints] = None
    ) -> pd.DataFrame:
        """
        Compute the efficient frontier — the set of optimal portfolios
        for each return level.
        """
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()

        # Get return range
        min_var = self.minimum_variance(constraints)
        max_ret = self.maximum_return(constraints)

        ret_range = np.linspace(min_var["return"], max_ret["return"], n_points)

        frontier = []
        for target in ret_range:
            try:
                port = self.target_return(target, constraints)
                frontier.append(
                    {
                        "Return": port["return"],
                        "Volatility": port["volatility"],
                        "Sharpe": port["sharpe"],
                    }
                )
            except Exception:
                continue

        df = pd.DataFrame(frontier)
        logger.info(f"Efficient frontier: {len(df)} points computed")
        return df

    # ------------------------------------------------------------------
    # Equal Weight Benchmark
    # ------------------------------------------------------------------
    def equal_weight(self) -> Dict:
        """1/N equal weight portfolio as a benchmark."""
        weights = pd.Series(np.ones(self.n) / self.n, index=self.tickers)
        return self._build_result(weights, "Equal Weight (1/N)")

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _build_result(self, weights: pd.Series, name: str) -> Dict:
        w = weights.values
        ret = self._portfolio_return(w)
        vol = self._portfolio_volatility(w)
        sharpe = (ret - self.rf) / vol if vol > 0 else 0

        return {
            "name": name,
            "weights": weights,
            "return": ret,
            "volatility": vol,
            "sharpe": sharpe,
            "n_assets": (weights.abs() > 1e-4).sum(),
            "max_weight": weights.max(),
            "min_weight": weights.min(),
            "concentration": (weights**2).sum(),  # HHI
        }
