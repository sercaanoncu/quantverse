import numpy as np
import pandas as pd
import pytest

from project.backtest.metrics import PerformanceMetrics
from project.reporting.tearsheet import TearsheetGenerator


def _dated(values):
    return pd.Series(
        values,
        index=pd.bdate_range("2025-01-02", periods=len(values)),
        dtype=float,
    )


def test_tearsheet_sharpe_and_sortino_use_arithmetic_excess_return():
    returns = _dated([0.01, -0.005, 0.004, -0.002, 0.006, 0.001])
    annual_risk_free = 0.04
    metrics = TearsheetGenerator(
        returns,
        risk_free_rate=annual_risk_free,
    )._compute_metrics()

    rf_daily = (1 + annual_risk_free) ** (1 / 252) - 1
    excess = returns - rf_daily
    expected_sharpe = excess.mean() / returns.std() * np.sqrt(252)
    downside = np.minimum(excess, 0.0)
    expected_sortino = (
        excess.mean() * 252 / (np.sqrt(np.mean(downside**2)) * np.sqrt(252))
    )

    assert float(metrics["Sharpe Ratio"]) == pytest.approx(expected_sharpe, abs=0.005)
    assert float(metrics["Sortino Ratio"]) == pytest.approx(expected_sortino, abs=0.005)
    assert "VaR Loss (5%)" in metrics
    assert "CVaR Loss (5%)" in metrics


def test_tearsheet_does_not_treat_missing_benchmark_returns_as_zero():
    returns = _dated([0.01, 0.02, -0.01, 0.005])
    benchmark = pd.Series(
        [0.004],
        index=[returns.index[0]],
        dtype=float,
    )

    tearsheet = TearsheetGenerator(returns, benchmark=benchmark)
    metrics = tearsheet._compute_metrics()

    assert len(tearsheet.bench_cum) == 1
    assert metrics["Beta"] == "N/A (insufficient overlap)"
    assert metrics["Information Ratio"] == "N/A (insufficient overlap)"


def test_performance_metrics_relative_statistics_use_only_common_dates():
    returns = _dated([0.01, 0.02, -0.01, 0.005])
    benchmark = pd.Series(
        [0.004, 0.006],
        index=[returns.index[0], returns.index[2]],
        dtype=float,
    )
    metrics = PerformanceMetrics(returns, risk_free_rate=0.0)
    aligned = pd.DataFrame({"portfolio": returns, "benchmark": benchmark}).dropna()
    active = aligned["portfolio"] - aligned["benchmark"]
    expected_information_ratio = active.mean() * 252 / (active.std() * np.sqrt(252))

    assert metrics.information_ratio(benchmark) == pytest.approx(
        expected_information_ratio
    )
    assert np.isfinite(metrics.alpha_jensen(benchmark))
