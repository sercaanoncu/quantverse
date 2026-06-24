"""
Scenario Analysis & Visualization
====================================
Tools for visualizing Monte Carlo results:
probability cones, terminal wealth distributions,
and strategy comparison under simulation.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class ScenarioAnalyzer:
    """Visualization and analysis tools for Monte Carlo simulation results."""

    @staticmethod
    def plot_probability_cone(
        sim_result: Dict, figsize: Tuple = (16, 8), n_sample_paths: int = 50
    ) -> plt.Figure:
        """
        Plot probability cone showing confidence bands around projected paths.

        Shows: median path, 50%/80%/95% confidence intervals, sample paths
        """
        wealth = sim_result["wealth_paths"]
        horizon = wealth.shape[1]
        x = np.arange(1, horizon + 1)

        # Percentiles at each time step
        p2_5 = np.percentile(wealth, 2.5, axis=0)
        p10 = np.percentile(wealth, 10, axis=0)
        p25 = np.percentile(wealth, 25, axis=0)
        p50 = np.percentile(wealth, 50, axis=0)
        p75 = np.percentile(wealth, 75, axis=0)
        p90 = np.percentile(wealth, 90, axis=0)
        p97_5 = np.percentile(wealth, 97.5, axis=0)

        fig, ax = plt.subplots(figsize=figsize)

        # Confidence bands
        ax.fill_between(x, p2_5, p97_5, alpha=0.1, color="steelblue", label="95% CI")
        ax.fill_between(x, p10, p90, alpha=0.15, color="steelblue", label="80% CI")
        ax.fill_between(x, p25, p75, alpha=0.2, color="steelblue", label="50% CI")

        # Median
        ax.plot(x, p50, color="navy", lw=2.5, label="Median")

        # Sample paths
        np.random.seed(42)
        idx = np.random.choice(
            wealth.shape[0], min(n_sample_paths, wealth.shape[0]), replace=False
        )
        for i in idx:
            ax.plot(x, wealth[i], color="gray", alpha=0.05, lw=0.5)

        # Reference line
        ax.axhline(
            y=1.0, color="red", linestyle="--", alpha=0.5, label="Starting Value"
        )

        ax.set_xlabel("Trading Days", fontsize=13)
        ax.set_ylabel("Portfolio Value (Starting = 1.0)", fontsize=13)
        ax.set_title(
            f"Monte Carlo Probability Cone — {sim_result['method']}\n"
            f"({sim_result['n_sims']:,} simulations, {sim_result['horizon']} days)",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(loc="upper left", fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_terminal_distribution(
        sim_result: Dict, figsize: Tuple = (14, 6)
    ) -> plt.Figure:
        """Plot terminal wealth distribution with key statistics."""
        terminal = sim_result["terminal_returns"] * 100
        pcts = sim_result["percentiles"]

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Histogram
        ax = axes[0]
        ax.hist(
            terminal,
            bins=100,
            density=True,
            alpha=0.6,
            color="steelblue",
            edgecolor="white",
        )
        ax.axvline(0, color="red", lw=1.5, linestyle="--", alpha=0.5)
        ax.axvline(
            np.median(terminal),
            color="navy",
            lw=2,
            label=f"Median: {np.median(terminal):.1f}%",
        )
        ax.axvline(
            pcts["p5"] * 100,
            color="orange",
            lw=1.5,
            linestyle="--",
            label=f"5th pct: {pcts['p5']*100:.1f}%",
        )
        ax.axvline(
            pcts["p95"] * 100,
            color="green",
            lw=1.5,
            linestyle="--",
            label=f"95th pct: {pcts['p95']*100:.1f}%",
        )

        ax.set_xlabel("Terminal Return (%)")
        ax.set_ylabel("Density")
        ax.set_title(
            f"Terminal Return Distribution — {sim_result['method']}", fontweight="bold"
        )
        ax.legend(fontsize=9)

        # CDF
        ax = axes[1]
        sorted_t = np.sort(terminal)
        cdf = np.arange(1, len(sorted_t) + 1) / len(sorted_t)
        ax.plot(sorted_t, cdf, color="steelblue", lw=1.5)
        ax.axhline(0.5, color="gray", linestyle=":", alpha=0.5)
        ax.axvline(0, color="red", linestyle="--", alpha=0.5)
        ax.fill_between(sorted_t, cdf, where=(sorted_t < 0), alpha=0.2, color="red")

        prob_gain = sim_result["prob_positive"]
        ax.set_xlabel("Terminal Return (%)")
        ax.set_ylabel("Cumulative Probability")
        ax.set_title(f"CDF — P(gain) = {prob_gain:.1%}", fontweight="bold")

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_method_comparison(
        all_results: Dict[str, Dict], figsize: Tuple = (16, 10)
    ) -> plt.Figure:
        """Compare terminal distributions across simulation methods."""
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        axes = axes.ravel()

        colors = ["steelblue", "coral", "seagreen", "mediumpurple"]

        for idx, (name, result) in enumerate(all_results.items()):
            if idx >= 4:
                break
            ax = axes[idx]
            terminal = result["terminal_returns"] * 100
            ax.hist(
                terminal,
                bins=80,
                density=True,
                alpha=0.6,
                color=colors[idx],
                edgecolor="white",
            )
            ax.axvline(0, color="red", lw=1, linestyle="--", alpha=0.5)
            ax.axvline(np.median(terminal), color="black", lw=2)

            stats_text = (
                f"Median: {np.median(terminal):.1f}%\n"
                f"VaR(5%): {result['var_5pct']*100:.1f}%\n"
                f"P(loss): {(1-result['prob_positive'])*100:.1f}%\n"
                f"Skew: {result['skewness']:.2f}"
            )
            ax.text(
                0.02,
                0.98,
                stats_text,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
            )

            ax.set_title(name, fontweight="bold")
            ax.set_xlabel("Terminal Return (%)")

        plt.suptitle(
            "Monte Carlo: Method Comparison", fontsize=15, fontweight="bold", y=1.02
        )
        plt.tight_layout()
        return fig

    @staticmethod
    def plot_drawdown_distribution(
        sim_result: Dict, figsize: Tuple = (14, 5)
    ) -> plt.Figure:
        """Plot distribution of maximum drawdowns across simulations."""
        mdd = sim_result["max_drawdowns"] * 100

        fig, ax = plt.subplots(figsize=figsize)
        ax.hist(mdd, bins=80, density=True, alpha=0.6, color="coral", edgecolor="white")
        ax.axvline(
            np.median(mdd), color="black", lw=2, label=f"Median: {np.median(mdd):.1f}%"
        )
        ax.axvline(
            np.percentile(mdd, 5),
            color="darkred",
            lw=1.5,
            linestyle="--",
            label=f"5th pct: {np.percentile(mdd, 5):.1f}%",
        )

        ax.set_xlabel("Maximum Drawdown (%)")
        ax.set_ylabel("Density")
        ax.set_title(
            f"Max Drawdown Distribution — {sim_result['method']}",
            fontsize=13,
            fontweight="bold",
        )
        ax.legend()
        plt.tight_layout()
        return fig

    @staticmethod
    def summary_table(all_results: Dict[str, Dict]) -> pd.DataFrame:
        """Build a summary comparison table across all methods."""
        rows = []
        for name, r in all_results.items():
            rows.append(
                {
                    "Method": name,
                    "Mean_Return_%": r["mean_return"] * 100,
                    "Median_Return_%": r["median_return"] * 100,
                    "Std_%": r["std_return"] * 100,
                    "Skewness": r["skewness"],
                    "Kurtosis": r["kurtosis"],
                    "VaR_5%": r["var_5pct"] * 100,
                    "CVaR_5%": r["cvar_5pct"] * 100,
                    "P(Positive)_%": r["prob_positive"] * 100,
                    "P(Loss>10%)_%": r["prob_loss_10pct"] * 100,
                    "P(Loss>20%)_%": r["prob_loss_20pct"] * 100,
                    "P(Gain>20%)_%": r["prob_gain_20pct"] * 100,
                    "Avg_MaxDD_%": r["avg_max_drawdown"] * 100,
                    "Worst_MaxDD_%": r["worst_max_drawdown"] * 100,
                }
            )
        return pd.DataFrame(rows).set_index("Method")

    @staticmethod
    def plot_stress_waterfall(
        stress_result: Dict, figsize: Tuple = (12, 6)
    ) -> plt.Figure:
        """Waterfall chart showing stress test contribution breakdown."""
        contributions = stress_result["contributions"]
        total = stress_result["portfolio_impact_%"]

        labels = list(contributions.keys()) + ["TOTAL"]
        values = list(contributions.values()) + [total]

        fig, ax = plt.subplots(figsize=figsize)

        colors = ["red" if v < 0 else "green" for v in values[:-1]] + ["navy"]
        cumulative = np.cumsum([0] + values[:-1])

        for i, (label, val) in enumerate(zip(labels[:-1], values[:-1])):
            ax.bar(
                i,
                val,
                bottom=cumulative[i],
                color=colors[i],
                edgecolor="white",
                width=0.6,
            )

        # Total bar
        ax.bar(len(labels) - 1, total, color="navy", edgecolor="white", width=0.6)

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_ylabel("Impact (%)")
        ax.set_title(
            f"Stress Test: {stress_result['scenario']}\n"
            f"{stress_result['description']}",
            fontsize=13,
            fontweight="bold",
        )
        ax.axhline(y=0, color="gray", linewidth=0.5)

        plt.tight_layout()
        return fig
