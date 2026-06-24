"""
Portfolio Backtester
=====================
Walk-forward backtesting engine with periodic re-optimization.

Design Principles:
- Transaction costs deducted from returns on rebalance days (net-of-cost P&L)
- t+1 execution: train on data[:i], apply weights on day i (no look-ahead)
- Optimizer failure fallback: keeps previous weights if optimizer fails
- result.success validated on all scipy.optimize calls
"""

import pandas as pd
import numpy as np
from sklearn.covariance import LedoitWolf
from scipy.optimize import minimize
import logging
from typing import Dict, Optional, Callable

from project.constants import DEFAULT_RISK_FREE_RATE

from .metrics import PerformanceMetrics
from .rebalancing import TransactionCosts

logger = logging.getLogger(__name__)


class PortfolioBacktester:

    def __init__(
        self,
        returns: pd.DataFrame,
        asset_class_map: Dict[str, str],
        costs: Optional[TransactionCosts] = None,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        max_position_weight: float = 0.25,
    ):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)
        self.class_map = asset_class_map
        self.costs = costs or TransactionCosts()
        self.rf = risk_free_rate
        self.max_position_weight = max_position_weight
        if self.max_position_weight * self.n_assets < 1.0:
            raise ValueError("max_position_weight is infeasible for the asset count")

    def walk_forward(
        self,
        optimizer_fn: Callable,
        train_window: int = 504,
        rebal_frequency: int = 63,
        expanding: bool = False,
        label: str = "Strategy",
    ) -> Dict:
        """
        Walk-forward backtest with net-of-cost returns.

        Transaction costs are subtracted from portfolio return on rebalance days,
        so reported metrics reflect realistic, implementable performance.
        """
        dates = self.returns.index
        n = len(dates)
        if train_window >= n:
            raise ValueError(f"Train window ({train_window}) >= data length ({n})")

        current_weights = np.ones(self.n_assets) / self.n_assets
        port_returns_list = []
        weights_history = []
        rebal_dates = []
        total_turnover = 0.0
        total_cost = 0.0
        n_rebalances = 0
        days_since_rebal = rebal_frequency

        for i in range(train_window, n):
            date = dates[i]
            daily_ret = self.returns.iloc[i].values
            rebal_cost_today = 0.0

            if days_since_rebal >= rebal_frequency:
                # Train on data up to (but not including) today
                if expanding:
                    train = self.returns.iloc[:i]
                else:
                    train = self.returns.iloc[max(0, i - train_window) : i]

                try:
                    new_weights = optimizer_fn(train)
                    if isinstance(new_weights, pd.Series):
                        new_weights = new_weights.reindex(self.tickers).fillna(0).values

                    if (
                        np.any(np.isnan(new_weights))
                        or abs(new_weights.sum() - 1.0) > 0.05
                    ):
                        logger.warning(f"Invalid weights at {date}, keeping previous")
                    else:
                        turnover = np.sum(np.abs(new_weights - current_weights))
                        rebal_cost_today = self.costs.cost(turnover)
                        total_turnover += turnover
                        total_cost += rebal_cost_today
                        n_rebalances += 1
                        rebal_dates.append(date)
                        current_weights = new_weights
                except Exception as e:
                    logger.warning(f"Optimization failed at {date}: {e}")

                days_since_rebal = 0

            # Net-of-cost daily return
            port_ret = np.sum(current_weights * daily_ret) - rebal_cost_today
            port_returns_list.append(port_ret)
            weights_history.append(current_weights.copy())

            # Drift weights
            new_values = current_weights * (1 + daily_ret)
            total_val = new_values.sum()
            if total_val > 0:
                current_weights = new_values / total_val

            days_since_rebal += 1

        bt_dates = dates[train_window:]
        port_returns = pd.Series(port_returns_list, index=bt_dates, name=label)
        port_values = (1 + port_returns).cumprod()

        metrics = PerformanceMetrics(port_returns, risk_free_rate=self.rf)
        report = metrics.full_report()

        oos_years = max(1, (n - train_window) / 252)
        return {
            "label": label,
            "returns": port_returns,
            "values": port_values,
            "weights_history": np.array(weights_history),
            "rebalance_dates": rebal_dates,
            "n_rebalances": n_rebalances,
            "total_turnover": total_turnover,
            "total_cost": total_cost,
            "annualized_cost_drag_%": total_cost / oos_years * 100,
            "metrics": report,
        }

    # ------------------------------------------------------------------
    # Built-in Optimizers (all with result.success checks)
    # ------------------------------------------------------------------
    @staticmethod
    def equal_weight_optimizer(returns: pd.DataFrame) -> pd.Series:
        n = returns.shape[1]
        return pd.Series(np.ones(n) / n, index=returns.columns)

    @staticmethod
    def _project_to_capped_simplex(raw_weights: np.ndarray, cap: float) -> np.ndarray:
        """Project positive scores to a long-only, fully invested, capped portfolio."""
        n = len(raw_weights)
        if cap * n < 1.0:
            raise ValueError("Cap is infeasible for the asset count")

        weights = np.maximum(np.asarray(raw_weights, dtype=float), 0.0)
        if weights.sum() <= 1e-12:
            weights = np.ones(n) / n
        else:
            weights = weights / weights.sum()

        for _ in range(n + 1):
            capped = weights > cap
            if not capped.any():
                break
            excess = float((weights[capped] - cap).sum())
            weights[capped] = cap
            free = ~capped
            if not free.any():
                break
            free_sum = float(weights[free].sum())
            if free_sum <= 1e-12:
                weights[free] = excess / free.sum()
            else:
                weights[free] += excess * weights[free] / free_sum

        weights = np.minimum(weights, cap)
        residual = 1.0 - weights.sum()
        free = weights < cap - 1e-12
        if abs(residual) > 1e-10 and free.any():
            weights[free] += residual * weights[free] / weights[free].sum()
        return weights / weights.sum()

    @staticmethod
    def _valid_long_only_weights(
        weights: np.ndarray, cap: float, tol: float = 1e-4
    ) -> bool:
        weights = np.asarray(weights, dtype=float)
        return (
            weights.ndim == 1
            and np.all(np.isfinite(weights))
            and abs(weights.sum() - 1.0) <= tol
            and np.all(weights >= -tol)
            and np.all(weights <= cap + tol)
        )

    def min_variance_optimizer(self, returns: pd.DataFrame) -> pd.Series:
        lw = LedoitWolf().fit(returns.values)
        cov = lw.covariance_ * 252
        n = returns.shape[1]
        cap = self.max_position_weight

        result = minimize(
            lambda w: np.sqrt(w @ cov @ w),
            np.ones(n) / n,
            method="SLSQP",
            bounds=[(0, cap)] * n,
            constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
            options={"maxiter": 1000, "ftol": 1e-12},
        )
        if not result.success:
            logger.warning(f"Min Variance did not converge: {result.message}")
            vols = np.sqrt(np.diag(cov))
            inv_var = 1.0 / np.maximum(vols**2, 1e-8)
            weights = self._project_to_capped_simplex(inv_var, cap)
            return pd.Series(weights, index=returns.columns)
        return pd.Series(result.x, index=returns.columns)

    def max_sharpe_optimizer(self, returns: pd.DataFrame) -> pd.Series:
        mu = returns.mean().values * 252
        lw = LedoitWolf().fit(returns.values)
        cov = lw.covariance_ * 252
        n = returns.shape[1]
        rf = self.rf
        cap = self.max_position_weight

        def neg_sharpe(w):
            vol = np.sqrt(w @ cov @ w)
            return -(w @ mu - rf) / vol if vol > 1e-8 else 0

        vols = np.sqrt(np.diag(cov))
        inv_vol = self._project_to_capped_simplex(1.0 / np.maximum(vols, 1e-8), cap)
        corner = np.zeros(n)
        remaining = 1.0
        for idx in np.argsort(mu)[::-1]:
            allocation = min(cap, remaining)
            corner[idx] = allocation
            remaining -= allocation
            if remaining <= 1e-12:
                break

        starts = [
            np.ones(n) / n,
            inv_vol,
            corner,
        ]
        best_success = None
        best_candidate = None
        for start in starts:
            result = minimize(
                neg_sharpe,
                start,
                method="SLSQP",
                bounds=[(0, cap)] * n,
                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                options={"maxiter": 1000, "ftol": 1e-10},
            )
            if not self._valid_long_only_weights(result.x, cap):
                continue
            score = neg_sharpe(result.x)
            if result.success:
                if best_success is None or score < best_success[0]:
                    best_success = (score, result.x)
            elif best_candidate is None or score < best_candidate[0]:
                best_candidate = (score, result.x)

        if best_success is not None:
            return pd.Series(best_success[1], index=returns.columns)
        if best_candidate is not None:
            logger.info("Max Sharpe used best feasible candidate after SLSQP warning")
            return pd.Series(best_candidate[1], index=returns.columns)

        logger.warning(
            "Max Sharpe did not produce feasible weights; fallback to inverse volatility"
        )
        return pd.Series(inv_vol, index=returns.columns)

    def inverse_vol_optimizer(self, returns: pd.DataFrame) -> pd.Series:
        vols = returns.std().values * np.sqrt(252)
        inv_vol = 1.0 / np.maximum(vols, 1e-8)
        weights = self._project_to_capped_simplex(inv_vol, self.max_position_weight)
        return pd.Series(weights, index=returns.columns)

    @staticmethod
    def hrp_optimizer(returns: pd.DataFrame) -> pd.Series:
        """HRP optimizer using the package import path."""
        try:
            from project.optimization.hierarchical import HRPOptimizer

            hrp = HRPOptimizer(returns)
            result = hrp.optimize(method="single")
            return result["weights"]
        except (ImportError, Exception) as e:
            logger.warning(f"HRP unavailable ({e}), fallback to inverse vol")
            vols = returns.std().values * np.sqrt(252)
            inv_vol = 1.0 / np.maximum(vols, 1e-8)
            return pd.Series(inv_vol / inv_vol.sum(), index=returns.columns)

    def run_all_strategies(
        self, train_window: int = 504, rebal_frequency: int = 63
    ) -> Dict[str, Dict]:
        strategies = {
            "Equal Weight": self.equal_weight_optimizer,
            "Min Variance": self.min_variance_optimizer,
            "Max Sharpe": self.max_sharpe_optimizer,
            "Inverse Vol": self.inverse_vol_optimizer,
            "HRP": self.hrp_optimizer,
        }
        results = {}
        for name, optimizer in strategies.items():
            try:
                logger.info(f"Running walk-forward: {name}")
                results[name] = self.walk_forward(
                    optimizer_fn=optimizer,
                    train_window=train_window,
                    rebal_frequency=rebal_frequency,
                    label=name,
                )
                logger.info(
                    f"  ✓ {name}: Sharpe={results[name]['metrics']['Sharpe Ratio']:.2f}"
                )
            except Exception as e:
                logger.warning(f"  ✗ {name} failed: {e}")
        return results
