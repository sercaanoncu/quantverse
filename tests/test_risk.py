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


def test_parametric_and_monte_carlo_do_not_fake_annual_var_with_sqrt_time():
    returns = pd.DataFrame(
        {"A": np.linspace(-0.02, 0.02, 300)},
        index=pd.date_range("2024-01-01", periods=300, freq="B"),
    )
    calc = VaRCVaRCalculator(returns)

    parametric = calc.parametric()
    monte_carlo = calc.monte_carlo(n_sims=100, horizon=5)

    assert np.isnan(parametric["VaR_annual"])
    assert np.isnan(parametric["CVaR_annual"])
    assert np.isnan(monte_carlo["VaR_annual"])
    assert np.isnan(monte_carlo["CVaR_annual"])
    assert parametric["annualization_status"] == (
        "not_reported_no_model_free_sqrt_time_scaling"
    )


def test_var_calculator_rejects_weight_for_missing_return_series():
    returns = pd.DataFrame(
        {"A": [0.01, -0.01], "B": [0.0, 0.01]},
        index=pd.date_range("2024-01-01", periods=2, freq="B"),
    )

    with pytest.raises(ValueError, match="missing from returns"):
        VaRCVaRCalculator(
            returns,
            weights=pd.Series({"A": 0.4, "B": 0.4, "MISSING": 0.2}),
        )
