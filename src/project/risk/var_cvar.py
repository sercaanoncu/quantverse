"""
Value at Risk & Conditional Value at Risk
===========================================
Multiple VaR/CVaR estimation approaches:
- Parametric (Gaussian)
- Historical Simulation
- Cornish-Fisher (adjusts for skewness/kurtosis)
- Monte Carlo Simulation
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging
from typing import Dict, Optional, Tuple

from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


class VaRCVaRCalculator:
    """
    Comprehensive VaR and CVaR (Expected Shortfall) calculator.

    VaR_α  = maximum loss at confidence level α
    CVaR_α = expected loss given loss exceeds VaR_α (always ≥ VaR)
    """

    def __init__(self, returns: pd.DataFrame, weights: Optional[pd.Series] = None):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Daily asset returns
        weights : pd.Series, optional
            Portfolio weights. If None, equal weight.
        """
        self.asset_returns = returns.dropna()
        if self.asset_returns.empty:
            raise ValueError("VaR/CVaR return history is empty")
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)

        if weights is not None:
            self.weights = self._aligned_weights(weights)
        else:
            self.weights = np.ones(self.n_assets) / self.n_assets

        self.portfolio_returns = self.asset_returns.values @ self.weights

    def set_weights(self, weights: pd.Series):
        """Update portfolio weights."""
        self.weights = self._aligned_weights(weights)
        self.portfolio_returns = self.asset_returns.values @ self.weights

    def _aligned_weights(self, weights: pd.Series) -> np.ndarray:
        return align_portfolio_weights(
            weights,
            self.tickers,
            context="VaR/CVaR portfolio",
        ).to_numpy(dtype=float)

    @staticmethod
    def _validate_alpha(alpha: float) -> None:
        if not 0.0 < float(alpha) < 1.0:
            raise ValueError("alpha must be strictly between 0 and 1")

    def historical_horizon(
        self,
        alpha: float = 0.05,
        horizon: int = 252,
    ) -> Dict[str, float]:
        """Empirical horizon VaR/CVaR from rolling compounded portfolio returns."""
        self._validate_alpha(alpha)
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        r = pd.Series(self.portfolio_returns, index=self.asset_returns.index)
        if len(r) < horizon:
            return {"VaR": np.nan, "CVaR": np.nan, "horizon": horizon, "n_obs": 0}

        horizon_returns = (
            r.rolling(horizon)
            .apply(
                lambda x: np.prod(1 + x) - 1,
                raw=True,
            )
            .dropna()
        )
        sorted_returns = np.sort(horizon_returns.values)
        cutoff = max(int(len(sorted_returns) * alpha), 1)
        var = -sorted_returns[cutoff - 1]
        cvar = -sorted_returns[:cutoff].mean()
        return {
            "VaR": var,
            "CVaR": cvar,
            "horizon": horizon,
            "n_obs": len(sorted_returns),
        }

    # ------------------------------------------------------------------
    # 1. Parametric (Gaussian) VaR/CVaR
    # ------------------------------------------------------------------
    def parametric(self, alpha: float = 0.05) -> Dict[str, float]:
        """
        Gaussian VaR/CVaR using mean and standard deviation.

        VaR  = μ - z_α · σ
        CVaR = μ - σ · φ(z_α) / α

        Underestimates tail risk for fat-tailed distributions.
        """
        self._validate_alpha(alpha)
        mu = self.portfolio_returns.mean()
        sigma = self.portfolio_returns.std()

        z = stats.norm.ppf(alpha)
        var = -(mu + z * sigma)
        cvar = -(mu - sigma * stats.norm.pdf(z) / alpha)

        return {
            "method": "Parametric (Gaussian)",
            "VaR": var,
            "CVaR": cvar,
            "alpha": alpha,
            "VaR_annual": np.nan,
            "CVaR_annual": np.nan,
            "annualization_status": "not_reported_no_model_free_sqrt_time_scaling",
            "loss_convention": "positive_loss_magnitude",
        }

    # ------------------------------------------------------------------
    # 2. Historical Simulation
    # ------------------------------------------------------------------
    def historical(self, alpha: float = 0.05) -> Dict[str, float]:
        """
        Non-parametric VaR/CVaR from actual return distribution.
        No distributional assumptions — uses the empirical quantile.
        """
        self._validate_alpha(alpha)
        sorted_returns = np.sort(self.portfolio_returns)
        n = len(sorted_returns)
        cutoff = int(n * alpha)
        if cutoff == 0:
            cutoff = 1

        var = -sorted_returns[cutoff - 1]
        cvar = -sorted_returns[:cutoff].mean()

        annual = self.historical_horizon(alpha=alpha, horizon=252)
        return {
            "method": "Historical",
            "VaR": var,
            "CVaR": cvar,
            "alpha": alpha,
            "VaR_annual": annual["VaR"],
            "CVaR_annual": annual["CVaR"],
            "n_tail_obs": cutoff,
            "n_annual_obs": annual["n_obs"],
            "annualization_status": "empirical_252_day_rolling_compounded_horizon",
            "loss_convention": "positive_loss_magnitude",
        }

    # ------------------------------------------------------------------
    # 3. Cornish-Fisher VaR/CVaR
    # ------------------------------------------------------------------
    def cornish_fisher(self, alpha: float = 0.05) -> Dict[str, float]:
        """
        Cornish-Fisher expansion adjusts the Gaussian quantile for
        skewness and kurtosis:

        z_CF = z + (z²-1)S/6 + (z³-3z)K/24 - (2z³-5z)S²/36

        Better than Gaussian for moderately non-normal distributions.
        """
        self._validate_alpha(alpha)
        mu = self.portfolio_returns.mean()
        sigma = self.portfolio_returns.std()
        s = stats.skew(self.portfolio_returns)
        k = stats.kurtosis(self.portfolio_returns)  # excess

        z = stats.norm.ppf(alpha)
        z_cf = (
            z
            + (z**2 - 1) * s / 6
            + (z**3 - 3 * z) * k / 24
            - (2 * z**3 - 5 * z) * s**2 / 36
        )

        var = -(mu + z_cf * sigma)
        # CVaR: use Gaussian CVaR scaled by CF adjustment ratio
        gaussian_cvar_z = stats.norm.pdf(z) / alpha
        cf_ratio = z_cf / z if abs(z) > 1e-10 else 1.0
        cvar = -(mu - sigma * gaussian_cvar_z * cf_ratio)

        return {
            "method": "Cornish-Fisher",
            "VaR": var,
            "CVaR": cvar,
            "alpha": alpha,
            "VaR_annual": np.nan,
            "CVaR_annual": np.nan,
            "skewness": s,
            "excess_kurtosis": k,
            "z_adjusted": z_cf,
            "annualization_status": "not_reported_no_model_free_sqrt_time_scaling",
            "loss_convention": "positive_loss_magnitude",
        }

    # ------------------------------------------------------------------
    # 4. Monte Carlo VaR/CVaR
    # ------------------------------------------------------------------
    def monte_carlo(
        self, alpha: float = 0.05, n_sims: int = 100_000, horizon: int = 1
    ) -> Dict[str, float]:
        """
        Monte Carlo simulation for VaR/CVaR.

        Parameters
        ----------
        n_sims : int
            Number of simulation paths
        horizon : int
            Holding period in trading days
        """
        self._validate_alpha(alpha)
        if n_sims <= 0 or horizon <= 0:
            raise ValueError("n_sims and horizon must be positive")
        mu = self.portfolio_returns.mean()
        sigma = self.portfolio_returns.std()

        # Simulate using local RNG to avoid global state mutation
        rng = np.random.default_rng(seed=42)
        simulated = rng.normal(mu * horizon, sigma * np.sqrt(horizon), n_sims)

        sorted_sims = np.sort(simulated)
        cutoff = int(n_sims * alpha)

        var = -sorted_sims[cutoff - 1]
        cvar = -sorted_sims[:cutoff].mean()

        return {
            "method": f"Monte Carlo ({n_sims:,} sims, {horizon}d)",
            "VaR": var,
            "CVaR": cvar,
            "alpha": alpha,
            "VaR_annual": np.nan,
            "CVaR_annual": np.nan,
            "annualization_status": "not_reported_no_model_free_sqrt_time_scaling",
            "loss_convention": "positive_loss_magnitude",
            "n_sims": n_sims,
            "horizon": horizon,
        }

    # ------------------------------------------------------------------
    # 5. Component VaR
    # ------------------------------------------------------------------
    def component_var(self, alpha: float = 0.05) -> pd.DataFrame:
        """
        Decompose portfolio VaR into asset-level contributions.

        Component VaR_i = w_i * β_i * VaR_portfolio
        where β_i = Cov(r_i, r_p) / Var(r_p)
        """
        port_ret = self.portfolio_returns
        hist = self.historical(alpha)
        port_var = hist["VaR"]

        betas = []
        for i, ticker in enumerate(self.tickers):
            cov_ip = np.cov(self.asset_returns.values[:, i], port_ret)[0, 1]
            var_p = np.var(port_ret)
            beta = cov_ip / var_p if var_p > 0 else 0
            betas.append(beta)

        betas = np.array(betas)
        component_var = self.weights * betas * port_var
        pct_contribution = (
            component_var / port_var * 100
            if abs(port_var) > 1e-12
            else np.zeros_like(component_var)
        )

        return pd.DataFrame(
            {
                "Weight": self.weights,
                "Beta": betas,
                "Component_VaR": component_var,
                "Pct_Contribution": pct_contribution,
            },
            index=self.tickers,
        ).sort_values("Pct_Contribution", ascending=False)

    # ------------------------------------------------------------------
    # 6. All Methods Comparison
    # ------------------------------------------------------------------
    def compare_all(self, alpha: float = 0.05) -> pd.DataFrame:
        """Run all VaR/CVaR methods and return comparison table."""
        methods = [
            self.parametric(alpha),
            self.historical(alpha),
            self.cornish_fisher(alpha),
            self.monte_carlo(alpha),
        ]

        rows = []
        for m in methods:
            rows.append(
                {
                    "Method": m["method"],
                    "VaR_Daily": m["VaR"],
                    "CVaR_Daily": m["CVaR"],
                    "VaR_Annual": m["VaR_annual"],
                    "CVaR_Annual": m["CVaR_annual"],
                    "Annualization_Status": m["annualization_status"],
                    "Loss_Convention": m["loss_convention"],
                }
            )

        return pd.DataFrame(rows).set_index("Method")

    # ------------------------------------------------------------------
    # 7. Rolling VaR
    # ------------------------------------------------------------------
    def rolling_var(self, window: int = 252, alpha: float = 0.05) -> pd.DataFrame:
        """Compute rolling historical VaR and CVaR."""
        n = len(self.portfolio_returns)
        dates = self.asset_returns.index[window:]
        var_ts, cvar_ts = [], []

        for i in range(window, n):
            sub = self.portfolio_returns[i - window : i]
            sorted_sub = np.sort(sub)
            cutoff = max(int(window * alpha), 1)
            var_ts.append(-sorted_sub[cutoff - 1])
            cvar_ts.append(-sorted_sub[:cutoff].mean())

        return pd.DataFrame(
            {
                "VaR": var_ts,
                "CVaR": cvar_ts,
            },
            index=dates,
        )
