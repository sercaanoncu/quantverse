"""
Publication-Quality Visualizations for Exploratory Analysis
============================================================
QQ-plots, distribution overlays, rolling statistics,
correlation heatmaps, PCA scree plots, and more.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy import stats
from typing import Dict, Optional, List, Tuple

# Style
plt.style.use("seaborn-v0_8-whitegrid")


class ExploratoryVisualizer:
    """Generate publication-quality plots for Module 2 analysis."""

    # Color scheme by asset class
    CLASS_COLORS = {
        "us_equity_sectors": "#2196F3",
        "international_equity": "#4CAF50",
        "crypto": "#FF9800",
        "commodities": "#9C27B0",
        "fixed_income": "#607D8B",
        "reits": "#E91E63",
        "signals": "#999999",
    }

    def __init__(self, asset_class_map: Optional[Dict] = None):
        self.asset_class_map = asset_class_map or {}

    def _get_color(self, ticker: str) -> str:
        ac = self.asset_class_map.get(ticker, "unknown")
        return self.CLASS_COLORS.get(ac, "#333333")

    # ------------------------------------------------------------------
    # 1. Return Distribution Histograms with Fitted Curves
    # ------------------------------------------------------------------
    def plot_return_distributions(
        self,
        returns: pd.DataFrame,
        tickers: Optional[List[str]] = None,
        ncols: int = 4,
        figsize: Optional[Tuple] = None,
    ):
        """Plot histograms with Normal and Student-t overlay for selected assets."""
        if tickers is None:
            tickers = list(returns.columns)[:12]

        nrows = int(np.ceil(len(tickers) / ncols))
        if figsize is None:
            figsize = (ncols * 4, nrows * 3)

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
        axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

        for idx, ticker in enumerate(tickers):
            ax = axes[idx]
            r = returns[ticker].dropna()

            # Histogram
            ax.hist(
                r,
                bins=80,
                density=True,
                alpha=0.5,
                color=self._get_color(ticker),
                edgecolor="white",
                linewidth=0.3,
            )

            # Normal fit
            mu, sigma = r.mean(), r.std()
            x = np.linspace(r.min(), r.max(), 200)
            ax.plot(x, stats.norm.pdf(x, mu, sigma), "b--", lw=1.5, label="Normal")

            # Student-t fit
            df_t, loc_t, scale_t = stats.t.fit(r)
            ax.plot(
                x,
                stats.t.pdf(x, df_t, loc_t, scale_t),
                "r-",
                lw=1.5,
                label=f"t (df={df_t:.1f})",
            )

            ax.set_title(ticker, fontsize=10, fontweight="bold")
            ax.legend(fontsize=7)
            ax.set_xlim(r.quantile(0.001), r.quantile(0.999))

        # Hide empty subplots
        for idx in range(len(tickers), len(axes)):
            axes[idx].set_visible(False)

        fig.suptitle(
            "Return Distributions: Histogram vs. Fitted Distributions",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 2. QQ-Plots Grid
    # ------------------------------------------------------------------
    def plot_qq_grid(
        self,
        returns: pd.DataFrame,
        tickers: Optional[List[str]] = None,
        ncols: int = 4,
        figsize: Optional[Tuple] = None,
    ):
        """Grid of QQ-plots against normal distribution."""
        if tickers is None:
            tickers = list(returns.columns)[:12]

        nrows = int(np.ceil(len(tickers) / ncols))
        if figsize is None:
            figsize = (ncols * 3.5, nrows * 3.5)

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
        axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

        for idx, ticker in enumerate(tickers):
            ax = axes[idx]
            r = returns[ticker].dropna().values

            (theoretical, sample), (slope, intercept, _) = stats.probplot(
                r, dist="norm"
            )
            ax.scatter(
                theoretical, sample, s=5, alpha=0.4, color=self._get_color(ticker)
            )
            ax.plot(theoretical, slope * theoretical + intercept, "r-", lw=1.5)

            ax.set_title(ticker, fontsize=10, fontweight="bold")
            ax.set_xlabel("")
            ax.set_ylabel("")

        for idx in range(len(tickers), len(axes)):
            axes[idx].set_visible(False)

        fig.suptitle(
            "QQ-Plots vs Normal Distribution\n(Heavy tails = deviations at extremes)",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 3. Rolling Volatility
    # ------------------------------------------------------------------
    def plot_rolling_volatility(
        self,
        rolling_stats: Dict[str, pd.DataFrame],
        tickers: Optional[List[str]] = None,
        figsize: Tuple = (16, 8),
    ):
        """Plot rolling annualized volatility for selected assets."""
        vol = rolling_stats["volatility"]
        if tickers is None:
            tickers = list(vol.columns)[:8]

        fig, ax = plt.subplots(figsize=figsize)
        for ticker in tickers:
            if ticker in vol.columns:
                ax.plot(
                    vol[ticker],
                    label=ticker,
                    alpha=0.8,
                    lw=1.2,
                    color=self._get_color(ticker),
                )

        ax.set_title(
            "Rolling 3-Month Annualized Volatility", fontsize=14, fontweight="bold"
        )
        ax.set_ylabel("Annualized Volatility (%)")
        ax.legend(loc="upper left", ncol=2, fontsize=9)
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 4. Skewness-Kurtosis Scatter
    # ------------------------------------------------------------------
    def plot_skewness_kurtosis(self, moments: pd.DataFrame, figsize: Tuple = (12, 8)):
        """Scatter plot of skewness vs excess kurtosis by asset class."""
        fig, ax = plt.subplots(figsize=figsize)

        for ac_name, color in self.CLASS_COLORS.items():
            if ac_name == "signals":
                continue
            mask = moments["Asset_Class"] == ac_name
            subset = moments[mask]
            if len(subset) > 0:
                ax.scatter(
                    subset["Skewness"],
                    subset["Excess_Kurtosis"],
                    c=color,
                    s=100,
                    alpha=0.8,
                    edgecolors="white",
                    linewidth=1.5,
                    label=ac_name.replace("_", " ").title(),
                )
                for ticker in subset.index:
                    ax.annotate(
                        ticker,
                        (
                            subset.loc[ticker, "Skewness"],
                            subset.loc[ticker, "Excess_Kurtosis"],
                        ),
                        fontsize=7,
                        alpha=0.8,
                    )

        # Reference lines
        ax.axhline(
            y=0, color="gray", linestyle="--", alpha=0.5, label="Normal kurtosis"
        )
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.5)

        ax.set_xlabel("Skewness", fontsize=13)
        ax.set_ylabel("Excess Kurtosis", fontsize=13)
        ax.set_title(
            "Skewness vs Kurtosis: Deviation from Normality",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(loc="upper left", framealpha=0.9)
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 5. Crisis vs Calm Correlation Comparison
    # ------------------------------------------------------------------
    def plot_crisis_vs_calm(self, crisis_result: Dict, figsize: Tuple = (20, 6)):
        """Side-by-side heatmaps: crisis correlation vs calm correlation."""
        fig, axes = plt.subplots(1, 3, figsize=figsize)

        for ax, key, title in zip(
            axes,
            ["calm", "crisis", "difference"],
            [
                f"Calm ({crisis_result['n_calm']} days)",
                f"Crisis ({crisis_result['n_crisis']} days)",
                "Difference (Crisis - Calm)",
            ],
        ):
            data = crisis_result[key]
            vmin, vmax = (-1, 1) if key != "difference" else (-0.5, 0.5)
            cmap = "RdBu_r" if key != "difference" else "RdYlGn_r"

            mask = np.triu(np.ones_like(data, dtype=bool), k=1)
            sns.heatmap(
                data,
                mask=mask,
                cmap=cmap,
                center=0,
                vmin=vmin,
                vmax=vmax,
                annot=True,
                fmt=".2f",
                annot_kws={"fontsize": 5},
                square=True,
                linewidths=0.3,
                ax=ax,
            )
            ax.set_title(title, fontsize=11, fontweight="bold")

        fig.suptitle(
            "Correlation Regime: Crisis vs Calm Markets",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 6. PCA Scree Plot & Loadings
    # ------------------------------------------------------------------
    def plot_pca(self, pca_result: Dict, figsize: Tuple = (16, 6)):
        """Scree plot + PC1/PC2 loadings."""
        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Scree plot
        ax = axes[0]
        evr = pca_result["explained_variance_ratio"]
        cumvar = pca_result["cumulative_variance"]
        n = min(15, len(evr))
        x = range(1, n + 1)

        ax.bar(x, evr[:n] * 100, alpha=0.7, color="steelblue", label="Individual")
        ax.plot(x, cumvar[:n] * 100, "ro-", markersize=5, label="Cumulative")
        ax.axhline(y=90, color="gray", linestyle="--", alpha=0.5, label="90% threshold")
        ax.set_xlabel("Principal Component")
        ax.set_ylabel("Variance Explained (%)")
        ax.set_title("PCA Scree Plot", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.set_xticks(list(x))

        # PC1 vs PC2 loadings
        ax = axes[1]
        loadings = pca_result["loadings"]
        for ticker in loadings.index:
            color = self._get_color(ticker)
            ax.scatter(
                loadings.loc[ticker, "PC1"],
                loadings.loc[ticker, "PC2"],
                c=color,
                s=80,
                alpha=0.8,
                edgecolors="white",
            )
            ax.annotate(
                ticker,
                (loadings.loc[ticker, "PC1"], loadings.loc[ticker, "PC2"]),
                fontsize=7,
                alpha=0.8,
            )

        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
        ax.axvline(x=0, color="gray", linestyle="-", alpha=0.3)
        ax.set_xlabel(f"PC1 ({evr[0]:.1%} var)", fontsize=11)
        ax.set_ylabel(f"PC2 ({evr[1]:.1%} var)", fontsize=11)
        ax.set_title("Asset Loadings: PC1 vs PC2", fontsize=12, fontweight="bold")

        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 7. GARCH Conditional Volatility
    # ------------------------------------------------------------------
    def plot_garch_volatility(
        self,
        returns: pd.Series,
        cond_vol: pd.Series,
        ticker: str,
        figsize: Tuple = (16, 8),
    ):
        """Plot returns with GARCH conditional volatility bands."""
        fig, axes = plt.subplots(
            2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [1, 1]}
        )

        # Returns
        ax = axes[0]
        ax.plot(returns.index, returns * 100, alpha=0.6, lw=0.5, color="steelblue")
        ax.fill_between(
            returns.index,
            -cond_vol * 100 * 2,
            cond_vol * 100 * 2,
            alpha=0.2,
            color="red",
            label="±2σ GARCH band",
        )
        ax.set_ylabel("Daily Return (%)")
        ax.set_title(
            f"{ticker}: Returns with GARCH(1,1) Volatility Bands",
            fontsize=12,
            fontweight="bold",
        )
        ax.legend(fontsize=9)

        # Conditional volatility
        ax = axes[1]
        ax.plot(cond_vol.index, cond_vol * 100 * np.sqrt(252), color="darkred", lw=1.2)
        ax.fill_between(
            cond_vol.index, 0, cond_vol * 100 * np.sqrt(252), alpha=0.2, color="red"
        )
        ax.set_ylabel("Annualized Volatility (%)")
        ax.set_title(
            "GARCH(1,1) Conditional Volatility", fontsize=12, fontweight="bold"
        )

        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 8. Stylized Facts Summary
    # ------------------------------------------------------------------
    def plot_stylized_facts_heatmap(
        self, facts: pd.DataFrame, figsize: Tuple = (10, 12)
    ):
        """Boolean heatmap showing which stylized facts hold for each asset."""
        bool_cols = ["Fat_Tails", "Negative_Skew", "Vol_Clustering", "Leverage_Effect"]
        data = facts[bool_cols].astype(int)

        fig, ax = plt.subplots(figsize=figsize)
        sns.heatmap(
            data,
            cmap="RdYlGn",
            center=0.5,
            annot=True,
            fmt="d",
            yticklabels=True,
            linewidths=0.5,
            ax=ax,
            cbar_kws={"label": "Holds (1) / Fails (0)"},
        )
        ax.set_title(
            "Stylized Facts of Financial Returns", fontsize=14, fontweight="bold"
        )
        ax.set_xticklabels(
            ["Fat Tails", "Negative Skew", "Vol Clustering", "Leverage Effect"],
            rotation=30,
            ha="right",
        )
        plt.tight_layout()
        return fig

    # ------------------------------------------------------------------
    # 9. Average Market Correlation Over Time
    # ------------------------------------------------------------------
    def plot_avg_correlation_timeseries(
        self, avg_corr: pd.Series, figsize: Tuple = (16, 5)
    ):
        """Plot the average market-wide correlation over time."""
        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(avg_corr.index, avg_corr.values, color="darkblue", lw=1, alpha=0.8)
        ax.fill_between(avg_corr.index, 0, avg_corr.values, alpha=0.15, color="blue")
        ax.axhline(
            y=avg_corr.mean(),
            color="red",
            linestyle="--",
            lw=1,
            label=f"Mean: {avg_corr.mean():.3f}",
        )
        ax.set_ylabel("Avg Pairwise Correlation")
        ax.set_title(
            "Market-Wide Average Correlation (Rolling 3-Month)",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(fontsize=10)
        plt.tight_layout()
        return fig
