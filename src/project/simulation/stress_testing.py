"""
Stress Testing
================
Apply historical and hypothetical stress scenarios to portfolios.
Measures impact of extreme market events on portfolio value.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field

from project.portfolio_contract import align_portfolio_weights

logger = logging.getLogger(__name__)


@dataclass
class StressScenario:
    """Definition of a stress test scenario."""

    name: str
    description: str
    shocks: Dict[str, float]  # {asset_class_or_ticker: shock_pct}
    duration_days: int = 1  # over how many days the shock unfolds
    correlation_override: Optional[float] = None  # force correlation to this level


class StressTester:
    """
    Apply stress scenarios to portfolios and measure impact.

    Three modes:
    1. Historical: replay actual crisis periods
    2. Hypothetical: user-defined factor shocks
    3. Reverse: find what shock would cause a given loss
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        prices: pd.DataFrame,
        weights: pd.Series,
        asset_class_map: Dict[str, str],
    ):
        self.returns = returns.dropna()
        if self.returns.empty:
            raise ValueError("Stress-test return history is empty")
        self.prices = prices
        self.tickers = list(returns.columns)
        self.weights = align_portfolio_weights(
            weights,
            self.tickers,
            context="Stress-test portfolio",
        )
        self.asset_class_map = asset_class_map
        self.port_returns = pd.Series(
            self.returns.values @ self.weights.values, index=self.returns.index
        )

    # ------------------------------------------------------------------
    # 1. Historical Scenario Replay
    # ------------------------------------------------------------------
    def historical_scenarios(self) -> pd.DataFrame:
        """
        Replay known crisis periods and measure portfolio impact.

        Automatically detects available date ranges in the data.
        """
        scenarios = {
            "COVID Crash": ("2020-02-19", "2020-03-23"),
            "COVID Recovery": ("2020-03-23", "2020-06-08"),
            "2020 Q4 Rally": ("2020-10-01", "2020-12-31"),
            "2021 Crypto Crash": ("2021-05-10", "2021-06-22"),
            "2021 Meme Stock Era": ("2021-01-15", "2021-02-15"),
            "2022 Rate Hike Selloff": ("2022-01-03", "2022-06-16"),
            "2022 Crypto Winter": ("2022-04-01", "2022-06-30"),
            "2022 UK Gilt Crisis": ("2022-09-20", "2022-10-14"),
            "2022 Q4 Recovery": ("2022-10-12", "2022-12-31"),
            "2023 Banking Crisis": ("2023-03-01", "2023-03-24"),
            "2023 Bond Rout": ("2023-07-18", "2023-10-19"),
            "2024 Yen Carry Unwind": ("2024-07-10", "2024-08-05"),
            "2024 Q4 Trump Trade": ("2024-10-01", "2024-12-31"),
        }

        results = []
        for name, (start, end) in scenarios.items():
            try:
                start_dt = pd.Timestamp(start)
                end_dt = pd.Timestamp(end)

                # Check data availability
                if start_dt < self.returns.index[0] or end_dt > self.returns.index[-1]:
                    continue

                period_ret = self.returns.loc[start_dt:end_dt]
                if len(period_ret) < 2:
                    continue

                # Portfolio cumulative return
                port_cum = (1 + period_ret.values @ self.weights.values).cumprod()
                port_total = port_cum[-1] - 1

                # Asset class returns
                ac_returns = {}
                for ac in set(self.asset_class_map.values()):
                    if ac == "signals":
                        continue
                    tickers = [
                        t
                        for t, c in self.asset_class_map.items()
                        if c == ac and t in self.tickers
                    ]
                    if tickers:
                        w_ac = self.weights[tickers]
                        if w_ac.sum() > 0:
                            ac_ret = period_ret[tickers].values @ (
                                w_ac.values / max(w_ac.sum(), 1e-10)
                            )
                            ac_returns[ac] = (np.cumprod(1 + ac_ret)[-1] - 1) * 100

                # Max drawdown during scenario
                cum = np.cumprod(1 + period_ret.values @ self.weights.values)
                running_peak = np.maximum(np.maximum.accumulate(cum), 1.0)
                dd = cum / running_peak - 1
                max_dd = dd.min()

                result = {
                    "Scenario": name,
                    "Start": start,
                    "End": end,
                    "Days": len(period_ret),
                    "Portfolio_Return_%": port_total * 100,
                    "Max_DD_%": max_dd * 100,
                }
                result.update({f"{k}_Return_%": v for k, v in ac_returns.items()})
                results.append(result)

            except Exception as e:
                logger.warning(f"Scenario '{name}' failed: {e}")

        df = pd.DataFrame(results).set_index("Scenario")
        return df

    # ------------------------------------------------------------------
    # 2. Hypothetical Factor Shocks
    # ------------------------------------------------------------------
    def hypothetical_shock(self, scenario: StressScenario) -> Dict:
        """
        Apply hypothetical shocks to the portfolio.

        Shocks can be applied at asset or asset-class level.
        """
        shocked_returns = {}

        for ticker in self.tickers:
            ac = self.asset_class_map.get(ticker, "unknown")
            shock = 0.0

            # Check for direct ticker shock
            if ticker in scenario.shocks:
                shock = scenario.shocks[ticker]
            # Check for asset class shock
            elif ac in scenario.shocks:
                shock = scenario.shocks[ac]

            shocked_returns[ticker] = shock / scenario.duration_days

        # Portfolio shock
        daily_shocks = pd.Series(shocked_returns)
        port_shock = (self.weights * daily_shocks).sum()
        total_shock = 0
        for ticker in self.tickers:
            ac = self.asset_class_map.get(ticker, "unknown")
            s = scenario.shocks.get(ticker, scenario.shocks.get(ac, 0))
            total_shock += self.weights[ticker] * s

        # Contribution breakdown
        contributions = {}
        for ac in set(self.asset_class_map.values()):
            if ac == "signals":
                continue
            tickers = [
                t
                for t, c in self.asset_class_map.items()
                if c == ac and t in self.tickers
            ]
            ac_shock = sum(
                self.weights[t] * scenario.shocks.get(t, scenario.shocks.get(ac, 0))
                for t in tickers
            )
            contributions[ac] = ac_shock * 100

        return {
            "scenario": scenario.name,
            "description": scenario.description,
            "portfolio_impact_%": total_shock * 100,
            "duration_days": scenario.duration_days,
            "contributions": contributions,
        }

    # ------------------------------------------------------------------
    # 3. Predefined Stress Scenarios
    # ------------------------------------------------------------------
    def get_predefined_scenarios(self) -> List[StressScenario]:
        """Return a set of standard stress test scenarios."""
        return [
            StressScenario(
                name="Equity Crash (-30%)",
                description="Global equity markets crash 30%, flight to quality",
                shocks={
                    "us_equity_sectors": -0.30,
                    "international_equity": -0.35,
                    "crypto": -0.50,
                    "commodities": -0.15,
                    "fixed_income": 0.05,
                    "reits": -0.25,
                },
                duration_days=30,
            ),
            StressScenario(
                name="Rate Shock (+300bps)",
                description="Sudden rate hike, bonds sell off, equities drop",
                shocks={
                    "us_equity_sectors": -0.15,
                    "international_equity": -0.20,
                    "crypto": -0.10,
                    "commodities": -0.05,
                    "fixed_income": -0.20,
                    "reits": -0.20,
                },
                duration_days=60,
            ),
            StressScenario(
                name="Crypto Winter (-70%)",
                description="Crypto collapse, minor equity impact",
                shocks={
                    "us_equity_sectors": -0.05,
                    "international_equity": -0.05,
                    "crypto": -0.70,
                    "commodities": 0.0,
                    "fixed_income": 0.02,
                    "reits": -0.03,
                },
                duration_days=90,
            ),
            StressScenario(
                name="Stagflation",
                description="High inflation + low growth, commodities surge",
                shocks={
                    "us_equity_sectors": -0.20,
                    "international_equity": -0.25,
                    "crypto": -0.15,
                    "commodities": 0.25,
                    "fixed_income": -0.15,
                    "reits": -0.15,
                },
                duration_days=120,
            ),
            StressScenario(
                name="Flight to Quality",
                description="Risk-off: equities down, treasuries and gold up",
                shocks={
                    "us_equity_sectors": -0.15,
                    "international_equity": -0.20,
                    "crypto": -0.25,
                    "commodities": 0.10,  # gold up
                    "fixed_income": 0.10,
                    "reits": -0.10,
                },
                duration_days=30,
            ),
            StressScenario(
                name="Everything Rally",
                description="Liquidity-driven rally across all assets",
                shocks={
                    "us_equity_sectors": 0.20,
                    "international_equity": 0.15,
                    "crypto": 0.40,
                    "commodities": 0.10,
                    "fixed_income": 0.05,
                    "reits": 0.15,
                },
                duration_days=60,
            ),
        ]

    def run_all_hypothetical(self) -> pd.DataFrame:
        """Run all predefined hypothetical stress scenarios."""
        scenarios = self.get_predefined_scenarios()
        results = []
        for scenario in scenarios:
            r = self.hypothetical_shock(scenario)
            row = {
                "Scenario": r["scenario"],
                "Description": r["description"],
                "Portfolio_Impact_%": r["portfolio_impact_%"],
                "Duration_Days": r["duration_days"],
            }
            row.update({f"{k}_%": v for k, v in r["contributions"].items()})
            results.append(row)

        return pd.DataFrame(results).set_index("Scenario")

    # ------------------------------------------------------------------
    # 4. Reverse Stress Test
    # ------------------------------------------------------------------
    def reverse_stress(
        self, target_loss: float = -0.20, n_worst: int = 10
    ) -> pd.DataFrame:
        """
        Reverse stress test: find historical periods where the portfolio
        would have lost at least |target_loss|.

        Parameters
        ----------
        target_loss : float
            Target cumulative loss (e.g., -0.20 = 20% loss)
        n_worst : int
            Number of worst periods to return
        """
        # Rolling cumulative returns at various windows
        windows = [5, 10, 21, 42, 63, 126, 252]
        worst_periods = []

        for w in windows:
            if w >= len(self.port_returns):
                continue
            rolling_cum = self.port_returns.rolling(w).apply(
                lambda x: (1 + x).prod() - 1, raw=True
            )
            # Find periods below target
            bad = rolling_cum[rolling_cum <= target_loss]
            for date, ret in bad.items():
                worst_periods.append(
                    {
                        "End_Date": date,
                        "Window_Days": w,
                        "Cumulative_Return_%": ret * 100,
                        "Start_Date": date - pd.Timedelta(days=int(w * 1.5)),
                    }
                )

        df = pd.DataFrame(worst_periods)
        if len(df) > 0:
            df = (
                df.sort_values("Cumulative_Return_%")
                .head(n_worst)
                .reset_index(drop=True)
            )
        return df
