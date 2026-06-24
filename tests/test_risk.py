import numpy as np
import pandas as pd
import pytest

from project.risk.tail_risk import TailRiskAnalyzer
from project.risk.var_cvar import VaRCVaRCalculator


def test_historical_var_annual_uses_empirical_horizon_not_sqrt_scaling():
    returns = pd.DataFrame(
        {"A": [-0.01] * 252 + [0.0] * 50},
        index=pd.date_range("2024-01-01", periods=302, freq="B"),
    )
    calc = VaRCVaRCalculator(returns)

    hist = calc.historical(alpha=0.01)

    assert hist["VaR"] == pytest.approx(0.01)
    assert hist["VaR_annual"] == pytest.approx(1 - 0.99**252)


def test_tail_risk_expected_shortfall_uses_empirical_252_day_horizon():
    returns = pd.Series(
        [-0.01] * 252 + [0.0] * 50,
        index=pd.date_range("2024-01-01", periods=302, freq="B"),
    )
    analyzer = TailRiskAnalyzer(returns)

    table = analyzer.expected_shortfall_table([0.01])

    assert table.loc["99.0%", "VaR_Daily"] == pytest.approx(0.01)
    assert table.loc["99.0%", "VaR_Annual"] == pytest.approx(1 - 0.99**252)
    assert np.isfinite(table.loc["99.0%", "CVaR_Annual"])
