import numpy as np
import pandas as pd

from project.research.global_portfolio_risk import (
    build_portfolio_risk_report,
    build_stock_risk_metrics,
)


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        rng.normal(0.0004, 0.012, size=(220, 4)),
        index=pd.date_range("2024-01-01", periods=220, freq="B"),
        columns=["A", "B", "C", "D"],
    )


def test_stock_and_portfolio_risk_outputs_are_directionally_valid():
    returns = _returns()
    stock = build_stock_risk_metrics(returns)
    weights = pd.DataFrame(
        {
            "model_name": ["Equal Weight"] * 4,
            "ticker": ["A", "B", "C", "D"],
            "weight": [0.25, 0.25, 0.25, 0.25],
        }
    )
    report, contributions, stress, tail = build_portfolio_risk_report(returns, weights)

    assert set(["annualized_volatility", "var_95", "cvar_95"]).issubset(stock.columns)
    assert (stock["cvar_95"] <= stock["var_95"]).all()
    assert (stock["max_drawdown"] <= 0.0).all()
    assert np.isfinite(report["sharpe"]).all()
    assert report["max_drawdown"].iloc[0] <= 0.0
    assert tail["cvar_95"].iloc[0] <= tail["var_95"].iloc[0]
    assert np.isclose(contributions["risk_contribution_pct"].sum(), 1.0)
    assert {
        "equity_selloff",
        "fx_shock",
        "high_volatility_regime",
        "crypto_crash",
        "turkey_specific_shock",
        "rate_shock",
    }.issubset(set(stress["scenario"]))
