"""
Covariance Estimator Evaluation & Comparison
==============================================
Tools to compare estimator quality via eigenvalue analysis,
minimum variance portfolio, out-of-sample stability, and
condition number diagnostics.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class CovarianceEvaluator:
    """Evaluate and compare covariance estimation methods."""

    def __init__(self, returns: pd.DataFrame):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.n_assets = len(self.tickers)

    # ------------------------------------------------------------------
    # 1. Eigenvalue Analysis
    # ------------------------------------------------------------------
    def eigenvalue_analysis(self, cov_results: Dict[str, Dict]) -> pd.DataFrame:
        """
        Compare eigenvalue spectra across estimation methods.

        Returns DataFrame with condition number, min/max eigenvalues,
        number of near-zero eigenvalues, and effective rank.
        """
        rows = []
        for name, result in cov_results.items():
            cov = result["covariance"].values
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)[::-1]

            cond = eigenvalues[0] / max(eigenvalues[-1], 1e-15)
            n_near_zero = np.sum(eigenvalues < 1e-10)

            # Effective rank (Shannon entropy of normalized eigenvalues)
            eig_norm = eigenvalues / eigenvalues.sum()
            eig_norm = eig_norm[eig_norm > 1e-15]
            eff_rank = np.exp(-np.sum(eig_norm * np.log(eig_norm)))

            rows.append(
                {
                    "Method": name,
                    "Max_Eigenvalue": eigenvalues[0],
                    "Min_Eigenvalue": eigenvalues[-1],
                    "Condition_Number": cond,
                    "Near_Zero_Eigenvalues": n_near_zero,
                    "Effective_Rank": eff_rank,
                    "Trace": eigenvalues.sum(),
                    "Determinant_Log": np.sum(np.log(np.maximum(eigenvalues, 1e-15))),
                }
            )

        df = pd.DataFrame(rows).set_index("Method")
        return df

    # ------------------------------------------------------------------
    # 2. Minimum Variance Portfolio Comparison
    # ------------------------------------------------------------------
    def min_variance_portfolios(
        self, cov_results: Dict[str, Dict]
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Compute the minimum variance portfolio (MVP) weights under each estimator.
        MVP is the portfolio that minimizes σ²_p = w'Σw subject to Σw = 1.

        Analytical solution: w* = Σ⁻¹·1 / (1'·Σ⁻¹·1)

        Comparing MVPs reveals how sensitive optimization is to the covariance estimator.
        """
        portfolios = {}
        for name, result in cov_results.items():
            cov = result["covariance"].values
            try:
                ones = np.ones(self.n_assets)
                inv_cov_ones = np.linalg.solve(cov, ones)
                weights = inv_cov_ones / (ones @ inv_cov_ones)

                # Portfolio metrics
                port_var = weights @ cov @ weights
                port_vol = np.sqrt(port_var) * np.sqrt(252)

                portfolios[name] = {
                    "weights": pd.Series(weights, index=self.tickers),
                    "annual_vol": port_vol,
                    "max_weight": weights.max(),
                    "min_weight": weights.min(),
                    "n_short": (weights < -0.01).sum(),
                    "weight_range": weights.max() - weights.min(),
                    "turnover_proxy": np.sum(np.abs(weights)),
                }
            except np.linalg.LinAlgError:
                logger.warning(f"Singular matrix for {name} — skipping MVP")

        # Summary table
        summary = pd.DataFrame(
            {
                name: {
                    "Annual_Vol_%": p["annual_vol"] * 100,
                    "Max_Weight_%": p["max_weight"] * 100,
                    "Min_Weight_%": p["min_weight"] * 100,
                    "N_Short": p["n_short"],
                    "Gross_Exposure": p["turnover_proxy"],
                }
                for name, p in portfolios.items()
            }
        ).T

        return summary, portfolios

    # ------------------------------------------------------------------
    # 3. Out-of-Sample Stability
    # ------------------------------------------------------------------
    def rolling_stability(
        self, window: int = 252, step: int = 21, method: str = "ledoit_wolf"
    ) -> Dict:
        """
        Test covariance estimator stability by computing estimates on
        rolling windows and measuring how much the MVP changes over time.

        A good estimator should produce stable portfolios across windows.
        """
        from .estimators import CovarianceEstimator

        dates = []
        vols = []
        max_weights = []
        turnover = []
        prev_weights = None

        for i in range(window, len(self.returns), step):
            sub = self.returns.iloc[i - window : i]
            est = CovarianceEstimator(sub)

            # Get covariance
            if method == "sample":
                result = est.sample()
            elif method == "ledoit_wolf":
                result = est.ledoit_wolf()
            elif method == "oas":
                result = est.oracle_approximating()
            elif method == "denoised":
                result = est.denoised()
            elif method == "gerber":
                result = est.gerber()
            elif method == "ewma":
                result = est.ewma()
            else:
                result = est.sample()

            cov = result["covariance"].values

            # MVP
            try:
                ones = np.ones(self.n_assets)
                inv_cov_ones = np.linalg.solve(cov, ones)
                w = inv_cov_ones / (ones @ inv_cov_ones)
            except np.linalg.LinAlgError:
                continue

            port_vol = np.sqrt(w @ cov @ w) * np.sqrt(252)
            dates.append(self.returns.index[i])
            vols.append(port_vol)
            max_weights.append(np.max(np.abs(w)))

            if prev_weights is not None:
                turnover.append(np.sum(np.abs(w - prev_weights)))
            else:
                turnover.append(0)
            prev_weights = w.copy()

        return {
            "dates": dates,
            "volatility": vols,
            "max_weight": max_weights,
            "turnover": turnover,
            "method": method,
        }

    # ------------------------------------------------------------------
    # 4. Frobenius Distance Between Estimators
    # ------------------------------------------------------------------
    def pairwise_distances(
        self, cov_results: Dict[str, Dict], metric: str = "correlation"
    ) -> pd.DataFrame:
        """
        Compute Frobenius distance between all pairs of estimators.
        Small distance = estimators agree. Large = they differ significantly.
        """
        names = list(cov_results.keys())
        n = len(names)
        dist_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                m1 = cov_results[names[i]][metric].values
                m2 = cov_results[names[j]][metric].values
                d = np.linalg.norm(m1 - m2, "fro")
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d

        return pd.DataFrame(dist_matrix, index=names, columns=names)

    # ------------------------------------------------------------------
    # 5. Marchenko-Pastur Fit
    # ------------------------------------------------------------------
    def marchenko_pastur_pdf(
        self, q: float, sigma: float = 1.0, pts: int = 1000
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Theoretical Marchenko-Pastur density for random correlation matrices.

        Parameters
        ----------
        q : float
            Ratio n_assets / n_observations
        sigma : float
            Scale parameter
        """
        lambda_min = sigma**2 * (1 - np.sqrt(q)) ** 2
        lambda_max = sigma**2 * (1 + np.sqrt(q)) ** 2

        x = np.linspace(lambda_min * 0.99, lambda_max * 1.01, pts)
        pdf = np.zeros_like(x)

        valid = (x >= lambda_min) & (x <= lambda_max)
        pdf[valid] = (1 / (2 * np.pi * q * sigma**2 * x[valid])) * np.sqrt(
            (lambda_max - x[valid]) * (x[valid] - lambda_min)
        )

        return x, pdf

    # ------------------------------------------------------------------
    # Visualization Methods
    # ------------------------------------------------------------------
    def plot_eigenvalue_spectrum(
        self, cov_results: Dict[str, Dict], figsize: Tuple = (14, 6)
    ):
        """Plot eigenvalue spectra for all estimators + MP distribution."""
        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Left: eigenvalue spectra
        ax = axes[0]
        for name, result in cov_results.items():
            corr = result["correlation"].values
            eigs = np.sort(np.linalg.eigvalsh(corr))[::-1]
            ax.plot(
                range(1, len(eigs) + 1), eigs, "o-", markersize=3, alpha=0.7, label=name
            )

        # Marchenko-Pastur bounds
        q = self.n_assets / len(self.returns)
        mp_upper = (1 + np.sqrt(q)) ** 2
        mp_lower = (1 - np.sqrt(q)) ** 2
        ax.axhline(
            y=mp_upper,
            color="red",
            linestyle="--",
            alpha=0.5,
            label=f"MP upper ({mp_upper:.2f})",
        )
        ax.axhline(
            y=mp_lower,
            color="blue",
            linestyle="--",
            alpha=0.5,
            label=f"MP lower ({mp_lower:.2f})",
        )

        ax.set_xlabel("Component")
        ax.set_ylabel("Eigenvalue")
        ax.set_title("Correlation Matrix Eigenvalue Spectrum", fontweight="bold")
        ax.legend(fontsize=8)
        ax.set_yscale("log")

        # Right: histogram of sample eigenvalues vs MP density
        ax = axes[1]
        sample_corr = cov_results[list(cov_results.keys())[0]]["correlation"].values
        eigs_sample = np.linalg.eigvalsh(sample_corr)
        ax.hist(
            eigs_sample,
            bins=30,
            density=True,
            alpha=0.6,
            color="steelblue",
            label="Sample eigenvalues",
        )

        x_mp, pdf_mp = self.marchenko_pastur_pdf(q)
        ax.plot(x_mp, pdf_mp, "r-", lw=2, label="Marchenko-Pastur")
        ax.set_xlabel("Eigenvalue")
        ax.set_ylabel("Density")
        ax.set_title(
            "Eigenvalue Distribution vs Random Matrix Theory", fontweight="bold"
        )
        ax.legend()

        plt.tight_layout()
        return fig

    def plot_mvp_comparison(self, portfolios: Dict, figsize: Tuple = (16, 8)):
        """Compare MVP weights across estimators."""
        n_methods = len(portfolios)
        fig, axes = plt.subplots(1, min(n_methods, 4), figsize=figsize, sharey=True)
        if not hasattr(axes, "__len__"):
            axes = [axes]

        for idx, (name, p) in enumerate(list(portfolios.items())[:4]):
            ax = axes[idx]
            w = p["weights"].sort_values()
            colors = ["red" if v < 0 else "steelblue" for v in w.values]
            w.plot(kind="barh", ax=ax, color=colors, edgecolor="white")
            ax.set_title(
                f"{name}\nVol: {p['annual_vol']*100:.1f}%",
                fontsize=10,
                fontweight="bold",
            )
            ax.axvline(x=0, color="gray", linewidth=0.5)

        plt.suptitle(
            "Minimum Variance Portfolio Weights by Estimator",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        return fig

    def plot_correlation_differences(
        self,
        cov_results: Dict[str, Dict],
        reference: str = "Sample",
        figsize: Tuple = (18, 5),
    ):
        """Heatmaps of correlation differences vs reference method."""
        ref_corr = cov_results[reference]["correlation"].values
        methods = [m for m in cov_results if m != reference][:3]

        fig, axes = plt.subplots(1, len(methods), figsize=figsize)
        if not hasattr(axes, "__len__"):
            axes = [axes]

        for ax, method in zip(axes, methods):
            diff = cov_results[method]["correlation"].values - ref_corr
            mask = np.triu(np.ones_like(diff, dtype=bool), k=1)
            sns.heatmap(
                pd.DataFrame(diff, index=self.tickers, columns=self.tickers),
                mask=mask,
                cmap="RdBu_r",
                center=0,
                vmin=-0.3,
                vmax=0.3,
                annot=False,
                square=True,
                linewidths=0.2,
                ax=ax,
                cbar_kws={"shrink": 0.8},
            )
            ax.set_title(f"{method} − {reference}", fontsize=10, fontweight="bold")

        plt.suptitle(
            f"Correlation Differences vs {reference}",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        return fig

    def plot_stability_comparison(
        self,
        methods: List[str] = None,
        window: int = 252,
        step: int = 21,
        figsize: Tuple = (16, 10),
    ):
        """Compare rolling MVP volatility and turnover across methods."""
        if methods is None:
            methods = ["sample", "ledoit_wolf", "denoised", "gerber"]

        fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)

        for method in methods:
            try:
                result = self.rolling_stability(window=window, step=step, method=method)
                axes[0].plot(
                    result["dates"],
                    [v * 100 for v in result["volatility"]],
                    label=method,
                    alpha=0.8,
                    lw=1.2,
                )
                axes[1].plot(
                    result["dates"], result["turnover"], label=method, alpha=0.8, lw=1.2
                )
            except Exception as e:
                logger.warning(f"Rolling stability failed for {method}: {e}")

        axes[0].set_ylabel("MVP Annual Volatility (%)")
        axes[0].set_title(
            "Rolling Minimum Variance Portfolio — Volatility", fontweight="bold"
        )
        axes[0].legend(fontsize=9)

        axes[1].set_ylabel("Portfolio Turnover")
        axes[1].set_title("Rolling MVP — Turnover (Weight Changes)", fontweight="bold")
        axes[1].legend(fontsize=9)

        plt.tight_layout()
        return fig
