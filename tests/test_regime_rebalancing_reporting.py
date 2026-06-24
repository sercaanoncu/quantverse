import numpy as np
import pandas as pd

from project.backtest.rebalancing import RebalancingEngine, TransactionCosts
from project.regime.adaptive_allocator import AdaptiveAllocator
from project.regime.clustering_regime import ClusteringRegimeDetector
from project.reporting.report_generator import ReportGenerator


def _returns(n_days=130, n_assets=4):
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        rng.normal(0.0002, 0.01, size=(n_days, n_assets)),
        index=pd.date_range("2024-01-01", periods=n_days, freq="B"),
        columns=[f"A{i}" for i in range(n_assets)],
    )


def test_clustering_regime_supports_more_than_three_regimes():
    returns = _returns(n_assets=5)
    port_returns = returns.mean(axis=1)

    detector = ClusteringRegimeDetector(returns, n_regimes=4).fit(port_returns)
    regimes = detector.get_regime_series()

    assert len(regimes) > 0
    assert detector.current_regime() in set(regimes)


def test_optimized_adaptive_allocator_uses_min_variance_for_high_vol_regime():
    class SpyAllocator(AdaptiveAllocator):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.strategies = []

        def optimize_for_regime(self, regime_returns, strategy="min_variance"):
            self.strategies.append(strategy)
            return pd.Series(1.0 / self.n_assets, index=self.tickers)

    returns = _returns(n_assets=4)
    class_map = {ticker: "us_equity_sectors" for ticker in returns.columns}
    regimes = pd.Series("High Vol (Bear)", index=returns.index)
    allocator = SpyAllocator(returns, class_map)

    allocator.adaptive_backtest(regimes, mode="optimized", rebal_frequency=21)

    assert allocator.strategies
    assert allocator.strategies[0] == "min_variance"


def test_rebalancing_period_end_dates_are_actual_observed_dates():
    returns = pd.DataFrame(
        {
            "A": np.zeros(55),
            "B": np.zeros(55),
        },
        index=pd.date_range("2024-01-01", periods=55, freq="B"),
    )
    target = pd.Series({"A": 0.5, "B": 0.5})
    engine = RebalancingEngine(
        returns,
        target,
        costs=TransactionCosts(proportional=0, spread=0, fixed_per_trade=0),
    )

    period_ends = engine._period_end_dates("ME")

    assert pd.Timestamp("2024-01-31") in period_ends
    assert pd.Timestamp("2024-02-29") in period_ends
    assert returns.index[-1] in period_ends


def test_report_generator_loads_from_explicit_data_dir(tmp_path):
    returns = pd.DataFrame(
        {"A": [0.01, -0.01]}, index=pd.date_range("2024-01-01", periods=2)
    )
    returns.to_parquet(tmp_path / "returns_daily.parquet")

    generator = ReportGenerator(data_dir=str(tmp_path))
    data = generator.load_all_data()

    assert "returns" in data
    assert data["returns"].equals(returns)
