"""
Strategy Tearsheet Generator
===============================
Produces a single-page quantitative tearsheet combining
performance metrics, equity curve, drawdowns, rolling Sharpe,
monthly returns heatmap, and risk decomposition.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import logging
from typing import Dict, Optional

from project.constants import DEFAULT_RISK_FREE_RATE

logger = logging.getLogger(__name__)


class TearsheetGenerator:
    """
    Generate institutional-quality strategy tearsheets.
    """

    def __init__(
        self,
        returns: pd.Series,
        benchmark: Optional[pd.Series] = None,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        name: str = "Strategy",
    ):
        self.returns = returns.dropna()
        self.benchmark = benchmark
        self.rf = risk_free_rate
        self.name = name

        # Precompute
        self.cum = (1 + self.returns).cumprod()
        self.dd = self.cum / self.cum.cummax().clip(lower=1.0) - 1

        if benchmark is not None:
            bench_common = benchmark.reindex(self.returns.index).dropna()
            self.bench_cum = (1 + bench_common).cumprod()

    def _compute_metrics(self) -> Dict:
        """Compute all summary metrics."""
        r = self.returns
        n = len(r)
        years = n / 252

        total_ret = (1 + r).prod() - 1
        cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 else 0
        ann_vol = r.std() * np.sqrt(252)
        rf_daily = (1 + self.rf) ** (1 / 252) - 1
        excess = r - rf_daily
        annualized_excess_return = excess.mean() * 252
        sharpe = annualized_excess_return / ann_vol if ann_vol > 0 else 0

        # Lower partial moment of order two around the daily risk-free hurdle.
        squared_neg = np.minimum(excess, 0) ** 2
        down_vol = np.sqrt(squared_neg.mean() * 252)
        sortino = annualized_excess_return / down_vol if down_vol > 0 else 0

        max_dd = self.dd.min()
        calmar = cagr / abs(max_dd) if max_dd != 0 else np.inf

        # Tail
        var5 = -np.percentile(r, 5)
        cutoff = np.percentile(r, 5)
        cvar5 = -r[r <= cutoff].mean() if (r <= cutoff).any() else var5

        # Monthly
        monthly = r.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        pos_months = (monthly > 0).mean()
        best_month = monthly.max()
        worst_month = monthly.min()

        metrics = {
            "Total Return": f"{total_ret:.2%}",
            "CAGR": f"{cagr:.2%}",
            "Volatility": f"{ann_vol:.2%}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Sortino Ratio": f"{sortino:.2f}",
            "Calmar Ratio": f"{calmar:.2f}",
            "Max Drawdown": f"{max_dd:.2%}",
            "VaR Loss (5%)": f"{var5:.2%}",
            "CVaR Loss (5%)": f"{cvar5:.2%}",
            "Skewness": f"{stats.skew(r):.2f}",
            "Kurtosis": f"{stats.kurtosis(r):.2f}",
            "Win Rate": f"{(r > 0).mean():.1%}",
            "Best Month": f"{best_month:.2%}",
            "Worst Month": f"{worst_month:.2%}",
            "Positive Months": f"{pos_months:.1%}",
            "Trading Days": f"{n}",
        }

        if self.benchmark is not None:
            aligned = pd.DataFrame(
                {"portfolio": r, "benchmark": self.benchmark}
            ).dropna()
            if len(aligned) > 1:
                r_common = aligned["portfolio"]
                bench_common = aligned["benchmark"]
                active = r_common - bench_common
                te = active.std() * np.sqrt(252)
                ir = active.mean() * 252 / te if te > 0 else 0
                cov_mat = np.cov(r_common, bench_common)
                beta = cov_mat[0, 1] / cov_mat[1, 1] if cov_mat[1, 1] > 0 else 0
                alpha_daily = (r_common - rf_daily) - beta * (bench_common - rf_daily)
                alpha = alpha_daily.mean() * 252
                metrics["Beta"] = f"{beta:.2f}"
                metrics["Jensen Alpha (ann.)"] = f"{alpha:.2%}"
                metrics["Tracking Error"] = f"{te:.2%}"
                metrics["Information Ratio"] = f"{ir:.2f}"
            else:
                unavailable = "N/A (insufficient overlap)"
                metrics["Beta"] = unavailable
                metrics["Jensen Alpha (ann.)"] = unavailable
                metrics["Tracking Error"] = unavailable
                metrics["Information Ratio"] = unavailable

        return metrics

    def generate(
        self, figsize: tuple = (20, 28), save_path: Optional[str] = None
    ) -> plt.Figure:
        """Generate the full tearsheet figure."""
        metrics = self._compute_metrics()

        fig = plt.figure(figsize=figsize, facecolor="white")
        gs = gridspec.GridSpec(
            6,
            2,
            figure=fig,
            hspace=0.35,
            wspace=0.25,
            height_ratios=[0.5, 1.2, 0.8, 0.8, 0.8, 1.0],
        )

        # --- Row 0: Title + Metrics ---
        ax_title = fig.add_subplot(gs[0, :])
        ax_title.axis("off")
        ax_title.text(
            0.5,
            0.85,
            f"QUANTITATIVE TEARSHEET — {self.name.upper()}",
            ha="center",
            va="top",
            fontsize=22,
            fontweight="bold",
            color="#1a237e",
        )
        ax_title.text(
            0.5,
            0.55,
            f'{self.returns.index[0].strftime("%Y-%m-%d")} to {self.returns.index[-1].strftime("%Y-%m-%d")}',
            ha="center",
            va="top",
            fontsize=13,
            color="gray",
        )

        # Metrics in columns
        items = list(metrics.items())
        n_cols = 4
        n_rows_m = (len(items) + n_cols - 1) // n_cols
        for i, (k, v) in enumerate(items):
            col = i // n_rows_m
            row = i % n_rows_m
            x = 0.05 + col * 0.24
            y = 0.35 - row * 0.065
            ax_title.text(
                x, y, f"{k}:", fontsize=9, color="gray", transform=ax_title.transAxes
            )
            ax_title.text(
                x + 0.14,
                y,
                v,
                fontsize=9,
                fontweight="bold",
                transform=ax_title.transAxes,
            )

        # --- Row 1: Equity Curve ---
        ax_eq = fig.add_subplot(gs[1, :])
        ax_eq.plot(
            self.cum.index, self.cum.values, color="#1565C0", lw=1.8, label=self.name
        )
        if self.benchmark is not None:
            ax_eq.plot(
                self.bench_cum.index,
                self.bench_cum.values,
                color="gray",
                lw=1.2,
                linestyle="--",
                label="Benchmark",
                alpha=0.7,
            )
        ax_eq.set_ylabel("Cumulative Return", fontsize=11)
        ax_eq.set_title("Equity Curve", fontsize=13, fontweight="bold")
        ax_eq.legend(fontsize=10)
        ax_eq.set_yscale("log")
        ax_eq.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))

        # --- Row 2 Left: Underwater ---
        ax_uw = fig.add_subplot(gs[2, 0])
        ax_uw.fill_between(
            self.dd.index, self.dd.values * 100, 0, color="#E53935", alpha=0.4
        )
        ax_uw.plot(self.dd.index, self.dd.values * 100, color="#B71C1C", lw=0.8)
        ax_uw.set_ylabel("Drawdown (%)", fontsize=10)
        ax_uw.set_title("Underwater Plot", fontsize=12, fontweight="bold")

        # --- Row 2 Right: Rolling Sharpe ---
        ax_rs = fig.add_subplot(gs[2, 1])
        rf_daily = (1 + self.rf) ** (1 / 252) - 1
        rolling_sharpe = self.returns.rolling(126).apply(
            lambda x: (
                (x.mean() - rf_daily) / x.std() * np.sqrt(252) if x.std() > 0 else 0
            )
        )
        ax_rs.plot(rolling_sharpe.index, rolling_sharpe.values, color="#00897B", lw=1.2)
        ax_rs.axhline(0, color="gray", linewidth=0.5)
        ax_rs.axhline(1, color="green", linewidth=0.5, linestyle="--", alpha=0.5)
        ax_rs.set_ylabel("Sharpe Ratio", fontsize=10)
        ax_rs.set_title("Rolling 6-Month Sharpe", fontsize=12, fontweight="bold")

        # --- Row 3 Left: Return Distribution ---
        ax_dist = fig.add_subplot(gs[3, 0])
        ax_dist.hist(
            self.returns * 100,
            bins=80,
            density=True,
            alpha=0.6,
            color="#1565C0",
            edgecolor="white",
        )
        ax_dist.axvline(0, color="red", linestyle="--", alpha=0.5)
        ax_dist.set_xlabel("Daily Return (%)", fontsize=10)
        ax_dist.set_title("Return Distribution", fontsize=12, fontweight="bold")

        # --- Row 3 Right: Rolling Volatility ---
        ax_rv = fig.add_subplot(gs[3, 1])
        rolling_vol = self.returns.rolling(21).std() * np.sqrt(252) * 100
        ax_rv.plot(rolling_vol.index, rolling_vol.values, color="#E65100", lw=1)
        ax_rv.set_ylabel("Annualized Vol (%)", fontsize=10)
        ax_rv.set_title("Rolling 1-Month Volatility", fontsize=12, fontweight="bold")

        # --- Row 4 Left: Monthly Returns ---
        ax_monthly = fig.add_subplot(gs[4, 0])
        monthly = self.returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        monthly_by_month = monthly.groupby(monthly.index.month).mean() * 100
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        colors = ["green" if v > 0 else "red" for v in monthly_by_month.values]
        ax_monthly.bar(
            range(1, 13),
            monthly_by_month.values,
            color=colors,
            edgecolor="white",
            alpha=0.7,
        )
        ax_monthly.set_xticks(range(1, 13))
        ax_monthly.set_xticklabels(month_names, fontsize=8)
        ax_monthly.set_ylabel("Avg Return (%)", fontsize=10)
        ax_monthly.set_title("Average Monthly Returns", fontsize=12, fontweight="bold")
        ax_monthly.axhline(0, color="gray", linewidth=0.5)

        # --- Row 4 Right: Annual Returns ---
        ax_annual = fig.add_subplot(gs[4, 1])
        annual = self.returns.resample("YE").apply(lambda x: (1 + x).prod() - 1)
        colors_a = ["green" if v > 0 else "red" for v in annual.values]
        ax_annual.bar(
            annual.index.year,
            annual.values * 100,
            color=colors_a,
            edgecolor="white",
            alpha=0.7,
        )
        ax_annual.set_ylabel("Return (%)", fontsize=10)
        ax_annual.set_title("Annual Returns", fontsize=12, fontweight="bold")
        ax_annual.axhline(0, color="gray", linewidth=0.5)

        # --- Row 5: Monthly Heatmap ---
        ax_hm = fig.add_subplot(gs[5, :])
        monthly_df = monthly.to_frame("return")
        monthly_df["Year"] = monthly_df.index.year
        monthly_df["Month"] = monthly_df.index.month
        heatmap_data = (
            monthly_df.pivot(index="Year", columns="Month", values="return") * 100
        )
        heatmap_data.columns = [month_names[m - 1] for m in heatmap_data.columns]

        sns.heatmap(
            heatmap_data,
            annot=True,
            fmt=".1f",
            cmap="RdYlGn",
            center=0,
            linewidths=0.3,
            ax=ax_hm,
            cbar_kws={"label": "Return (%)", "shrink": 0.6},
            annot_kws={"fontsize": 8},
        )
        ax_hm.set_title("Monthly Returns Heatmap (%)", fontsize=12, fontweight="bold")

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
            logger.info(f"Tearsheet saved: {save_path}")

        return fig
