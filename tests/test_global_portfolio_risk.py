from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.build_global_portfolio_risk_report as risk_report_script
from project.research.global_portfolio_risk import (
    _extreme_metric_warning,
    build_portfolio_risk_report,
    build_stock_risk_metrics,
)


def test_v2_risk_builder_has_no_legacy_weight_fallback():
    source = Path(risk_report_script.__file__).read_text(encoding="utf-8")

    assert "global_portfolio_league_weights.csv" in source
    assert "global_master_candidate_weights.csv" not in source


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        rng.normal(0.0004, 0.012, size=(220, 4)),
        index=pd.date_range("2024-01-01", periods=220, freq="B"),
        columns=["A", "B", "C", "D"],
    )


def _metadata() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "sleeve": ["global_equity_us"] * 4,
            "country": ["United States"] * 4,
            "currency": ["USD"] * 4,
            "include": [True] * 4,
            "investable": [True] * 4,
            "signal_only": [False] * 4,
            "benchmark_only": [False] * 4,
        }
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
    report, contributions, stress, tail = build_portfolio_risk_report(
        returns,
        weights,
        risk_free_rate_annual=0.04,
        risk_free_policy="unit_test_fixed_rate",
        metadata=_metadata(),
    )

    assert set(["annualized_volatility", "var_95", "cvar_95"]).issubset(stock.columns)
    assert (stock["cvar_95"] <= stock["var_95"]).all()
    assert (stock["max_drawdown"] <= 0.0).all()
    assert np.isfinite(report["sharpe"]).all()
    assert report["risk_free_rate_annual"].iloc[0] == 0.04
    assert report["risk_free_policy"].iloc[0] == "unit_test_fixed_rate"
    daily_risk_free_hurdle = (1.0 + 0.04) ** (1.0 / 252.0) - 1.0
    expected_sharpe = (
        report["annualized_return"].iloc[0] - daily_risk_free_hurdle * 252.0
    ) / report["annualized_volatility"].iloc[0]
    assert np.isclose(report["sharpe"].iloc[0], expected_sharpe)
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
    targeted = stress.set_index("scenario")
    assert targeted.loc["crypto_crash", "target_exposure"] == 0.0
    assert targeted.loc["turkey_specific_shock", "target_exposure"] == 0.0
    assert targeted.loc["fx_shock", "target_exposure"] == 0.0
    assert targeted.loc["equity_selloff", "target_exposure"] == 1.0
    assert targeted.loc["crypto_crash", "applicability_status"] == (
        "zero_target_exposure"
    )


def test_zero_weight_asset_is_not_a_portfolio_covariance_input():
    returns = _returns()
    weights = pd.DataFrame(
        {
            "Model": ["Equal Weight", "Equal Weight", "Equal Weight"],
            "Ticker": ["A", "B", "C"],
            "Weight": [0.5, 0.5, 0.0],
        }
    )

    _, contributions, _, _ = build_portfolio_risk_report(returns, weights)

    assert set(contributions["ticker"]) == {"A", "B"}


def test_portfolio_risk_rejects_nonzero_weight_missing_from_returns():
    weights = pd.DataFrame(
        {
            "Model": ["Broken"] * 4,
            "Ticker": ["A", "B", "C", "MISSING"],
            "Weight": [0.3, 0.3, 0.3, 0.1],
        }
    )

    with pytest.raises(ValueError, match="missing from the returns matrix"):
        build_portfolio_risk_report(_returns(), weights)


def test_high_short_sample_point_estimates_are_review_flags():
    warning = _extreme_metric_warning(
        {
            "observations": 356,
            "annualized_return": 0.69,
            "cagr": 0.94,
            "annualized_volatility": 0.24,
            "sharpe": 2.9,
            "sortino": 4.6,
        }
    )

    assert "high_annualized_return_short_sample_review_required" in warning
    assert "high_cagr_short_sample_review_required" in warning
