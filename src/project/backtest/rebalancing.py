"""
Rebalancing Engine
====================
Multiple rebalancing strategies with transaction cost modeling.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


@dataclass
class TransactionCosts:
    """Transaction cost model."""

    proportional: float = 0.001  # 10 bps per trade
    fixed_per_trade: float = 0.0  # fixed cost per trade
    spread: float = 0.0005  # half-spread
    market_impact: float = 0.0  # price impact (for large trades)

    def cost(self, turnover: float, n_trades: int = 1) -> float:
        return (
            self.proportional + self.spread
        ) * turnover + self.fixed_per_trade * n_trades


class RebalancingEngine:
    """
    Rebalancing strategies for portfolio backtesting.

    Methods:
    1. Calendar-based (monthly, quarterly, annual)
    2. Threshold-based (rebalance when drift exceeds threshold)
    3. No rebalance (buy and hold)
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        target_weights: pd.Series,
        costs: Optional[TransactionCosts] = None,
    ):
        self.returns = returns.dropna()
        self.target = align_portfolio_weights(
            target_weights,
            returns.columns,
            context="Rebalancing target",
        )
        self.tickers = list(returns.columns)
        self.costs = costs or TransactionCosts()

    def _drift_weights(
        self, current_weights: np.ndarray, daily_returns: np.ndarray
    ) -> np.ndarray:
        """Compute weights after one day of market drift."""
        new_values = current_weights * (1 + daily_returns)
        total = new_values.sum()
        return new_values / total if total > 0 else current_weights

    def buy_and_hold(self) -> Dict:
        """No rebalancing — weights drift freely."""
        return self._run_backtest(rebal_dates=set())

    def _period_end_dates(self, frequency: str) -> set:
        """Return actual index dates for the last available observation per period."""
        groups = self.returns.groupby(pd.Grouper(freq=frequency))
        return set(groups.tail(1).index)

    def calendar_rebalance(self, frequency: str = "M") -> Dict:
        """
        Rebalance on calendar schedule.

        Parameters
        ----------
        frequency : str
            'M' monthly, 'Q' quarterly, 'A' annual, 'W' weekly
        """
        if frequency == "W":
            rebal_dates = self._period_end_dates("W-FRI")
        elif frequency == "M":
            rebal_dates = self._period_end_dates("ME")
        elif frequency == "Q":
            rebal_dates = self._period_end_dates("QE")
        elif frequency == "A":
            rebal_dates = self._period_end_dates("YE")
        else:
            rebal_dates = self._period_end_dates("ME")

        return self._run_backtest(
            rebal_dates=rebal_dates, label=f"Calendar ({frequency})"
        )

    def threshold_rebalance(self, threshold: float = 0.05) -> Dict:
        """
        Rebalance when any asset drifts more than threshold from target.

        Parameters
        ----------
        threshold : float
            Maximum allowable drift (e.g., 0.05 = 5%)
        """
        n = len(self.tickers)
        target = self.target.values
        current = target.copy()

        dates = self.returns.index
        port_values = [1.0]
        weights_history = [current.copy()]
        rebal_dates_actual = []
        total_cost = 0
        total_turnover = 0
        n_rebalances = 0

        for i in range(len(dates)):
            daily_ret = self.returns.iloc[i].values

            # Portfolio return using beginning-of-day weights
            port_ret = np.sum(current * daily_ret)

            # Drift weights to end-of-day
            current = self._drift_weights(current, daily_ret)

            # Check if drift exceeded threshold; if so, rebalance
            cost_today = 0
            max_drift = np.max(np.abs(current - target))
            if max_drift > threshold:
                turnover = np.sum(np.abs(current - target))
                cost_today = self.costs.cost(turnover)
                total_cost += cost_today
                total_turnover += turnover
                n_rebalances += 1
                rebal_dates_actual.append(dates[i])
                current = target.copy()

            # Deduct transaction costs from portfolio value
            port_values.append(port_values[-1] * (1 + port_ret) * (1 - cost_today))
            weights_history.append(current.copy())

        port_values = np.array(port_values[1:])
        port_returns = pd.Series(
            np.diff(np.concatenate([[1], port_values]))
            / np.concatenate([[1], port_values[:-1]]),
            index=dates,
        )

        return {
            "label": f"Threshold ({threshold:.0%})",
            "portfolio_returns": port_returns,
            "portfolio_values": pd.Series(port_values, index=dates),
            "weights_history": np.array(weights_history[1:]),
            "n_rebalances": n_rebalances,
            "total_turnover": total_turnover,
            "total_cost": total_cost,
            "avg_turnover_per_rebal": total_turnover / max(n_rebalances, 1),
            "rebalance_dates": rebal_dates_actual,
        }

    def _run_backtest(self, rebal_dates: set, label: str = "") -> Dict:
        """Core backtest loop."""
        n = len(self.tickers)
        target = self.target.values
        current = target.copy()

        dates = self.returns.index
        port_values = [1.0]
        weights_history = [current.copy()]
        total_cost = 0
        total_turnover = 0
        n_rebalances = 0

        for i in range(len(dates)):
            daily_ret = self.returns.iloc[i].values

            # Rebalance check
            cost_today = 0
            if dates[i] in rebal_dates:
                turnover = np.sum(np.abs(current - target))
                cost_today = self.costs.cost(turnover)
                total_cost += cost_today
                total_turnover += turnover
                n_rebalances += 1
                current = target.copy()

            port_ret = np.sum(current * daily_ret)
            port_values.append(port_values[-1] * (1 + port_ret) * (1 - cost_today))
            current = self._drift_weights(current, daily_ret)
            weights_history.append(current.copy())

        port_values = np.array(port_values[1:])
        port_returns = pd.Series(
            np.diff(np.concatenate([[1], port_values]))
            / np.concatenate([[1], port_values[:-1]]),
            index=dates,
        )

        return {
            "label": label or ("Buy & Hold" if len(rebal_dates) == 0 else "Calendar"),
            "portfolio_returns": port_returns,
            "portfolio_values": pd.Series(port_values, index=dates),
            "weights_history": np.array(weights_history[1:]),
            "n_rebalances": n_rebalances,
            "total_turnover": total_turnover,
            "total_cost": total_cost,
            "avg_turnover_per_rebal": total_turnover / max(n_rebalances, 1),
        }

    def compare_all(self, threshold: float = 0.05) -> Dict[str, Dict]:
        """Run all rebalancing methods and return results."""
        results = {
            "Buy & Hold": self.buy_and_hold(),
            "Monthly": self.calendar_rebalance("M"),
            "Quarterly": self.calendar_rebalance("Q"),
            "Annual": self.calendar_rebalance("A"),
            f"Threshold ({threshold:.0%})": self.threshold_rebalance(threshold),
        }
        return results
