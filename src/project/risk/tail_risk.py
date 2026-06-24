"""
Tail Risk Analysis
===================
Extreme Value Theory (EVT), Generalized Pareto Distribution (GPD),
tail index estimation, and expected shortfall beyond VaR.
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TailRiskAnalyzer:
    """
    Advanced tail risk analysis using Extreme Value Theory.

    EVT is the mathematically rigorous way to model extreme returns
    rather than extrapolating from the body of the distribution.
    """

    def __init__(self, returns: pd.Series):
        """
        Parameters
        ----------
        returns : pd.Series
            Portfolio or asset returns
        """
        self.returns = returns.dropna()
        self.n = len(self.returns)

    # ------------------------------------------------------------------
    # 1. GPD Tail Fitting (Peaks Over Threshold)
    # ------------------------------------------------------------------
    def fit_gpd_tail(self, threshold_pct: float = 5.0, tail: str = "left") -> Dict:
        """
        Fit Generalized Pareto Distribution to tail exceedances.

        POT method: model exceedances over a threshold with GPD.

        Parameters
        ----------
        threshold_pct : float
            Threshold as percentile (e.g., 5 = bottom 5%)
        tail : str
            'left' for losses, 'right' for gains
        """
        if tail == "left":
            data = -self.returns.values  # flip for losses
            threshold = np.percentile(data, 100 - threshold_pct)
        else:
            data = self.returns.values
            threshold = np.percentile(data, 100 - threshold_pct)

        exceedances = data[data > threshold] - threshold
        n_exceed = len(exceedances)

        if n_exceed < 10:
            logger.warning(f"Only {n_exceed} exceedances — GPD fit may be unreliable")

        # Fit GPD
        shape, loc, scale = stats.genpareto.fit(exceedances, floc=0)

        # KS test
        ks_stat, ks_p = stats.kstest(exceedances, "genpareto", args=(shape, 0, scale))

        # EVT-based VaR and CVaR
        n_total = len(data)
        p_exceed = n_exceed / n_total

        def evt_var(alpha):
            """VaR using GPD tail estimate."""
            if abs(shape) < 1e-10:  # exponential case (shape ~= 0)
                return threshold - scale * np.log(alpha / p_exceed)
            return threshold + (scale / shape) * ((alpha / p_exceed) ** (-shape) - 1)

        def evt_cvar(alpha):
            """CVaR using GPD tail estimate."""
            if shape >= 1:
                return np.inf  # GPD has infinite mean when xi >= 1
            var = evt_var(alpha)
            return (var + scale - shape * threshold) / (1 - shape)

        var_1pct = evt_var(0.01)
        var_5pct = evt_var(0.05)
        cvar_1pct = evt_cvar(0.01)
        cvar_5pct = evt_cvar(0.05)

        return {
            "tail": tail,
            "threshold": threshold,
            "threshold_pct": threshold_pct,
            "n_exceedances": n_exceed,
            "shape_xi": shape,  # ξ: tail index. >0 = heavy tail, 0 = exponential, <0 = bounded
            "scale_sigma": scale,
            "KS_stat": ks_stat,
            "KS_pvalue": ks_p,
            "VaR_1pct": var_1pct,
            "VaR_5pct": var_5pct,
            "CVaR_1pct": cvar_1pct,
            "CVaR_5pct": cvar_5pct,
        }

    # ------------------------------------------------------------------
    # 2. Hill Estimator (Tail Index)
    # ------------------------------------------------------------------
    def hill_estimator(self, k_range: Optional[range] = None) -> pd.DataFrame:
        """
        Hill estimator for the tail index α.

        α = [1/k Σ(log X_{(i)} - log X_{(k+1)})]^{-1}

        Heavy tails: α < 4 (infinite 4th moment)
        Very heavy: α < 2 (infinite variance)

        Parameters
        ----------
        k_range : range
            Number of order statistics to use. Default: 10 to n/4
        """
        sorted_abs = np.sort(np.abs(self.returns.values))[::-1]

        if k_range is None:
            k_range = range(10, min(len(sorted_abs) // 4, 300))

        results = []
        for k in k_range:
            if k >= len(sorted_abs) - 1:
                break
            log_ratios = np.log(sorted_abs[:k]) - np.log(sorted_abs[k])
            gamma = log_ratios.mean()
            alpha = 1 / gamma if gamma > 0 else np.inf

            results.append({"k": k, "gamma": gamma, "alpha": alpha})

        return pd.DataFrame(results)

    # ------------------------------------------------------------------
    # 3. Tail Concentration
    # ------------------------------------------------------------------
    def tail_concentration(self, thresholds: Optional[list] = None) -> pd.DataFrame:
        """
        Measure what fraction of total losses comes from tail events.

        Answers: "How much of my risk is in extreme events?"
        """
        if thresholds is None:
            thresholds = [1, 2, 3, 5, 10]

        losses = -self.returns[self.returns < 0]
        total_loss = losses.sum()
        if total_loss == 0:
            return pd.DataFrame(
                columns=[
                    "Tail_%",
                    "Threshold",
                    "N_Events",
                    "Tail_Loss_Sum",
                    "Pct_of_Total_Loss",
                ]
            )

        rows = []
        for pct in thresholds:
            cutoff = np.percentile(losses, 100 - pct)
            tail_losses = losses[losses >= cutoff]
            n_events = len(tail_losses)
            tail_total = tail_losses.sum()
            concentration = tail_total / total_loss * 100

            rows.append(
                {
                    "Tail_%": pct,
                    "Threshold": cutoff,
                    "N_Events": n_events,
                    "Tail_Loss_Sum": tail_total,
                    "Pct_of_Total_Loss": concentration,
                }
            )

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # 4. Expected Shortfall Table
    # ------------------------------------------------------------------
    def _historical_horizon(self, alpha: float, horizon: int = 252) -> Dict[str, float]:
        """Empirical horizon VaR/CVaR from rolling compounded returns."""
        if self.n < horizon:
            return {"VaR": np.nan, "CVaR": np.nan, "n_obs": 0}

        horizon_returns = (
            self.returns.rolling(horizon)
            .apply(
                lambda x: np.prod(1 + x) - 1,
                raw=True,
            )
            .dropna()
        )
        sorted_ret = np.sort(horizon_returns.values)
        cutoff = max(int(len(sorted_ret) * alpha), 1)
        return {
            "VaR": -sorted_ret[cutoff - 1],
            "CVaR": -sorted_ret[:cutoff].mean(),
            "n_obs": len(sorted_ret),
        }

    def expected_shortfall_table(self, alphas: Optional[list] = None) -> pd.DataFrame:
        """
        Compute Expected Shortfall (CVaR) at multiple confidence levels.
        """
        if alphas is None:
            alphas = [0.01, 0.025, 0.05, 0.10]

        sorted_ret = np.sort(self.returns.values)
        rows = []
        for alpha in alphas:
            cutoff = max(int(self.n * alpha), 1)
            var = -sorted_ret[cutoff - 1]
            cvar = -sorted_ret[:cutoff].mean()
            worst = -sorted_ret[0]
            annual = self._historical_horizon(alpha=alpha, horizon=252)

            rows.append(
                {
                    "Alpha": alpha,
                    "Confidence": f"{(1-alpha)*100:.1f}%",
                    "VaR_Daily": var,
                    "CVaR_Daily": cvar,
                    "VaR_Annual": annual["VaR"],
                    "CVaR_Annual": annual["CVaR"],
                    "Worst_Day": worst,
                    "N_Tail_Obs": cutoff,
                    "N_Annual_Obs": annual["n_obs"],
                }
            )

        return pd.DataFrame(rows).set_index("Confidence")

    # ------------------------------------------------------------------
    # 5. Tail Dependence Summary
    # ------------------------------------------------------------------
    def tail_risk_summary(self) -> Dict:
        """Comprehensive tail risk summary."""
        r = self.returns.values
        gpd_left = self.fit_gpd_tail(threshold_pct=5.0, tail="left")
        es_table = self.expected_shortfall_table()

        return {
            "skewness": float(stats.skew(r)),
            "excess_kurtosis": float(stats.kurtosis(r)),
            "tail_index_xi": gpd_left["shape_xi"],
            "gpd_ks_pvalue": gpd_left["KS_pvalue"],
            "var_1pct_evt": gpd_left["VaR_1pct"],
            "cvar_1pct_evt": gpd_left["CVaR_1pct"],
            "var_5pct_historical": float(es_table.loc["95.0%", "VaR_Daily"]),
            "cvar_5pct_historical": float(es_table.loc["95.0%", "CVaR_Daily"]),
            "worst_daily_loss": float(-np.min(r)),
            "worst_weekly_loss": float(-pd.Series(r).rolling(5).sum().min()),
        }
