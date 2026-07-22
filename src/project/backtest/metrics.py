"""
Performance Metrics
====================
Comprehensive suite of risk-adjusted return metrics
for portfolio evaluation and strategy comparison.
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging
from typing import Dict, Optional

from project.constants import DEFAULT_RISK_FREE_RATE, TRADING_DAYS_PER_YEAR

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Compute 30+ performance and risk metrics for a return series.
    """

    def __init__(
        self,
        returns: pd.Series,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        periods_per_year: int = TRADING_DAYS_PER_YEAR,
    ):
        self.returns = returns.dropna()
        self.rf = risk_free_rate
        self.rf_daily = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
        self.ppy = periods_per_year
        self.n = len(self.returns)

    # --- Return Metrics ---
    def total_return(self) -> float:
        return (1 + self.returns).prod() - 1

    def annualized_return(self) -> float:
        total = self.total_return()
        years = self.n / self.ppy
        return (1 + total) ** (1 / years) - 1 if years > 0 else 0

    def cagr(self) -> float:
        return self.annualized_return()

    # --- Volatility Metrics ---
    def annualized_volatility(self) -> float:
        return self.returns.std() * np.sqrt(self.ppy)

    def downside_volatility(self, threshold: float = 0.0) -> float:
        shortfall = np.minimum(self.returns - threshold, 0.0)
        return float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(self.ppy))

    # --- Risk-Adjusted Returns ---
    def sharpe_ratio(self) -> float:
        # Use arithmetic annualization: (mean_daily - rf_daily) / std_daily * sqrt(252)
        # This is the standard practitioner formula (Sharpe 1994)
        excess_daily = self.returns - self.rf_daily
        return (
            excess_daily.mean() / excess_daily.std() * np.sqrt(self.ppy)
            if excess_daily.std() > 0
            else 0
        )

    def sortino_ratio(self) -> float:
        excess_daily = self.returns - self.rf_daily
        shortfall = np.minimum(excess_daily, 0.0)
        down_vol = float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(self.ppy))
        return excess_daily.mean() * self.ppy / down_vol if down_vol > 0 else 0

    def calmar_ratio(self) -> float:
        ann_ret = self.annualized_return()
        mdd = self.max_drawdown()
        return ann_ret / abs(mdd) if mdd != 0 else np.inf

    def omega_ratio(self, threshold: float = 0.0) -> float:
        excess = self.returns - threshold
        gains = excess[excess > 0].sum()
        losses = -excess[excess < 0].sum()
        return gains / losses if losses > 0 else np.inf

    def information_ratio(self, benchmark: pd.Series) -> float:
        # Use common dates only (no fillna(0) which biases active returns)
        aligned = pd.DataFrame(
            {"portfolio": self.returns, "benchmark": benchmark}
        ).dropna()
        if len(aligned) < 2:
            return 0
        active = aligned["portfolio"] - aligned["benchmark"]
        te = active.std() * np.sqrt(self.ppy)
        return active.mean() * self.ppy / te if te > 0 else 0

    def treynor_ratio(self, benchmark: pd.Series) -> float:
        beta = self.beta(benchmark)
        annualized_excess_return = (self.returns - self.rf_daily).mean() * self.ppy
        return annualized_excess_return / beta if abs(beta) > 1e-6 else 0

    # --- Drawdown Metrics ---
    def max_drawdown(self) -> float:
        cum = (1 + self.returns).cumprod()
        dd = cum / cum.cummax().clip(lower=1.0) - 1
        return dd.min()

    def max_drawdown_duration(self) -> int:
        cum = (1 + self.returns).cumprod()
        peak = cum.cummax().clip(lower=1.0)
        in_dd = cum < peak
        if not in_dd.any():
            return 0
        groups = (~in_dd).cumsum()
        dd_lengths = in_dd.groupby(groups).sum()
        return int(dd_lengths.max()) if len(dd_lengths) > 0 else 0

    def average_drawdown(self) -> float:
        cum = (1 + self.returns).cumprod()
        dd = cum / cum.cummax().clip(lower=1.0) - 1
        return dd[dd < 0].mean() if (dd < 0).any() else 0

    def ulcer_index(self) -> float:
        cum = (1 + self.returns).cumprod()
        dd = cum / cum.cummax().clip(lower=1.0) - 1
        return np.sqrt((dd**2).mean())

    # --- Tail Risk ---
    def var_historical(self, alpha: float = 0.05) -> float:
        return -np.percentile(self.returns, alpha * 100)

    def cvar_historical(self, alpha: float = 0.05) -> float:
        cutoff = np.percentile(self.returns, alpha * 100)
        return -self.returns[self.returns <= cutoff].mean()

    def skewness(self) -> float:
        return float(stats.skew(self.returns))

    def kurtosis(self) -> float:
        return float(stats.kurtosis(self.returns))

    def tail_ratio(self) -> float:
        p95 = np.percentile(self.returns, 95)
        p5 = abs(np.percentile(self.returns, 5))
        return p95 / p5 if p5 > 0 else np.inf

    # --- Stability & Consistency ---
    def beta(self, benchmark: pd.Series) -> float:
        aligned = pd.DataFrame({"port": self.returns, "bench": benchmark}).dropna()
        if len(aligned) < 2:
            return 0
        cov = np.cov(aligned["port"], aligned["bench"])
        return cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 0

    def alpha_jensen(self, benchmark: pd.Series) -> float:
        aligned = pd.DataFrame(
            {"portfolio": self.returns, "benchmark": benchmark}
        ).dropna()
        if len(aligned) < 2:
            return 0
        covariance = np.cov(aligned["portfolio"], aligned["benchmark"])
        benchmark_variance = covariance[1, 1]
        if benchmark_variance <= 0:
            return 0
        beta = covariance[0, 1] / benchmark_variance
        alpha_daily = (aligned["portfolio"] - self.rf_daily) - beta * (
            aligned["benchmark"] - self.rf_daily
        )
        return float(alpha_daily.mean() * self.ppy)

    def win_rate(self) -> float:
        return (self.returns > 0).mean()

    def profit_loss_ratio(self) -> float:
        gains = self.returns[self.returns > 0].mean()
        losses = abs(self.returns[self.returns < 0].mean())
        return gains / losses if losses > 0 else np.inf

    def best_day(self) -> float:
        return self.returns.max()

    def worst_day(self) -> float:
        return self.returns.min()

    def best_month(self) -> float:
        monthly = self.returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        return monthly.max() if len(monthly) > 0 else 0

    def worst_month(self) -> float:
        monthly = self.returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        return monthly.min() if len(monthly) > 0 else 0

    def positive_months_pct(self) -> float:
        monthly = self.returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        return (monthly > 0).mean() if len(monthly) > 0 else 0

    # --- Summary ---
    def full_report(self, benchmark: Optional[pd.Series] = None) -> Dict:
        report = {
            "Total Return": self.total_return(),
            "CAGR": self.cagr(),
            "Annualized Volatility": self.annualized_volatility(),
            "Sharpe Ratio": self.sharpe_ratio(),
            "Sortino Ratio": self.sortino_ratio(),
            "Calmar Ratio": self.calmar_ratio(),
            "Omega Ratio": self.omega_ratio(),
            "Max Drawdown": self.max_drawdown(),
            "Max DD Duration (days)": self.max_drawdown_duration(),
            "Avg Drawdown": self.average_drawdown(),
            "Ulcer Index": self.ulcer_index(),
            "VaR (5%)": self.var_historical(0.05),
            "CVaR (5%)": self.cvar_historical(0.05),
            "Skewness": self.skewness(),
            "Excess Kurtosis": self.kurtosis(),
            "Tail Ratio": self.tail_ratio(),
            "Win Rate": self.win_rate(),
            "Profit/Loss Ratio": self.profit_loss_ratio(),
            "Best Day": self.best_day(),
            "Worst Day": self.worst_day(),
            "Best Month": self.best_month(),
            "Worst Month": self.worst_month(),
            "Positive Months %": self.positive_months_pct(),
            "Trading Days": self.n,
        }

        if benchmark is not None:
            report["Beta"] = self.beta(benchmark)
            report["Jensen Alpha"] = self.alpha_jensen(benchmark)
            report["Information Ratio"] = self.information_ratio(benchmark)
            report["Treynor Ratio"] = self.treynor_ratio(benchmark)

        return report
