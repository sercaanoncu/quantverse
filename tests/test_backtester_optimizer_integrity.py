import numpy as np
import pandas as pd
import pytest

from project.backtest.backtester import PortfolioBacktester


def _returns(rows=40):
    rng = np.random.default_rng(17)
    return pd.DataFrame(
        rng.normal(0.0005, 0.01, size=(rows, 4)),
        index=pd.bdate_range("2025-01-02", periods=rows),
        columns=["A", "B", "C", "D"],
    )


def test_walk_forward_records_optimizer_failure_instead_of_hiding_it():
    returns = _returns()
    backtester = PortfolioBacktester(
        returns,
        {ticker: "equity" for ticker in returns.columns},
        max_position_weight=0.50,
    )

    def failed_optimizer(_train):
        raise RuntimeError("synthetic failure")

    result = backtester.walk_forward(
        failed_optimizer,
        train_window=20,
        rebal_frequency=10,
    )

    assert result["optimizer_failure_count"] == 2
    assert result["optimization_status"] == (
        "diagnostic_previous_weights_carried_forward"
    )
    assert all(
        "synthetic failure" in failure["reason"]
        for failure in result["optimizer_failures"]
    )


def test_hrp_failure_is_not_silently_relabelled_as_inverse_volatility(monkeypatch):
    from project.optimization import hierarchical

    def fail(_self, method="single"):
        raise RuntimeError(f"failed {method}")

    monkeypatch.setattr(hierarchical.HRPOptimizer, "optimize", fail)

    with pytest.raises(RuntimeError, match="failed single"):
        PortfolioBacktester.hrp_optimizer(_returns())
