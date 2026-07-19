"""
Drawdown Analysis
==================
Maximum drawdown, drawdown duration, underwater equity curves,
Calmar ratio, and drawdown-at-risk.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, List

from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


class DrawdownAnalyzer:
    """Portfolio and asset-level drawdown analysis."""

    def __init__(self, returns: pd.DataFrame, weights: Optional[pd.Series] = None):
        self.asset_returns = returns.dropna()
        self.tickers = list(returns.columns)

        if weights is not None:
            w = align_portfolio_weights(
                weights,
                self.tickers,
                context="Drawdown portfolio",
            ).to_numpy(dtype=float)
            self.portfolio_returns = pd.Series(
                self.asset_returns.values @ w,
                index=self.asset_returns.index,
                name="Portfolio",
            )
        else:
            w = np.ones(len(self.tickers)) / len(self.tickers)
            self.portfolio_returns = pd.Series(
                self.asset_returns.values @ w,
                index=self.asset_returns.index,
                name="Portfolio",
            )

    def _drawdown_series(self, returns: pd.Series) -> pd.Series:
        """Compute drawdown time series from returns."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = cumulative / running_max - 1
        return drawdown

    # ------------------------------------------------------------------
    # 1. Portfolio Drawdown Series
    # ------------------------------------------------------------------
    def portfolio_drawdown(self) -> pd.Series:
        """Drawdown time series for the portfolio."""
        return self._drawdown_series(self.portfolio_returns)

    def asset_drawdowns(self) -> pd.DataFrame:
        """Drawdown time series for each asset."""
        dd = pd.DataFrame(index=self.asset_returns.index)
        for ticker in self.tickers:
            dd[ticker] = self._drawdown_series(self.asset_returns[ticker])
        return dd

    # ------------------------------------------------------------------
    # 2. Drawdown Table (Top N)
    # ------------------------------------------------------------------
    def top_drawdowns(self, n: int = 10) -> pd.DataFrame:
        """
        Identify the top N drawdown episodes for the portfolio.

        Returns start date, trough date, recovery date, depth, and duration.
        """
        dd = self.portfolio_drawdown()
        cumulative = (1 + self.portfolio_returns).cumprod()

        episodes = []
        in_drawdown = False
        start = None

        for i in range(len(dd)):
            if dd.iloc[i] < 0 and not in_drawdown:
                in_drawdown = True
                start = dd.index[i]
            elif dd.iloc[i] >= 0 and in_drawdown:
                in_drawdown = False
                end = dd.index[i]
                period_dd = dd.loc[start:end]
                trough_idx = period_dd.idxmin()
                depth = period_dd.min()

                episodes.append(
                    {
                        "Start": start,
                        "Trough": trough_idx,
                        "Recovery": end,
                        "Depth_%": depth * 100,
                        "Duration_Days": (end - start).days,
                        "Decline_Days": (trough_idx - start).days,
                        "Recovery_Days": (end - trough_idx).days,
                    }
                )

        # Handle ongoing drawdown
        if in_drawdown and start is not None:
            period_dd = dd.loc[start:]
            trough_idx = period_dd.idxmin()
            episodes.append(
                {
                    "Start": start,
                    "Trough": trough_idx,
                    "Recovery": None,
                    "Depth_%": period_dd.min() * 100,
                    "Duration_Days": (dd.index[-1] - start).days,
                    "Decline_Days": (trough_idx - start).days,
                    "Recovery_Days": None,
                }
            )

        df = pd.DataFrame(episodes)
        if len(df) > 0:
            df = df.sort_values("Depth_%").head(n).reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # 3. Summary Metrics
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, float]:
        """Comprehensive drawdown summary metrics."""
        dd = self.portfolio_drawdown()
        ret = self.portfolio_returns

        max_dd = dd.min()
        ann_return = ret.mean() * 252
        ann_vol = ret.std() * np.sqrt(252)

        # Calmar ratio = annualized return / max drawdown
        calmar = ann_return / abs(max_dd) if max_dd != 0 else np.inf

        # Sterling ratio = (return - rf) / avg of top 5 drawdowns
        top5 = self.top_drawdowns(5)
        avg_top5_dd = top5["Depth_%"].mean() / 100 if len(top5) > 0 else max_dd
        sterling = ann_return / abs(avg_top5_dd) if avg_top5_dd != 0 else np.inf

        # Ulcer Index = RMS of drawdowns
        ulcer = np.sqrt((dd**2).mean())

        # Pain Index = mean of absolute drawdowns
        pain = dd.abs().mean()

        # Current drawdown
        current_dd = dd.iloc[-1]

        # Average drawdown duration
        top_dd = self.top_drawdowns(20)
        avg_duration = top_dd["Duration_Days"].mean() if len(top_dd) > 0 else 0

        return {
            "Max_Drawdown_%": max_dd * 100,
            "Current_Drawdown_%": current_dd * 100,
            "Calmar_Ratio": calmar,
            "Sterling_Ratio": sterling,
            "Ulcer_Index": ulcer,
            "Pain_Index": pain,
            "Ann_Return_%": ann_return * 100,
            "Ann_Volatility_%": ann_vol * 100,
            "Avg_DD_Duration_Days": avg_duration,
        }

    # ------------------------------------------------------------------
    # 4. Drawdown-at-Risk (DaR)
    # ------------------------------------------------------------------
    def drawdown_at_risk(self, alpha: float = 0.05) -> Dict[str, float]:
        """
        Drawdown-at-Risk: the α-percentile of the drawdown distribution.
        CDaR = average drawdown beyond DaR (Conditional DaR).
        """
        dd = self.portfolio_drawdown()
        dd_values = dd.values

        dar = np.percentile(dd_values, alpha * 100)  # will be negative
        cdar = dd_values[dd_values <= dar].mean()

        return {
            "DaR": dar,
            "CDaR": cdar,
            "DaR_%": dar * 100,
            "CDaR_%": cdar * 100,
            "alpha": alpha,
        }

    # ------------------------------------------------------------------
    # 5. Underwater Plot Data
    # ------------------------------------------------------------------
    def underwater_data(self) -> pd.DataFrame:
        """Return data for underwater equity curve plot."""
        cumulative = (1 + self.portfolio_returns).cumprod()
        running_max = cumulative.cummax()
        underwater = cumulative / running_max - 1

        return pd.DataFrame(
            {
                "Cumulative": cumulative,
                "Peak": running_max,
                "Underwater": underwater,
            }
        )
