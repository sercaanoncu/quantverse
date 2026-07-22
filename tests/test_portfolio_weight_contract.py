import numpy as np
import pandas as pd
import pytest

from project.portfolio_contract import align_portfolio_weights
from project.risk.drawdown import DrawdownAnalyzer
from project.risk.factor_risk import FactorRiskDecomposer


def test_weight_contract_aligns_omitted_zero_weight_assets():
    aligned = align_portfolio_weights(
        pd.Series({"A": 0.6, "B": 0.4}),
        ["A", "B", "C"],
    )

    assert aligned.to_dict() == {"A": 0.6, "B": 0.4, "C": 0.0}


@pytest.mark.parametrize(
    "weights, message",
    [
        (pd.Series([0.5, 0.5], index=["A", "A"]), "duplicate tickers"),
        (pd.Series({"A": 0.8, "MISSING": 0.2}), "missing from returns"),
        (pd.Series({"A": 0.7, "B": 0.2}), "sum to 1"),
        (pd.Series({"A": np.nan, "B": 1.0}), "finite"),
    ],
)
def test_weight_contract_rejects_invalid_portfolios(weights, message):
    with pytest.raises(ValueError, match=message):
        align_portfolio_weights(weights, ["A", "B"])


def test_drawdown_analyzer_uses_shared_weight_contract():
    returns = pd.DataFrame(
        {"A": [0.01, -0.02], "B": [0.0, 0.01]},
        index=pd.bdate_range("2025-01-02", periods=2),
    )

    with pytest.raises(ValueError, match="missing from returns"):
        DrawdownAnalyzer(
            returns,
            pd.Series({"A": 0.4, "B": 0.4, "MISSING": 0.2}),
        )


def test_factor_risk_fails_safely_for_zero_volatility_portfolio():
    returns = pd.DataFrame(
        0.0,
        index=pd.bdate_range("2025-01-02", periods=20),
        columns=["A", "B"],
    )
    decomposer = FactorRiskDecomposer(
        returns,
        pd.Series({"A": 0.5, "B": 0.5}),
    )

    with pytest.raises(ValueError, match="undefined"):
        decomposer.marginal_risk_contribution()
