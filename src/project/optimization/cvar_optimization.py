"""
Mean-CVaR Portfolio Optimization
==================================
Tail-risk aware optimization that minimizes Conditional Value at Risk
(Expected Shortfall) instead of variance.

Captures asymmetric and fat-tailed risk that Mean-Variance ignores.
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import logging
from typing import Dict, Optional

from project.constants import DEFAULT_RISK_FREE_RATE

from .constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


class CVaROptimizer:
    """
    Portfolio optimization using CVaR (Expected Shortfall) as risk measure.

    CVaR_α = E[R | R ≤ VaR_α]

    This is a more conservative risk measure than VaR because it
    captures the average loss in the worst α% of scenarios.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        expected_returns: Optional[pd.Series] = None,
        alpha: float = 0.05,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Historical daily returns
        expected_returns : pd.Series, optional
            Annualized expected returns. If None, use historical mean.
        alpha : float
            CVaR confidence level (0.05 = worst 5%)
        """
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n = len(self.tickers)
        self.alpha = alpha
        self.rf = risk_free_rate

        if expected_returns is not None:
            if list(expected_returns.index) != self.tickers:
                raise ValueError(
                    "Expected return labels must match returns columns in the same order"
                )
            self.mu = expected_returns
        else:
            self.mu = self.returns.mean() * 252

    def _finalize_weights(
        self,
        result,
        constraints: PortfolioConstraints,
        optimizer_name: str,
    ) -> pd.Series:
        """Validate optimizer output and fail loudly on infeasible solutions."""
        if not result.success:
            raise RuntimeError(f"{optimizer_name} optimizer failed: {result.message}")
        weights = np.asarray(result.x, dtype=float)
        weights[np.abs(weights) < 1e-12] = 0.0
        if abs(weights.sum()) < 1e-12:
            raise RuntimeError(f"{optimizer_name} optimizer returned zero-sum weights")
        weights = weights / weights.sum()
        constraints.assert_valid_weights(weights)
        return pd.Series(weights, index=self.tickers)

    def _portfolio_cvar(self, w: np.ndarray) -> float:
        """Compute historical CVaR for a given weight vector."""
        port_returns = self.returns.values @ w
        cutoff = int(len(port_returns) * self.alpha)
        if cutoff == 0:
            cutoff = 1
        sorted_returns = np.sort(port_returns)
        cvar = -sorted_returns[:cutoff].mean()
        return cvar

    def _portfolio_var(self, w: np.ndarray) -> float:
        """Compute historical VaR."""
        port_returns = self.returns.values @ w
        var = -np.percentile(port_returns, self.alpha * 100)
        return var

    def minimum_cvar(self, constraints: Optional[PortfolioConstraints] = None) -> Dict:
        """Find the portfolio that minimizes CVaR (maximum safety)."""
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        bounds = constraints.get_bounds(self.n)
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

        result = minimize(
            self._portfolio_cvar,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = self._finalize_weights(result, constraints, "Minimum CVaR")
        return self._build_result(weights, "Minimum CVaR")

    def maximum_return_cvar_constrained(
        self, max_cvar: float, constraints: Optional[PortfolioConstraints] = None
    ) -> Dict:
        """
        Maximize return subject to a CVaR constraint.

        Parameters
        ----------
        max_cvar : float
            Maximum allowable daily CVaR (e.g., 0.02 = 2%)
        """
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        bounds = constraints.get_bounds(self.n)
        cons = [
            {"type": "eq", "fun": lambda w: w.sum() - 1.0},
            {"type": "ineq", "fun": lambda w: max_cvar - self._portfolio_cvar(w)},
        ]

        result = minimize(
            lambda w: -(w @ self.mu.values),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        weights = self._finalize_weights(result, constraints, "Max return CVaR")
        return self._build_result(weights, f"Max Return (CVaR ≤ {max_cvar:.2%})")

    def mean_cvar_efficient_frontier(
        self, n_points: int = 30, constraints: Optional[PortfolioConstraints] = None
    ) -> pd.DataFrame:
        """
        Compute the Mean-CVaR efficient frontier.
        """
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only()

        # Get CVaR range
        min_cvar_port = self.minimum_cvar(constraints)
        min_cvar = min_cvar_port["cvar_daily"]

        # Equal weight CVaR as upper reference
        ew = np.ones(self.n) / self.n
        max_cvar = self._portfolio_cvar(ew) * 1.5

        cvar_range = np.linspace(min_cvar, max_cvar, n_points)
        frontier = []

        for target_cvar in cvar_range:
            try:
                port = self.maximum_return_cvar_constrained(target_cvar, constraints)
                frontier.append(
                    {
                        "Return": port["return"],
                        "CVaR_Daily": port["cvar_daily"],
                        "CVaR_Annual": port["cvar_annual"],
                        "VaR_Daily": port["var_daily"],
                        "Volatility": port["volatility"],
                    }
                )
            except Exception:
                continue

        return pd.DataFrame(frontier)

    def _build_result(self, weights: pd.Series, name: str) -> Dict:
        w = weights.values
        ret = w @ self.mu.values
        cov = self.returns.cov().values * 252
        vol = np.sqrt(w @ cov @ w)
        cvar = self._portfolio_cvar(w)
        var = self._portfolio_var(w)
        sharpe = (ret - self.rf) / vol if vol > 0 else 0

        return {
            "name": name,
            "weights": weights,
            "return": ret,
            "volatility": vol,
            "sharpe": sharpe,
            "cvar_daily": cvar,
            "var_daily": var,
            # One-day historical CVaR has no model-free sqrt-time annualization.
            "cvar_annual": np.nan,
            "n_assets": (weights.abs() > 1e-4).sum(),
            "max_weight": weights.max(),
            "min_weight": weights.min(),
            "concentration": (weights**2).sum(),
        }
