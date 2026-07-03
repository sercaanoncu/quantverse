"""
Risk Parity / Equal Risk Contribution (ERC)
=============================================
Each asset contributes equally to total portfolio risk.

Unlike equal weight, this accounts for volatility differences
so low-vol assets get more weight.
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import logging
from typing import Dict, Optional

from .constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


class RiskParityOptimizer:
    """
    Risk Parity portfolio construction.

    Objective: find w such that RC_i = RC_j for all i, j
    where RC_i = w_i * (Σw)_i / (w'Σw) is the risk contribution of asset i.
    """

    def __init__(
        self, cov_matrix: pd.DataFrame, expected_returns: Optional[pd.Series] = None
    ):
        if list(cov_matrix.index) != list(cov_matrix.columns):
            raise ValueError(
                "Covariance matrix index/columns must match and be ordered identically"
            )
        if expected_returns is not None and list(expected_returns.index) != list(
            cov_matrix.index
        ):
            raise ValueError(
                "Expected return labels must match covariance labels in the same order"
            )
        self.cov = cov_matrix
        self.tickers = list(cov_matrix.index)
        self.n = len(self.tickers)
        self.mu = expected_returns

    def _risk_contributions(self, w: np.ndarray) -> np.ndarray:
        """Compute marginal and total risk contributions."""
        Sigma = self.cov.values
        port_vol = np.sqrt(w @ Sigma @ w)
        if not np.isfinite(port_vol) or port_vol <= 1e-12:
            return np.zeros_like(w)
        marginal = Sigma @ w / port_vol
        rc = w * marginal  # risk contribution
        return rc

    def _risk_parity_objective(
        self, w: np.ndarray, target_rc: Optional[np.ndarray] = None
    ) -> float:
        """
        Objective: minimize sum of squared differences between
        actual and target risk contributions.
        """
        rc = self._risk_contributions(w)
        if target_rc is None:
            target_rc = np.ones(self.n) / self.n  # equal risk contribution
        port_vol = np.sqrt(w @ self.cov.values @ w)
        if not np.isfinite(port_vol) or port_vol <= 1e-12:
            rc_pct = np.zeros_like(rc)
        else:
            rc_pct = rc / port_vol  # as fraction of total risk
        return np.sum((rc_pct - target_rc) ** 2)

    def optimize(
        self,
        target_risk_budget: Optional[np.ndarray] = None,
        constraints: Optional[PortfolioConstraints] = None,
    ) -> Dict:
        """
        Find risk parity weights.

        Parameters
        ----------
        target_risk_budget : np.ndarray, optional
            Target risk contribution per asset (sums to 1).
            None = equal risk contribution.
        """
        if constraints is None:
            constraints = PortfolioConstraints.default_long_only(max_weight=1.0)
        constraints.check_feasible(self.n)

        w0 = np.ones(self.n) / self.n
        # Minimum weight > 0 for risk parity (all assets must contribute)
        min_w = (
            constraints.min_weight if constraints and constraints.min_weight else 0.001
        )
        max_w = (
            constraints.max_weight if constraints and constraints.max_weight else 1.0
        )
        bounds = [(max(min_w, 0.001), max_w)] * self.n
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

        result = minimize(
            self._risk_parity_objective,
            w0,
            args=(target_risk_budget,),
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 1000, "ftol": 1e-12},
        )

        if not result.success:
            raise RuntimeError(f"Risk parity optimizer failed: {result.message}")

        weights = pd.Series(result.x, index=self.tickers)
        weights = weights / weights.sum()  # ensure normalization
        constraints.assert_valid_weights(weights.values)

        # Compute risk contributions
        rc = self._risk_contributions(weights.values)
        port_vol = np.sqrt(weights.values @ self.cov.values @ weights.values)
        if not np.isfinite(port_vol) or port_vol <= 1e-12:
            rc_pct = np.zeros_like(rc)
        else:
            rc_pct = rc / port_vol

        # Portfolio metrics
        w = weights.values
        ret = w @ (self.mu.values if self.mu is not None else np.zeros(self.n))
        vol = port_vol
        sharpe = (ret / vol) if np.isfinite(vol) and vol > 0 else 0

        logger.info(
            f"Risk Parity: vol={vol*100:.1f}%, "
            f"RC range=[{rc_pct.min():.3f}, {rc_pct.max():.3f}]"
        )

        return {
            "name": "Risk Parity (ERC)",
            "weights": weights,
            "return": ret,
            "volatility": vol,
            "sharpe": sharpe,
            "n_assets": (weights > 1e-4).sum(),
            "max_weight": weights.max(),
            "min_weight": weights.min(),
            "concentration": (weights**2).sum(),
            "risk_contributions": pd.Series(rc_pct, index=self.tickers),
            "convergence": result.success,
        }

    def inverse_volatility(self) -> Dict:
        """
        Simple inverse volatility weighting.
        Not true risk parity (ignores correlations) but fast approximation.
        """
        vols = np.sqrt(np.diag(self.cov.values))
        inv_vol = 1.0 / vols
        weights = pd.Series(inv_vol / inv_vol.sum(), index=self.tickers)

        w = weights.values
        ret = w @ (self.mu.values if self.mu is not None else np.zeros(self.n))
        vol = np.sqrt(w @ self.cov.values @ w)

        return {
            "name": "Inverse Volatility",
            "weights": weights,
            "return": ret,
            "volatility": vol,
            "sharpe": (ret / vol) if vol > 0 else 0,
            "n_assets": self.n,
            "max_weight": weights.max(),
            "min_weight": weights.min(),
            "concentration": (weights**2).sum(),
        }
