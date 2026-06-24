"""
Portfolio Constraints
======================
Shared constraint definitions for all optimization methods.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class PortfolioConstraints:
    """
    Unified constraint specification for portfolio optimization.

    Parameters
    ----------
    long_only : bool
        If True, all weights >= 0
    max_weight : float
        Maximum weight per asset (e.g., 0.20 = 20%)
    min_weight : float
        Minimum weight per asset (0 for long-only, can be negative for short)
    max_sector_weight : dict
        Maximum total weight per asset class {class_name: max_weight}
    max_total_short : float
        Maximum total short exposure (e.g., 0.30 = 30%)
    max_leverage : float
        Maximum gross exposure (sum of |w|), e.g., 1.0 = no leverage
    target_return : float, optional
        Target annualized return for constrained optimization
    max_volatility : float, optional
        Maximum annualized volatility
    max_drawdown : float, optional
        Maximum allowable drawdown (for backtesting constraints)
    """

    long_only: bool = True
    max_weight: float = 0.25
    min_weight: float = 0.0
    max_sector_weight: Dict[str, float] = field(default_factory=dict)
    max_total_short: float = 0.0
    max_leverage: float = 1.0
    target_return: Optional[float] = None
    max_volatility: Optional[float] = None
    max_drawdown: Optional[float] = None

    def get_bounds(self, n_assets: int) -> List[Tuple[float, float]]:
        """Get scipy-compatible bounds for each asset."""
        lb = max(self.min_weight, 0.0) if self.long_only else self.min_weight
        return [(lb, self.max_weight)] * n_assets

    def check_feasible(self, n_assets: int) -> None:
        """Raise if sum-to-one cannot be satisfied under per-asset bounds."""
        bounds = self.get_bounds(n_assets)
        min_sum = sum(lb for lb, _ in bounds)
        max_sum = sum(ub for _, ub in bounds)
        if min_sum > 1.0 + 1e-12 or max_sum < 1.0 - 1e-12:
            raise ValueError(
                "Infeasible portfolio constraints: "
                f"sum lower bound={min_sum:.6f}, sum upper bound={max_sum:.6f}"
            )

    def validate_weights(
        self, weights: np.ndarray, tol: float = 1e-4
    ) -> Dict[str, bool]:
        """Validate a weight vector against constraints."""
        checks = {
            "sum_to_one": abs(weights.sum() - 1.0) < tol,
            "max_weight": np.all(weights <= self.max_weight + tol),
        }
        if self.long_only:
            checks["long_only"] = np.all(weights >= -tol)
        checks["min_weight"] = np.all(
            weights >= self.get_bounds(len(weights))[0][0] - tol
        )
        if self.max_leverage < np.inf:
            checks["leverage"] = np.sum(np.abs(weights)) <= self.max_leverage + tol
        return checks

    def assert_valid_weights(self, weights: np.ndarray, tol: float = 1e-4) -> None:
        """Raise if a solved portfolio violates configured constraints."""
        checks = self.validate_weights(weights, tol=tol)
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            raise ValueError(f"Portfolio weights violate constraints: {failed}")

    @staticmethod
    def default_long_only(max_weight: float = 0.25) -> "PortfolioConstraints":
        return PortfolioConstraints(
            long_only=True, max_weight=max_weight, min_weight=0.0
        )

    @staticmethod
    def unconstrained() -> "PortfolioConstraints":
        return PortfolioConstraints(
            long_only=False, max_weight=1.0, min_weight=-1.0, max_leverage=3.0
        )
