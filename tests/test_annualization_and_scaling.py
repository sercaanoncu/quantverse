import json

import numpy as np
import pandas as pd

from project.constants import TRADING_DAYS_PER_YEAR
from project.research.global_portfolio_risk import evaluate_return_series
from project.research.global_return_forecasting import build_return_forecasts

import scripts.run_quantverse_v2_demo as demo


def test_daily_return_annualization_known_case():
    daily = pd.Series([0.001] * TRADING_DAYS_PER_YEAR)
    metrics = evaluate_return_series(daily)

    assert np.isclose(metrics["annualized_return"], 0.252)
    assert np.isclose(metrics["cagr"], (1.001**TRADING_DAYS_PER_YEAR) - 1.0)
    assert np.isclose(metrics["annualized_volatility"], 0.0)


def test_12m_forecast_is_horizon_return_not_double_annualized():
    returns = pd.DataFrame(
        {"AAA": [0.001] * 300},
        index=pd.date_range("2024-01-01", periods=300, freq="B"),
    )
    forecasts = build_return_forecasts(returns, horizons={"12M": 252})
    row = forecasts.iloc[0]

    assert np.isclose(row["rolling_mean_expected_return"], 0.252)
    assert row["expected_return_unit"] == (
        "decimal cumulative simple return over forecast horizon"
    )
    assert "not annualized" in row["annualization_method"]


def test_demo_summary_labels_realized_annualized_return_not_guaranteed_forecast(
    tmp_path,
    monkeypatch,
):
    processed = tmp_path / "data" / "processed"
    universe_dir = tmp_path / "data" / "universe"
    processed.mkdir(parents=True)
    universe_dir.mkdir(parents=True)
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "PROCESSED", processed)
    monkeypatch.setattr(demo, "SUMMARY_PATH", processed / "summary.json")

    pd.DataFrame({"ticker": ["AAA"]}).to_csv(
        universe_dir / "current_global_equity_universe.csv", index=False
    )
    pd.DataFrame({"Date": ["2024-01-01"], "AAA": [0.01]}).to_csv(
        processed / "global_security_simple_returns_usd.csv", index=False
    )
    pd.DataFrame({"ticker": ["AAA"], "selection_flag": [True]}).to_csv(
        processed / "global_stock_scores.csv", index=False
    )
    pd.DataFrame({"ticker": ["AAA"], "horizon": ["12M"]}).to_csv(
        processed / "global_stock_return_forecasts.csv", index=False
    )
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "actual_status": ["benchmark_only"],
            "constraints_pass": [True],
            "sharpe": [1.0],
            "cagr": [0.1],
        }
    ).to_csv(processed / "global_portfolio_league.csv", index=False)
    pd.DataFrame(
        {"model_name": ["Equal Weight"], "ticker": ["AAA"], "weight": [1.0]}
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "annualized_return": [2.5],
            "annualized_volatility": [0.3],
            "cvar_95": [-0.02],
            "extreme_metric_warning": ["extreme_annualized_return_review_required"],
        }
    ).to_csv(processed / "global_portfolio_risk_report.csv", index=False)
    pd.DataFrame({"check": ["finite"], "passed": [True]}).to_csv(
        processed / "global_risk_metric_sanity_checks.csv", index=False
    )
    pd.DataFrame({"transaction_cost_decimal": [0.001]}).to_csv(
        processed / "global_walk_forward_turnover.csv", index=False
    )
    (processed / "global_walk_forward_summary.json").write_text(
        json.dumps({"walk_forward_status": "unit", "leakage_audit_passed": True}),
        encoding="utf-8",
    )
    (processed / "global_master_decision_summary.json").write_text(
        json.dumps({"promotion_decision": "not promoted", "reason": "unit"}),
        encoding="utf-8",
    )

    summary = demo.build_demo_summary()

    assert summary["expected_portfolio_return"] == 2.5
    assert "annualized arithmetic" in summary["expected_portfolio_return_label"]
    assert "not guaranteed" in summary["expected_portfolio_return_label"]
    assert summary["expected_portfolio_return_warning"] == (
        "extreme_annualized_return_review_required"
    )
    assert summary["transaction_cost_status"] == "applied_in_walk_forward_net_returns"
