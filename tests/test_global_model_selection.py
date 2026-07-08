import pandas as pd

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
)


def _league() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "effective_holdings": 4,
                "concentration_warning": "none",
                "cagr": 0.08,
                "annualized_return": 0.08,
                "volatility": 0.15,
                "sharpe": 0.53,
                "sortino": 0.70,
                "max_drawdown": -0.12,
                "cvar_95": -0.015,
                "turnover": 0.0,
            },
            {
                "model_name": "Risky Active",
                "actual_status": "actually_run",
                "constraints_pass": True,
                "effective_holdings": 3,
                "concentration_warning": "none",
                "cagr": 0.20,
                "annualized_return": 0.20,
                "volatility": 0.45,
                "sharpe": 0.44,
                "sortino": 0.50,
                "max_drawdown": -0.35,
                "cvar_95": -0.050,
                "turnover": 1.8,
            },
            {
                "model_name": "Diagnostic Forecast",
                "actual_status": "diagnostic_only",
                "constraints_pass": True,
                "effective_holdings": 3,
                "concentration_warning": "none",
                "cagr": 0.50,
                "annualized_return": 0.50,
                "volatility": 0.20,
                "sharpe": 2.50,
                "sortino": 3.00,
                "max_drawdown": -0.10,
                "cvar_95": -0.010,
                "turnover": 0.0,
            },
            {
                "model_name": "Random Portfolios",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "effective_holdings": 4,
                "concentration_warning": "benchmark_distribution",
                "cagr": 0.30,
                "annualized_return": 0.30,
                "volatility": 0.10,
                "sharpe": 3.00,
                "sortino": 3.50,
                "max_drawdown": -0.05,
                "cvar_95": -0.010,
                "turnover": 0.0,
            },
        ]
    )


def test_final_model_cannot_be_blocked_or_diagnostic_only():
    report = build_model_selection_report(_league())
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] != "Diagnostic Forecast"
    diagnostic = report.loc[report["model_name"].eq("Diagnostic Forecast")].iloc[0]
    assert not bool(diagnostic["eligible_final_model"])
    assert "diagnostic_only" in diagnostic["rejection_reason"]
    random_row = report.loc[report["model_name"].eq("Random Portfolios")].iloc[0]
    assert not bool(random_row["eligible_final_model"])
    assert "benchmark distribution" in random_row["rejection_reason"]


def test_equal_weight_wins_when_active_fails_risk_and_cost_gates():
    report = build_model_selection_report(_league())
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    assert (
        "Equal Weight remains the defensible benchmark"
        in decision["final_decision_reason"]
    )


def test_selection_penalizes_drawdown_and_turnover():
    report = build_model_selection_report(_league())
    equal_weight_score = float(
        report.loc[report["model_name"].eq("Equal Weight"), "selection_score"].iloc[0]
    )
    risky_score = float(
        report.loc[report["model_name"].eq("Risky Active"), "selection_score"].iloc[0]
    )

    assert risky_score < equal_weight_score
    risky = report.loc[report["model_name"].eq("Risky Active")].iloc[0]
    assert "drawdown" in risky["rejection_reason"]
    assert "walk-forward Sharpe improvement" in risky["rejection_reason"]


def test_model_decision_json_schema_fields_are_present():
    decision = build_final_model_decision(build_model_selection_report(_league()))

    assert {
        "final_selected_model",
        "final_model_selection_method",
        "final_model_selection_score",
        "final_decision",
        "final_decision_reason",
        "equal_weight_comparison",
        "random_portfolio_percentile",
        "publish_readiness_status",
    }.issubset(decision)
