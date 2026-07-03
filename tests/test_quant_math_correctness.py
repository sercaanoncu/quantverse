import numpy as np
import pandas as pd

from project.research.global_portfolio_risk import (
    build_risk_metric_sanity_checks,
    evaluate_return_series,
)


def test_known_drawdown_var_and_cvar_sign_convention():
    series = pd.Series([0.10, -0.20, 0.05, -0.10, 0.02])
    metrics = evaluate_return_series(series)

    wealth = (1.0 + series).cumprod()
    expected_drawdown = float((wealth / wealth.cummax() - 1.0).min())
    expected_var = float(series.quantile(0.05))
    expected_cvar = float(series[series <= expected_var].mean())

    assert np.isclose(metrics["max_drawdown"], expected_drawdown)
    assert np.isclose(metrics["var_95"], expected_var)
    assert np.isclose(metrics["cvar_95"], expected_cvar)
    assert metrics["cvar_95"] <= metrics["var_95"]


def test_risk_metric_sanity_checks_detect_valid_report():
    report = pd.DataFrame(
        {
            "annualized_return": [0.10],
            "annualized_volatility": [0.20],
            "max_drawdown": [-0.15],
            "var_95": [-0.02],
            "cvar_95": [-0.03],
            "sharpe": [0.5],
        }
    )
    tail = pd.DataFrame({"var_95": [-0.02], "cvar_95": [-0.03]})
    checks = build_risk_metric_sanity_checks(report, tail)

    assert checks["passed"].all()
