"""
Monte Carlo Portfolio Simulation
==================================
Forward-looking simulation of portfolio return paths using
multiple approaches to model the joint return distribution.

Methods:
1. Multivariate Normal (baseline)
2. Multivariate Student-t (fat tails)
3. Historical Bootstrap (block and iid)
4. GARCH-filtered Bootstrap (volatility clustering)
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.covariance import LedoitWolf
import logging
from typing import Dict, Optional, Tuple, List

from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Forward-looking Monte Carlo simulation engine for multi-asset portfolios.

    Generates thousands of possible 12-month return paths, then computes
    terminal wealth distribution, confidence intervals, and probability
    of various outcomes.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        weights: pd.Series,
        horizon_days: int = 252,
        n_sims: int = 10_000,
        seed: int = 42,
    ):
        """
        Parameters
        ----------
        returns : pd.DataFrame
            Historical daily returns (assets as columns)
        weights : pd.Series
            Portfolio weights
        horizon_days : int
            Simulation horizon in trading days (252 = 1 year)
        n_sims : int
            Number of simulation paths
        """
        self.returns = returns.dropna()
        if self.returns.empty:
            raise ValueError("Monte Carlo calibration returns are empty")
        if (self.returns <= -1.0).any().any():
            raise ValueError(
                "Monte Carlo log-return calibration requires simple returns above -100%"
            )
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)
        aligned_weights = align_portfolio_weights(
            weights,
            self.tickers,
            context="Monte Carlo portfolio",
        )
        self.weights = aligned_weights.to_numpy(dtype=float)
        self.horizon = horizon_days
        self.n_sims = n_sims
        self.seed = seed
        if self.horizon <= 0 or self.n_sims <= 0:
            raise ValueError("horizon_days and n_sims must be positive")

        # Parametric methods are calibrated in log-return space so generated
        # asset-level simple returns cannot fall below -100%.
        self.log_returns = np.log1p(self.returns)
        self.mu_log = self.log_returns.mean().to_numpy(dtype=float)

        lw = LedoitWolf().fit(self.log_returns.to_numpy(dtype=float))
        self.cov_log_lw = lw.covariance_

        # Portfolio historical returns for calibration
        self.port_hist = self.returns.values @ self.weights

    # ------------------------------------------------------------------
    # 1. Multivariate Normal Simulation
    # ------------------------------------------------------------------
    def simulate_normal(self) -> Dict:
        """
        Simulate using multivariate normal distribution.

        Pros: Simple, fast, well-understood
        Cons: Underestimates tail events, assumes symmetric returns
        """
        rng = np.random.default_rng(seed=self.seed)

        simulated_log_returns = rng.multivariate_normal(
            self.mu_log, self.cov_log_lw, size=(self.n_sims, self.horizon)
        )
        simulated_simple_returns = np.expm1(simulated_log_returns)

        port_daily = simulated_simple_returns @ self.weights

        # Cumulative wealth paths
        wealth_paths = np.cumprod(1 + port_daily, axis=1)

        return self._build_result(wealth_paths, port_daily, "Multivariate Normal")

    # ------------------------------------------------------------------
    # 2. Multivariate Student-t Simulation
    # ------------------------------------------------------------------
    def simulate_student_t(self, df: int = 5) -> Dict:
        """
        Simulate using multivariate Student-t distribution.

        Fat tails captured by degrees of freedom parameter.
        df=5 → much heavier tails than Normal
        df=30 → approximately Normal
        """
        rng = np.random.default_rng(seed=self.seed)

        # Generate multivariate t via: X = μ + Z * sqrt(df/chi2(df))
        if df <= 2:
            raise ValueError("Student-t degrees of freedom must exceed 2")
        eigenvalues, eigenvectors = np.linalg.eigh(self.cov_log_lw)
        covariance_root = eigenvectors @ np.diag(
            np.sqrt(np.clip(eigenvalues, 0.0, None))
        )

        port_daily = np.zeros((self.n_sims, self.horizon))

        for t in range(self.horizon):
            # Standard normal
            Z = rng.standard_normal((self.n_sims, self.n_assets))
            # Chi-squared scaling
            chi2 = rng.chisquare(df, self.n_sims)
            # Scale by df-2 so the simulated covariance matches the calibrated
            # covariance while retaining Student-t tails.
            scale = np.sqrt((df - 2) / chi2)[:, np.newaxis]
            simulated_log_returns = self.mu_log + (Z @ covariance_root.T) * scale
            asset_returns = np.expm1(simulated_log_returns)
            port_daily[:, t] = asset_returns @ self.weights

        wealth_paths = np.cumprod(1 + port_daily, axis=1)

        return self._build_result(
            wealth_paths, port_daily, f"Multivariate Student-t (df={df})"
        )

    # ------------------------------------------------------------------
    # 3. Historical Bootstrap (Block)
    # ------------------------------------------------------------------
    def simulate_bootstrap(self, block_size: int = 21) -> Dict:
        """
        Block bootstrap simulation — resample historical return blocks.

        Preserves short-term autocorrelation and cross-asset structure.

        Parameters
        ----------
        block_size : int
            Number of consecutive days per block (21 ≈ 1 month)
        """
        rng = np.random.default_rng(seed=self.seed)
        n_obs = len(self.returns)
        if block_size <= 0 or block_size > n_obs:
            raise ValueError(
                "block_size must be positive and no greater than calibration history"
            )
        n_blocks = self.horizon // block_size + 1

        port_daily = np.zeros((self.n_sims, self.horizon))

        for sim in range(self.n_sims):
            path = []
            for _ in range(n_blocks):
                start = rng.integers(0, n_obs - block_size + 1)
                block = self.returns.values[start : start + block_size]
                path.append(block @ self.weights)
            port_daily[sim, :] = np.concatenate(path)[: self.horizon]

        wealth_paths = np.cumprod(1 + port_daily, axis=1)

        return self._build_result(
            wealth_paths, port_daily, f"Block Bootstrap (block={block_size}d)"
        )

    # ------------------------------------------------------------------
    # 4. GARCH-Filtered Bootstrap
    # ------------------------------------------------------------------
    def simulate_garch_bootstrap(self) -> Dict:
        """
        Bootstrap standardized residuals from a GARCH(1,1) model,
        then reconstruct return paths with time-varying volatility.

        Captures volatility clustering in forward simulations.
        """
        rng = np.random.default_rng(seed=self.seed)

        # Fit GARCH(1,1) to portfolio returns using MLE via arch library
        port_hist = self.port_hist
        port_pct = port_hist * 100  # arch expects percentage returns

        from arch import arch_model

        garch = arch_model(
            port_pct, vol="Garch", p=1, q=1, mean="Constant", dist="normal"
        )
        garch_fit = garch.fit(disp="off")

        # Extract estimated parameters (in percentage-return scale)
        mu_p = garch_fit.params.get("mu", 0) / 100  # back to decimal
        omega = garch_fit.params["omega"] / (100**2)  # scale back to decimal variance
        alpha = garch_fit.params.get("alpha[1]", 0.08)
        beta = garch_fit.params.get("beta[1]", 0.90)

        logger.info(
            f"GARCH(1,1) estimated: omega={omega:.2e}, alpha={alpha:.4f}, "
            f"beta={beta:.4f}, persistence={alpha+beta:.4f}"
        )

        # Compute conditional variances using estimated parameters
        resid = port_hist - mu_p
        T = len(resid)
        sigma2 = np.zeros(T)
        sigma2[0] = np.var(resid)
        for t in range(1, T):
            sigma2[t] = omega + alpha * resid[t - 1] ** 2 + beta * sigma2[t - 1]

        # Standardized residuals
        std_resid = resid / np.sqrt(sigma2)

        # Forward simulation
        port_daily = np.zeros((self.n_sims, self.horizon))
        last_sigma2 = sigma2[-1]
        last_resid = resid[-1]

        for sim in range(self.n_sims):
            s2 = last_sigma2
            e = last_resid
            for t in range(self.horizon):
                s2 = omega + alpha * e**2 + beta * s2
                z = rng.choice(std_resid)
                e = z * np.sqrt(s2)
                port_daily[sim, t] = mu_p + e

        if (port_daily <= -1.0).any():
            raise ValueError(
                "GARCH simulation generated a return at or below -100%; "
                "the diagnostic is invalid under simple-return compounding"
            )
        wealth_paths = np.cumprod(1 + port_daily, axis=1)

        return self._build_result(wealth_paths, port_daily, "GARCH Bootstrap")

    # ------------------------------------------------------------------
    # 5. Run All Methods
    # ------------------------------------------------------------------
    def simulate_all(
        self, student_df: int = 5, block_size: int = 21
    ) -> Dict[str, Dict]:
        """Run all simulation methods."""
        results = {}
        for name, func in [
            ("Normal", self.simulate_normal),
            ("Student-t", lambda: self.simulate_student_t(df=student_df)),
            ("Bootstrap", lambda: self.simulate_bootstrap(block_size=block_size)),
            ("GARCH", self.simulate_garch_bootstrap),
        ]:
            try:
                results[name] = func()
                logger.info(
                    f"✓ {name}: median terminal = {results[name]['median_return']:.2%}"
                )
            except Exception as e:
                logger.warning(f"✗ {name} failed: {e}")
        return results

    # ------------------------------------------------------------------
    # Result Builder
    # ------------------------------------------------------------------
    def _build_result(
        self, wealth_paths: np.ndarray, port_daily: np.ndarray, method: str
    ) -> Dict:
        """Compute summary statistics from simulation paths."""
        if not np.isfinite(wealth_paths).all() or (wealth_paths <= 0).any():
            raise ValueError("Simulation produced non-finite or non-positive wealth")
        terminal = wealth_paths[:, -1]
        terminal_returns = terminal - 1  # simple return

        # Drawdowns per path
        running_max = np.maximum.accumulate(wealth_paths, axis=1)
        drawdowns = wealth_paths / running_max - 1
        max_drawdowns = drawdowns.min(axis=1)

        # Percentiles
        pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        percentiles = {f"p{p}": np.percentile(terminal_returns, p) for p in pcts}
        terminal_std = float(terminal_returns.std())
        distribution_is_degenerate = terminal_std <= 1e-12

        return {
            "method": method,
            "wealth_paths": wealth_paths,
            "terminal_wealth": terminal,
            "terminal_returns": terminal_returns,
            "daily_returns": port_daily,
            "max_drawdowns": max_drawdowns,
            # Summary stats
            "mean_return": terminal_returns.mean(),
            "median_return": np.median(terminal_returns),
            "std_return": terminal_std,
            "skewness": (
                np.nan
                if distribution_is_degenerate
                else float(stats.skew(terminal_returns))
            ),
            "kurtosis": (
                np.nan
                if distribution_is_degenerate
                else float(stats.kurtosis(terminal_returns))
            ),
            "distribution_is_degenerate": distribution_is_degenerate,
            # Percentiles
            "percentiles": percentiles,
            # Probabilities
            "prob_positive": (terminal_returns > 0).mean(),
            "prob_loss_10pct": (terminal_returns < -0.10).mean(),
            "prob_loss_20pct": (terminal_returns < -0.20).mean(),
            "prob_gain_20pct": (terminal_returns > 0.20).mean(),
            "prob_gain_50pct": (terminal_returns > 0.50).mean(),
            # Risk
            "var_5pct": -np.percentile(terminal_returns, 5),
            "cvar_5pct": -terminal_returns[
                terminal_returns <= np.percentile(terminal_returns, 5)
            ].mean(),
            "tail_risk_convention": "positive_terminal_loss_magnitude",
            "calibration_space": (
                "historical_simple_returns"
                if method.startswith("Block Bootstrap")
                else "log_returns_for_parametric_methods"
            ),
            "avg_max_drawdown": max_drawdowns.mean(),
            "worst_max_drawdown": max_drawdowns.min(),
            # Paths
            "n_sims": self.n_sims,
            "horizon": self.horizon,
        }
