"""
Dashboard Data Builder
========================
Prepares aggregated data structures for the final dashboard
and multi-strategy tearsheet comparison.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from typing import Dict, Optional, List

from project.constants import DEFAULT_RISK_FREE_RATE
from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


class DashboardDataBuilder:
    """
    Build aggregated views across all modules for the final dashboard.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        all_weights: pd.DataFrame,
        asset_class_map: Dict[str, str],
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ):
        self.returns = returns.dropna()
        self.all_weights = all_weights
        self.class_map = asset_class_map
        self.risk_free_rate = risk_free_rate
        self.tickers = list(returns.columns)
        self.strategies = list(all_weights.columns)

    def _port_returns(self, strategy: str) -> pd.Series:
        w = align_portfolio_weights(
            self.all_weights[strategy],
            self.tickers,
            context=f"Dashboard strategy {strategy}",
        ).to_numpy(dtype=float)
        return pd.Series(
            self.returns.values @ w, index=self.returns.index, name=strategy
        )

    # ------------------------------------------------------------------
    # 1. Multi-Strategy Equity Curves
    # ------------------------------------------------------------------
    def equity_curves(self) -> pd.DataFrame:
        curves = {}
        for strat in self.strategies:
            r = self._port_returns(strat)
            curves[strat] = (1 + r).cumprod()
        return pd.DataFrame(curves)

    # ------------------------------------------------------------------
    # 2. Risk-Return Scatter Data
    # ------------------------------------------------------------------
    def risk_return_scatter(self) -> pd.DataFrame:
        rows = []
        for strat in self.strategies:
            r = self._port_returns(strat)
            ann_ret = r.mean() * 252
            ann_vol = r.std() * np.sqrt(252)
            sharpe = (ann_ret - self.risk_free_rate) / ann_vol if ann_vol > 0 else 0
            cum = (1 + r).cumprod()
            max_dd = (cum / cum.cummax().clip(lower=1.0) - 1).min()
            rows.append(
                {
                    "Strategy": strat,
                    "Return": ann_ret,
                    "Volatility": ann_vol,
                    "Sharpe": sharpe,
                    "Max_DD": max_dd,
                }
            )
        return pd.DataFrame(rows).set_index("Strategy")

    # ------------------------------------------------------------------
    # 3. Asset Class Allocation Summary
    # ------------------------------------------------------------------
    def allocation_summary(self) -> pd.DataFrame:
        alloc = {}
        for strat in self.strategies:
            w = self.all_weights[strat]
            ac_w = {}
            for ac in sorted(set(self.class_map.values()) - {"signals"}):
                tickers = [
                    t
                    for t, c in self.class_map.items()
                    if c == ac and t in self.tickers
                ]
                ac_w[ac] = w.reindex(tickers).fillna(0).sum() * 100
            alloc[strat] = ac_w
        return pd.DataFrame(alloc).T

    # ------------------------------------------------------------------
    # 4. Correlation of Strategy Returns
    # ------------------------------------------------------------------
    def strategy_correlation(self) -> pd.DataFrame:
        ret_df = pd.DataFrame({s: self._port_returns(s) for s in self.strategies})
        return ret_df.corr()

    # ------------------------------------------------------------------
    # 5. Comprehensive Dashboard Figure
    # ------------------------------------------------------------------
    def plot_dashboard(
        self, figsize: tuple = (24, 20), save_path: Optional[str] = None
    ) -> plt.Figure:
        """Generate a multi-panel summary dashboard."""
        fig = plt.figure(figsize=figsize, facecolor="white")
        gs = plt.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.25)

        # 1. Equity Curves (top, full width)
        ax1 = fig.add_subplot(gs[0, :])
        curves = self.equity_curves()
        for col in curves.columns:
            ax1.plot(curves.index, curves[col], lw=1.5, alpha=0.8, label=col)
        ax1.set_ylabel("Cumulative Return")
        ax1.set_title("Strategy Equity Curves", fontsize=14, fontweight="bold")
        ax1.legend(fontsize=8, ncol=4)
        ax1.set_yscale("log")
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1f}"))

        # 2. Risk-Return Scatter
        ax2 = fig.add_subplot(gs[1, 0])
        rr = self.risk_return_scatter()
        colors = plt.cm.Set2(np.linspace(0, 1, len(rr)))
        for i, (strat, row) in enumerate(rr.iterrows()):
            ax2.scatter(
                row["Volatility"] * 100,
                row["Return"] * 100,
                s=120,
                c=[colors[i]],
                edgecolors="white",
                linewidth=2,
                zorder=5,
            )
            ax2.annotate(
                strat,
                (row["Volatility"] * 100, row["Return"] * 100),
                fontsize=7,
                textcoords="offset points",
                xytext=(4, 4),
            )
        ax2.set_xlabel("Volatility (%)")
        ax2.set_ylabel("Return (%)")
        ax2.set_title("Risk-Return", fontsize=12, fontweight="bold")

        # 3. Asset Class Allocation
        ax3 = fig.add_subplot(gs[1, 1])
        alloc = self.allocation_summary()
        alloc.plot(kind="bar", stacked=True, ax=ax3, edgecolor="white", linewidth=0.3)
        ax3.set_ylabel("Allocation (%)")
        ax3.set_title("Asset Class Allocation", fontsize=12, fontweight="bold")
        ax3.legend(fontsize=6, bbox_to_anchor=(1.02, 1), loc="upper left")
        ax3.set_xticklabels(ax3.get_xticklabels(), rotation=35, ha="right", fontsize=8)

        # 4. Strategy Correlation
        ax4 = fig.add_subplot(gs[1, 2])
        corr = self.strategy_correlation()
        sns.heatmap(
            corr,
            annot=True,
            fmt=".2f",
            cmap="RdYlBu_r",
            center=0,
            linewidths=0.3,
            ax=ax4,
            annot_kws={"fontsize": 7},
            cbar_kws={"shrink": 0.8},
        )
        ax4.set_title("Strategy Correlation", fontsize=12, fontweight="bold")
        ax4.tick_params(labelsize=7)

        # 5. Drawdown Comparison
        ax5 = fig.add_subplot(gs[2, 0])
        for strat in self.strategies[:6]:
            r = self._port_returns(strat)
            cum = (1 + r).cumprod()
            dd = (cum / cum.cummax().clip(lower=1.0) - 1) * 100
            ax5.plot(dd.index, dd.values, lw=1, alpha=0.7, label=strat)
        ax5.set_ylabel("Drawdown (%)")
        ax5.set_title("Drawdowns", fontsize=12, fontweight="bold")
        ax5.legend(fontsize=6)

        # 6. Sharpe Ratio Bar
        ax6 = fig.add_subplot(gs[2, 1])
        sharpes = rr["Sharpe"].sort_values(ascending=True)
        colors_s = ["green" if v > 0 else "red" for v in sharpes.values]
        sharpes.plot(kind="barh", ax=ax6, color=colors_s, edgecolor="white")
        ax6.set_xlabel("Sharpe Ratio")
        ax6.set_title("Sharpe Ratios", fontsize=12, fontweight="bold")
        ax6.axvline(x=0, color="gray", linewidth=0.5)

        # 7. Max Drawdown Bar
        ax7 = fig.add_subplot(gs[2, 2])
        mdd = (rr["Max_DD"] * 100).sort_values(ascending=True)
        mdd.plot(kind="barh", ax=ax7, color="coral", edgecolor="white")
        ax7.set_xlabel("Max Drawdown (%)")
        ax7.set_title("Maximum Drawdowns", fontsize=12, fontweight="bold")

        plt.suptitle(
            "QUANTVERSE — Portfolio Intelligence Dashboard",
            fontsize=18,
            fontweight="bold",
            y=1.01,
            color="#1a237e",
        )

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
            logger.info(f"Dashboard saved: {save_path}")

        return fig
