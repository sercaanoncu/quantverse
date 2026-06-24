"""
Performance Attribution
========================
Decompose portfolio performance into allocation, selection,
and interaction effects using Brinson-Fachler framework.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class PerformanceAttribution:
    """
    Multi-level performance attribution.

    1. Brinson-Fachler: allocation + selection + interaction
    2. Asset-level contribution
    3. Rolling attribution windows
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        portfolio_weights: pd.Series,
        benchmark_weights: pd.Series,
        asset_class_map: Dict[str, str],
    ):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)
        self.port_w = portfolio_weights.reindex(self.tickers).fillna(0)
        self.bench_w = benchmark_weights.reindex(self.tickers).fillna(0)
        self.class_map = asset_class_map

    # ------------------------------------------------------------------
    # 1. Asset-Level Return Contribution
    # ------------------------------------------------------------------
    def asset_contribution(self, period: Optional[str] = None) -> pd.DataFrame:
        """
        Decompose total return into asset-level contributions.

        Contribution_i = w_i × r_i
        """
        if period:
            ret = self.returns.loc[period]
        else:
            ret = self.returns

        # Cumulative returns per asset
        cum_ret = (1 + ret).prod() - 1

        port_contrib = self.port_w * cum_ret
        bench_contrib = self.bench_w * cum_ret
        active_contrib = port_contrib - bench_contrib

        return pd.DataFrame(
            {
                "Port_Weight_%": self.port_w * 100,
                "Bench_Weight_%": self.bench_w * 100,
                "Active_Weight_%": (self.port_w - self.bench_w) * 100,
                "Asset_Return_%": cum_ret * 100,
                "Port_Contribution_%": port_contrib * 100,
                "Bench_Contribution_%": bench_contrib * 100,
                "Active_Contribution_%": active_contrib * 100,
                "Asset_Class": [self.class_map.get(t, "unknown") for t in self.tickers],
            },
            index=self.tickers,
        ).sort_values("Active_Contribution_%", ascending=False)

    # ------------------------------------------------------------------
    # 2. Brinson-Fachler Attribution (Sector Level)
    # ------------------------------------------------------------------
    def brinson_fachler(self) -> pd.DataFrame:
        """
        Brinson-Fachler attribution at asset class level.

        Allocation Effect:  (w_p,s - w_b,s) × (R_b,s - R_b)
        Selection Effect:   w_b,s × (R_p,s - R_b,s)
        Interaction Effect:  (w_p,s - w_b,s) × (R_p,s - R_b,s)

        Total Active = Allocation + Selection + Interaction
        """
        cum_ret = (1 + self.returns).prod() - 1

        # Benchmark total return
        bench_total = (self.bench_w * cum_ret).sum()

        classes = sorted(set(self.class_map.values()) - {"signals"})
        rows = []

        for ac in classes:
            tickers = [
                t for t, c in self.class_map.items() if c == ac and t in self.tickers
            ]
            if not tickers:
                continue

            # Sector weights
            w_p = self.port_w[tickers].sum()
            w_b = self.bench_w[tickers].sum()

            # Sector returns (weighted average within sector)
            if w_p > 0:
                r_p = (self.port_w[tickers] * cum_ret[tickers]).sum() / w_p
            else:
                r_p = 0
            if w_b > 0:
                r_b = (self.bench_w[tickers] * cum_ret[tickers]).sum() / w_b
            else:
                r_b = cum_ret[tickers].mean() if len(tickers) > 0 else 0

            # Brinson-Fachler decomposition
            allocation = (w_p - w_b) * (r_b - bench_total)
            selection = w_b * (r_p - r_b)
            interaction = (w_p - w_b) * (r_p - r_b)
            total = allocation + selection + interaction

            rows.append(
                {
                    "Asset_Class": ac,
                    "Port_Weight_%": w_p * 100,
                    "Bench_Weight_%": w_b * 100,
                    "Port_Return_%": r_p * 100,
                    "Bench_Return_%": r_b * 100,
                    "Allocation_%": allocation * 100,
                    "Selection_%": selection * 100,
                    "Interaction_%": interaction * 100,
                    "Total_Active_%": total * 100,
                }
            )

        df = pd.DataFrame(rows).set_index("Asset_Class")

        # Add totals row
        totals = df[
            ["Allocation_%", "Selection_%", "Interaction_%", "Total_Active_%"]
        ].sum()
        totals["Port_Weight_%"] = self.port_w.sum() * 100
        totals["Bench_Weight_%"] = self.bench_w.sum() * 100
        totals["Port_Return_%"] = (self.port_w * cum_ret).sum() * 100
        totals["Bench_Return_%"] = bench_total * 100
        df.loc["TOTAL"] = totals

        return df

    # ------------------------------------------------------------------
    # 3. Rolling Attribution
    # ------------------------------------------------------------------
    def rolling_contribution(self, window: int = 63) -> pd.DataFrame:
        """
        Rolling window asset class contribution to portfolio returns.

        Parameters
        ----------
        window : int
            Rolling window in trading days (63 ≈ 3 months)
        """
        classes = sorted(set(self.class_map.values()) - {"signals"})
        rolling_contrib = {ac: [] for ac in classes}
        dates = []

        for i in range(window, len(self.returns)):
            sub = self.returns.iloc[i - window : i]
            cum_ret = (1 + sub).prod() - 1
            dates.append(self.returns.index[i])

            for ac in classes:
                tickers = [
                    t
                    for t, c in self.class_map.items()
                    if c == ac and t in self.tickers
                ]
                if tickers:
                    contrib = (self.port_w[tickers] * cum_ret[tickers]).sum()
                    rolling_contrib[ac].append(contrib * 100)
                else:
                    rolling_contrib[ac].append(0)

        return pd.DataFrame(rolling_contrib, index=dates)

    # ------------------------------------------------------------------
    # 4. Monthly Return Table
    # ------------------------------------------------------------------
    def monthly_returns(self) -> pd.DataFrame:
        """
        Generate monthly return table (months as columns, years as rows).
        Classic format for performance reporting.
        """
        port_daily = pd.Series(
            self.returns.values @ self.port_w.values, index=self.returns.index
        )
        monthly = port_daily.resample("ME").apply(lambda x: (1 + x).prod() - 1)

        table = pd.DataFrame(index=sorted(monthly.index.year.unique()))
        for month in range(1, 13):
            month_name = pd.Timestamp(2000, month, 1).strftime("%b")
            vals = monthly[monthly.index.month == month]
            table[month_name] = (
                vals.values[: len(table)]
                if len(vals) >= len(table)
                else pd.Series(vals.values, index=vals.index.year).reindex(table.index)
            )

        # Annual returns
        yearly = port_daily.resample("YE").apply(lambda x: (1 + x).prod() - 1)
        table["Year"] = (
            yearly.values[: len(table)]
            if len(yearly) >= len(table)
            else pd.Series(yearly.values, index=yearly.index.year).reindex(table.index)
        )

        return table * 100  # in percent

    # ------------------------------------------------------------------
    # 5. Tracking Error Analysis
    # ------------------------------------------------------------------
    def tracking_error_analysis(self) -> Dict:
        """Compute tracking error and information ratio vs benchmark."""
        port_ret = self.returns.values @ self.port_w.values
        bench_ret = self.returns.values @ self.bench_w.values

        active = port_ret - bench_ret
        te = np.std(active) * np.sqrt(252)
        ir = np.mean(active) * 252 / te if te > 1e-8 else 0

        active_series = pd.Series(active, index=self.returns.index)
        rolling_te = active_series.rolling(63).std() * np.sqrt(252)

        return {
            "tracking_error": te,
            "information_ratio": ir,
            "active_return": np.mean(active) * 252,
            "rolling_te": rolling_te,
            "active_returns": active_series,
        }
