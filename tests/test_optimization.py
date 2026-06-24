import numpy as np
import pandas as pd
import pytest

from project.optimization.constraints import PortfolioConstraints
from project.optimization.cvar_optimization import CVaROptimizer
from project.optimization.hierarchical import HRPOptimizer
from project.optimization.mean_variance import MeanVarianceOptimizer
from project.optimization.risk_parity import RiskParityOptimizer


def _sample_returns(n_days=120, n_assets=6):
    rng = np.random.default_rng(123)
    data = rng.normal(0.0004, 0.01, size=(n_days, n_assets))
    return pd.DataFrame(
        data,
        index=pd.date_range("2024-01-01", periods=n_days, freq="B"),
        columns=[f"A{i}" for i in range(n_assets)],
    )


def test_mean_variance_rejects_infeasible_position_caps():
    tickers = ["A", "B", "C"]
    mu = pd.Series([0.08, 0.09, 0.10], index=tickers)
    cov = pd.DataFrame(np.eye(3) * 0.04, index=tickers, columns=tickers)
    optimizer = MeanVarianceOptimizer(mu, cov)

    with pytest.raises(ValueError, match="Infeasible portfolio constraints"):
        optimizer.minimum_variance(
            PortfolioConstraints.default_long_only(max_weight=0.20)
        )


def test_mean_variance_rejects_misaligned_inputs():
    mu = pd.Series([0.08, 0.09], index=["A", "B"])
    cov = pd.DataFrame(np.eye(2), index=["B", "A"], columns=["B", "A"])

    with pytest.raises(ValueError, match="labels must match"):
        MeanVarianceOptimizer(mu, cov)


def test_cvar_rejects_misaligned_expected_returns():
    returns = _sample_returns(n_assets=3)
    expected = pd.Series([0.08, 0.09, 0.10], index=["A1", "A0", "A2"])

    with pytest.raises(ValueError, match="Expected return labels"):
        CVaROptimizer(returns, expected_returns=expected)


def test_hrp_respects_configured_max_weight_after_projection():
    returns = _sample_returns(n_assets=6)
    optimizer = HRPOptimizer(returns)

    result = optimizer.optimize(
        constraints=PortfolioConstraints.default_long_only(max_weight=0.25)
    )

    assert result["weights"].sum() == pytest.approx(1.0)
    assert result["weights"].max() <= 0.2501


def test_risk_parity_rejects_misaligned_expected_returns():
    cov = pd.DataFrame(np.eye(2), index=["A", "B"], columns=["A", "B"])
    expected = pd.Series([0.08, 0.09], index=["B", "A"])

    with pytest.raises(ValueError, match="Expected return labels"):
        RiskParityOptimizer(cov, expected_returns=expected)
