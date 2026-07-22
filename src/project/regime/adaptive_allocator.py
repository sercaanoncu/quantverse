"""
Adaptive Portfolio Allocation
================================
Dynamically adjust portfolio weights based on detected market regime.

The core idea: different regimes call for different portfolios.
- Bull/Low Vol → more risk, more equity, more crypto
- Bear/High Vol → defensive, more bonds, more gold, less leverage
- Sideways → balanced, risk parity style
"""

import pandas as pd
import numpy as np
from sklearn.covariance import LedoitWolf
from scipy.optimize import minimize
import logging
from typing import Dict, Optional, Callable

from project.constants import DEFAULT_RISK_FREE_RATE

logger = logging.getLogger(__name__)


class AdaptiveAllocator:
    """
    Regime-conditional portfolio construction.

    Assigns a different optimization strategy or target allocation
    to each market regime, then switches dynamically.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        asset_class_map: Dict[str, str],
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)
        self.class_map = asset_class_map
        self.rf = risk_free_rate

    # ------------------------------------------------------------------
    # 1. Regime-Specific Target Allocations (Rule-Based)
    # ------------------------------------------------------------------
    def rule_based_targets(self) -> Dict[str, Dict[str, float]]:
        """
        Predefined asset class target allocations per regime.

        Returns dict of {regime: {asset_class: weight}}
        """
        return {
            "Low Vol": {
                "us_equity_sectors": 0.40,
                "international_equity": 0.15,
                "crypto": 0.10,
                "commodities": 0.10,
                "fixed_income": 0.15,
                "reits": 0.10,
            },
            "Medium Vol": {
                "us_equity_sectors": 0.30,
                "international_equity": 0.10,
                "crypto": 0.05,
                "commodities": 0.15,
                "fixed_income": 0.25,
                "reits": 0.15,
            },
            "High Vol": {
                "us_equity_sectors": 0.15,
                "international_equity": 0.05,
                "crypto": 0.02,
                "commodities": 0.20,
                "fixed_income": 0.45,
                "reits": 0.13,
            },
        }

    def _ac_targets_to_asset_weights(self, ac_targets: Dict[str, float]) -> pd.Series:
        """Convert asset class targets to individual asset weights (equal within class)."""
        weights = pd.Series(0.0, index=self.tickers)
        for ac, target_w in ac_targets.items():
            tickers_in_class = [
                t for t, c in self.class_map.items() if c == ac and t in self.tickers
            ]
            if tickers_in_class:
                per_asset = target_w / len(tickers_in_class)
                for t in tickers_in_class:
                    weights[t] = per_asset
        # Normalize
        weights = weights / weights.sum()
        return weights

    # ------------------------------------------------------------------
    # 2. Regime-Conditional Optimization
    # ------------------------------------------------------------------
    def optimize_for_regime(
        self, regime_returns: pd.DataFrame, strategy: str = "min_variance"
    ) -> pd.Series:
        """
        Optimize portfolio on returns from a specific regime.

        Parameters
        ----------
        regime_returns : pd.DataFrame
            Historical returns observed during this regime
        strategy : str
            'min_variance', 'max_sharpe', 'risk_parity', 'inverse_vol'
        """
        if len(regime_returns) < 30:
            return pd.Series(1.0 / self.n_assets, index=self.tickers)

        lw = LedoitWolf().fit(regime_returns.values)
        cov = lw.covariance_ * 252
        mu = regime_returns.mean().values * 252
        n = self.n_assets

        if strategy == "min_variance":
            result = minimize(
                lambda w: np.sqrt(w @ cov @ w),
                np.ones(n) / n,
                method="SLSQP",
                bounds=[(0, 0.20)] * n,
                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
            )
            if not result.success:
                logger.warning(
                    f"Regime min-variance failed: {result.message}; using inverse vol"
                )
                vols = np.sqrt(np.diag(cov))
                inv_vol = 1.0 / np.maximum(vols, 1e-8)
                return pd.Series(inv_vol / inv_vol.sum(), index=self.tickers)
            return pd.Series(result.x, index=self.tickers)

        elif strategy == "max_sharpe":

            def neg_sharpe(w):
                r = w @ mu
                v = np.sqrt(w @ cov @ w)
                return -(r - self.rf) / v if v > 0 else 0

            result = minimize(
                neg_sharpe,
                np.ones(n) / n,
                method="SLSQP",
                bounds=[(0, 0.20)] * n,
                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
            )
            if not result.success:
                logger.warning(
                    f"Regime max-sharpe failed: {result.message}; using equal weight"
                )
                return pd.Series(1.0 / n, index=self.tickers)
            return pd.Series(result.x, index=self.tickers)

        elif strategy == "inverse_vol":
            vols = np.sqrt(np.diag(cov))
            inv_vol = 1.0 / np.maximum(vols, 1e-8)
            w = inv_vol / inv_vol.sum()
            return pd.Series(w, index=self.tickers)

        else:
            return pd.Series(1.0 / n, index=self.tickers)

    # ------------------------------------------------------------------
    # 3. Walk-Forward Adaptive Backtest
    # ------------------------------------------------------------------
    def adaptive_backtest(
        self,
        regime_series: pd.Series,
        mode: str = "rule_based",
        train_window: int = 252,
        rebal_frequency: int = 21,
        transition_smooth: float = 0.0,
    ) -> Dict:
        """
        Walk-forward backtest with regime-adaptive allocation.

        Parameters
        ----------
        regime_series : pd.Series
            Regime labels aligned with return dates
        mode : str
            'rule_based' = predefined asset class targets
            'optimized' = re-optimize per regime on historical data
        train_window : int
            Lookback for optimization (used in 'optimized' mode)
        rebal_frequency : int
            Check/rebalance every N days
        transition_smooth : float
            Blend factor for regime transitions (0 = instant switch, 0.5 = 50% blend)
        """
        aligned_dates = self.returns.index.intersection(regime_series.index)
        returns_aligned = self.returns.loc[aligned_dates]
        regimes_aligned = regime_series.loc[aligned_dates]

        # Pre-compute rule-based targets
        if mode == "rule_based":
            regime_weights = {}
            targets = self.rule_based_targets()
            for regime_name, ac_target in targets.items():
                regime_weights[regime_name] = self._ac_targets_to_asset_weights(
                    ac_target
                )

        # Walk-forward
        current_weights = np.ones(self.n_assets) / self.n_assets
        prev_regime = None
        port_returns = []
        weight_history = []
        regime_history = []
        rebal_count = 0
        days_since_rebal = rebal_frequency

        for i in range(len(aligned_dates)):
            date = aligned_dates[i]
            daily_ret = returns_aligned.iloc[i].values
            # t+1 execution: use PREVIOUS day's regime (avoid look-ahead)
            current_regime = (
                regimes_aligned.iloc[i - 1] if i > 0 else regimes_aligned.iloc[0]
            )

            # Rebalance check
            regime_changed = current_regime != prev_regime
            periodic = days_since_rebal >= rebal_frequency

            if regime_changed or periodic:
                if mode == "rule_based":
                    # Match regime labels flexibly (handles HMM's "Low Vol (Bull)" etc)
                    matched = None
                    for rname in regime_weights:
                        if rname in current_regime or current_regime in rname:
                            matched = rname
                            break
                    if matched:
                        new_weights = regime_weights[matched].values
                    elif current_regime in regime_weights:
                        new_weights = regime_weights[current_regime].values
                    else:
                        new_weights = np.ones(self.n_assets) / self.n_assets
                elif mode == "optimized":
                    start = max(0, i - train_window)
                    train_data = returns_aligned.iloc[start:i]
                    regime_mask = regimes_aligned.iloc[start:i] == current_regime
                    regime_data = train_data[regime_mask]
                    strategy = (
                        "min_variance"
                        if "High Vol" in str(current_regime)
                        else "max_sharpe"
                    )
                    new_weights = self.optimize_for_regime(regime_data, strategy).values
                else:
                    new_weights = np.ones(self.n_assets) / self.n_assets

                # Smooth transition
                if transition_smooth > 0 and prev_regime is not None:
                    current_weights = (
                        1 - transition_smooth
                    ) * new_weights + transition_smooth * current_weights
                else:
                    current_weights = new_weights

                rebal_count += 1
                days_since_rebal = 0
                prev_regime = current_regime

            # Daily return
            port_ret = np.sum(current_weights * daily_ret)
            port_returns.append(port_ret)
            weight_history.append(current_weights.copy())
            regime_history.append(current_regime)

            # Drift
            new_vals = current_weights * (1 + daily_ret)
            total = new_vals.sum()
            if total > 0:
                current_weights = new_vals / total

            days_since_rebal += 1

        port_returns = pd.Series(port_returns, index=aligned_dates, name="Adaptive")
        port_values = (1 + port_returns).cumprod()

        # Metrics
        ann_ret = port_returns.mean() * 252
        ann_vol = port_returns.std() * np.sqrt(252)
        sharpe = (ann_ret - self.rf) / ann_vol if ann_vol > 0 else 0
        cum = port_values.values
        running_peak = np.maximum(np.maximum.accumulate(cum), 1.0)
        max_dd = (cum / running_peak - 1).min()

        return {
            "label": f"Adaptive ({mode})",
            "returns": port_returns,
            "values": port_values,
            "weights_history": np.array(weight_history),
            "regime_history": pd.Series(regime_history, index=aligned_dates),
            "n_rebalances": rebal_count,
            "metrics": {
                "CAGR": ann_ret,
                "Volatility": ann_vol,
                "Sharpe": sharpe,
                "Max_Drawdown": max_dd,
                "Calmar": ann_ret / abs(max_dd) if max_dd != 0 else np.inf,
            },
        }
