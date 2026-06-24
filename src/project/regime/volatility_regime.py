"""
Volatility Regime Detection
==============================
Simple but effective regime detection based on
realized volatility thresholds and percentiles.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class VolatilityRegimeDetector:
    """
    Rule-based volatility regime classification.

    Simple and interpretable: uses rolling volatility percentiles
    to classify market environment.
    """

    def __init__(self, returns: pd.DataFrame):
        self.returns = returns.dropna()
        self.tickers = list(returns.columns)

    def detect(
        self,
        port_returns: pd.Series,
        vol_window: int = 21,
        lookback: int = 252,
        low_pct: float = 33,
        high_pct: float = 67,
    ) -> pd.DataFrame:
        """
        Classify each day into a volatility regime.

        Parameters
        ----------
        vol_window : int
            Rolling window for realized volatility (21 = 1 month)
        lookback : int
            Lookback for percentile ranking (252 = 1 year)
        low_pct : float
            Percentile below which = Low Vol regime
        high_pct : float
            Percentile above which = High Vol regime
        """
        vol = port_returns.rolling(vol_window).std() * np.sqrt(252)
        vol_pctile = vol.rolling(lookback).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100
        )

        regimes = pd.Series("Medium Vol", index=port_returns.index, name="Regime")
        regimes[vol_pctile <= low_pct] = "Low Vol"
        regimes[vol_pctile >= high_pct] = "High Vol"

        result = pd.DataFrame(
            {
                "Regime": regimes,
                "Realized_Vol": vol,
                "Vol_Percentile": vol_pctile,
            }
        )

        self.result = result.dropna()
        self._compute_stats(port_returns)
        return self.result

    def _compute_stats(self, port_returns: pd.Series):
        """Compute per-regime statistics."""
        aligned = port_returns.reindex(self.result.index)
        stats = {}
        for regime in ["Low Vol", "Medium Vol", "High Vol"]:
            mask = self.result["Regime"] == regime
            r = aligned[mask]
            if len(r) > 0:
                stats[regime] = {
                    "mean_return_ann": r.mean() * 252,
                    "volatility_ann": r.std() * np.sqrt(252),
                    "sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0,
                    "n_days": mask.sum(),
                    "pct_time": mask.mean() * 100,
                    "avg_vol": self.result.loc[mask, "Realized_Vol"].mean(),
                }
        self.regime_stats = stats

    def get_regime_summary(self) -> pd.DataFrame:
        return pd.DataFrame(self.regime_stats).T

    def current_regime(self) -> str:
        return self.result["Regime"].iloc[-1]

    def regime_transition_matrix(self) -> pd.DataFrame:
        """Empirical transition probabilities between regimes."""
        regimes = self.result["Regime"]
        labels = ["Low Vol", "Medium Vol", "High Vol"]
        n = len(labels)
        trans = np.zeros((n, n))

        for i in range(1, len(regimes)):
            from_idx = labels.index(regimes.iloc[i - 1])
            to_idx = labels.index(regimes.iloc[i])
            trans[from_idx, to_idx] += 1

        # Normalize rows
        row_sums = trans.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        trans = trans / row_sums

        return pd.DataFrame(trans, index=labels, columns=labels)
