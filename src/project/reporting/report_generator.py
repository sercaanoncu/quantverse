"""
Report Generator
==================
Combines outputs from all modules into structured reports.
Produces summary tables, key findings, and recommendations.
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generate comprehensive portfolio analysis reports.
    """

    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.sections = {}

    def load_all_data(self) -> Dict:
        """Load all module outputs."""
        data = {}
        files = {
            "returns": "returns_daily.parquet",
            "prices": "prices_clean.parquet",
            "class_map": "asset_class_map.json",
            "portfolio_weights": "portfolio_weights.parquet",
            "portfolio_summary": "portfolio_summary.parquet",
            "risk_metrics": "risk_metrics.parquet",
            "backtest_summary": "backtest_summary.parquet",
            "regime_labels": "regime_labels.parquet",
        }

        for key, filename in files.items():
            path = self.data_dir / filename
            try:
                if filename.endswith(".json"):
                    with open(path, "r") as f:
                        data[key] = json.load(f)
                elif filename.endswith(".parquet"):
                    data[key] = pd.read_parquet(path)
                logger.info(f"Loaded: {filename}")
            except FileNotFoundError:
                logger.warning(f"Not found: {filename}")
            except Exception as e:
                logger.warning(f"Error loading {filename}: {e}")

        self.data = data
        return data

    def executive_summary(self) -> str:
        """Generate executive summary text."""
        lines = []
        lines.append("=" * 80)
        lines.append("QUANTVERSE — EXECUTIVE SUMMARY")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 80)

        if "returns" in self.data:
            ret = self.data["returns"]
            lines.append(
                f"\nUniverse: {ret.shape[1]} assets, {ret.shape[0]} trading days"
            )
            lines.append(f"Period: {ret.index[0].date()} to {ret.index[-1].date()}")

        if "portfolio_summary" in self.data:
            ps = self.data["portfolio_summary"]
            lines.append(f"\nPortfolio Strategies Analyzed: {len(ps)}")
            if "Sharpe" in ps.columns:
                best = ps["Sharpe"].idxmax()
                lines.append(
                    f"Best Sharpe Ratio: {best} ({ps.loc[best, 'Sharpe']:.2f})"
                )

        if "risk_metrics" in self.data:
            rm = self.data["risk_metrics"]
            if "Max_DD_%" in rm.columns:
                safest = rm["Max_DD_%"].idxmax()  # least negative
                lines.append(
                    f"Shallowest Max Drawdown: {safest} ({rm.loc[safest, 'Max_DD_%']:.1f}%)"
                )

        if "regime_labels" in self.data:
            rl = self.data["regime_labels"]
            if "Vol_Regime" in rl.columns:
                current = rl["Vol_Regime"].iloc[-1]
                lines.append(f"\nCurrent Market Regime: {current}")

        return "\n".join(lines)

    def strategy_ranking(self) -> pd.DataFrame:
        """Rank strategies across multiple dimensions."""
        if "portfolio_summary" not in self.data:
            return pd.DataFrame()

        ps = self.data["portfolio_summary"].copy()

        # Normalize and create composite score
        ranking = pd.DataFrame(index=ps.index)

        # Higher is better
        for col in ["Return (%)", "Sharpe"]:
            if col in ps.columns:
                ranking[f"{col}_rank"] = ps[col].rank(ascending=False)

        # Lower is better
        for col in ["Volatility (%)", "HHI"]:
            if col in ps.columns:
                ranking[f"{col}_rank"] = ps[col].rank(ascending=True)

        # Composite (average rank)
        ranking["Composite_Rank"] = ranking.mean(axis=1)
        ranking = ranking.sort_values("Composite_Rank")

        return ranking

    def key_findings(self) -> List[str]:
        """Generate key findings across all modules."""
        findings = []

        if "portfolio_summary" in self.data:
            ps = self.data["portfolio_summary"]
            if "Sharpe" in ps.columns:
                best_sharpe = ps["Sharpe"].max()
                worst_sharpe = ps["Sharpe"].min()
                findings.append(
                    f"Sharpe ratio ranges from {worst_sharpe:.2f} to {best_sharpe:.2f} "
                    f"across strategies — estimator and method choice matters significantly."
                )

        if "risk_metrics" in self.data:
            rm = self.data["risk_metrics"]
            if "CVaR_5%" in rm.columns:
                max_cvar = rm["CVaR_5%"].max()
                min_cvar = rm["CVaR_5%"].min()
                findings.append(
                    f"Daily CVaR(5%) varies from {min_cvar:.3f}% to {max_cvar:.3f}% — "
                    f"tail risk is highly strategy-dependent."
                )

        if "backtest_summary" in self.data:
            bs = self.data["backtest_summary"]
            if "Sharpe" in bs.columns:
                best_oos = bs["Sharpe"].idxmax()
                findings.append(
                    f"Walk-forward out-of-sample: {best_oos} achieves highest Sharpe "
                    f"({bs.loc[best_oos, 'Sharpe']:.2f}), confirming robustness."
                )

        # Data-driven findings only — no hard-coded claims
        if "backtest_summary" in self.data:
            bs = self.data["backtest_summary"]
            if "Sharpe" in bs.columns and len(bs) > 1:
                simple = ["Equal Weight", "Inverse Vol", "Inv Volatility"]
                complex_strats = ["Max Sharpe", "Min Variance"]
                simple_avg = bs.loc[bs.index.isin(simple), "Sharpe"].mean()
                complex_avg = bs.loc[bs.index.isin(complex_strats), "Sharpe"].mean()
                if not np.isnan(simple_avg) and not np.isnan(complex_avg):
                    if simple_avg > complex_avg:
                        findings.append(
                            f"Out-of-sample data shows simpler strategies (avg Sharpe: {simple_avg:.2f}) "
                            f"outperformed complex optimizations (avg Sharpe: {complex_avg:.2f}) "
                            f"in this sample period. This is consistent with the well-documented "
                            f"estimation error sensitivity of mean-variance optimization."
                        )
                    else:
                        findings.append(
                            f"Complex strategies (avg Sharpe: {complex_avg:.2f}) outperformed "
                            f"simpler approaches (avg Sharpe: {simple_avg:.2f}) out-of-sample, "
                            f"suggesting estimation quality was sufficient for this period."
                        )

        return findings

    def generate_text_report(self) -> str:
        """Generate full text report."""
        self.load_all_data()

        sections = []
        sections.append(self.executive_summary())

        # Key Findings
        sections.append("\n" + "=" * 80)
        sections.append("KEY FINDINGS")
        sections.append("=" * 80)
        for i, finding in enumerate(self.key_findings(), 1):
            sections.append(f"\n{i}. {finding}")

        # Strategy Ranking
        ranking = self.strategy_ranking()
        if len(ranking) > 0:
            sections.append("\n" + "=" * 80)
            sections.append("STRATEGY RANKING (Composite)")
            sections.append("=" * 80)
            sections.append(ranking.round(1).to_string())

        # Portfolio Summary
        if "portfolio_summary" in self.data:
            sections.append("\n" + "=" * 80)
            sections.append("PORTFOLIO SUMMARY")
            sections.append("=" * 80)
            sections.append(self.data["portfolio_summary"].round(3).to_string())

        # Risk Metrics
        if "risk_metrics" in self.data:
            sections.append("\n" + "=" * 80)
            sections.append("RISK METRICS")
            sections.append("=" * 80)
            sections.append(self.data["risk_metrics"].round(4).to_string())

        # Backtest
        if "backtest_summary" in self.data:
            sections.append("\n" + "=" * 80)
            sections.append("WALK-FORWARD BACKTEST")
            sections.append("=" * 80)
            sections.append(self.data["backtest_summary"].round(4).to_string())

        return "\n".join(sections)
