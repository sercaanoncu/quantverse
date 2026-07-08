import pandas as pd

from project.research.global_model_selection import (
    build_final_model_decision,
    build_model_selection_report,
)


def test_forecast_failed_validation_blocks_forecast_enhanced_selection():
    league = pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "annualized_return": 0.10,
                "volatility": 0.15,
                "sharpe": 0.67,
                "max_drawdown": -0.10,
                "cvar_95": -0.015,
            },
            {
                "model_name": "Forecast-Enhanced Constrained Portfolio",
                "actual_status": "actually_run",
                "constraints_pass": True,
                "annualized_return": 0.12,
                "volatility": 0.12,
                "sharpe": 1.00,
                "max_drawdown": -0.08,
                "cvar_95": -0.012,
            },
        ]
    )
    walk = pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "avg_annualized_return": 0.10,
                "avg_volatility": 0.15,
                "avg_sharpe": 0.67,
                "avg_sortino": 0.90,
                "avg_max_drawdown": -0.10,
                "avg_cvar_95": -0.015,
                "avg_turnover": 0.1,
            },
            {
                "model_name": "Forecast-Enhanced Constrained Portfolio",
                "avg_annualized_return": 0.12,
                "avg_volatility": 0.12,
                "avg_sharpe": 1.00,
                "avg_sortino": 1.30,
                "avg_max_drawdown": -0.08,
                "avg_cvar_95": -0.012,
                "avg_turnover": 0.2,
            },
        ]
    )
    random = pd.DataFrame(
        [
            {"model_name": "Equal Weight", "sharpe_percentile": 0.55},
            {
                "model_name": "Forecast-Enhanced Constrained Portfolio",
                "sharpe_percentile": 0.90,
            },
        ]
    )

    report = build_model_selection_report(
        league,
        walk_forward=walk,
        random_percentiles=random,
        forecast_validation_status="failed_scale_sanity",
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    forecast = report.loc[
        report["model_name"].eq("Forecast-Enhanced Constrained Portfolio")
    ].iloc[0]
    assert "forecast validation blocks" in forecast["promotion_gate_failed_reasons"]


def test_in_sample_max_sharpe_cannot_override_weak_walk_forward():
    league = pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "actual_status": "benchmark_only",
                "constraints_pass": True,
                "annualized_return": 0.10,
                "volatility": 0.15,
                "sharpe": 0.67,
                "max_drawdown": -0.10,
                "cvar_95": -0.015,
            },
            {
                "model_name": "Max Sharpe",
                "actual_status": "actually_run",
                "constraints_pass": True,
                "annualized_return": 0.80,
                "volatility": 0.20,
                "sharpe": 4.00,
                "max_drawdown": -0.12,
                "cvar_95": -0.020,
            },
        ]
    )
    walk = pd.DataFrame(
        [
            {
                "model_name": "Equal Weight",
                "avg_annualized_return": 0.10,
                "avg_volatility": 0.15,
                "avg_sharpe": 0.67,
                "avg_sortino": 0.90,
                "avg_max_drawdown": -0.10,
                "avg_cvar_95": -0.015,
                "avg_turnover": 0.1,
            },
            {
                "model_name": "Max Sharpe",
                "avg_annualized_return": 0.08,
                "avg_volatility": 0.18,
                "avg_sharpe": 0.44,
                "avg_sortino": 0.60,
                "avg_max_drawdown": -0.13,
                "avg_cvar_95": -0.018,
                "avg_turnover": 0.2,
            },
        ]
    )
    random = pd.DataFrame(
        [
            {"model_name": "Equal Weight", "sharpe_percentile": 0.60},
            {"model_name": "Max Sharpe", "sharpe_percentile": 0.90},
        ]
    )

    report = build_model_selection_report(
        league,
        walk_forward=walk,
        random_percentiles=random,
    )
    decision = build_final_model_decision(report)

    assert decision["final_selected_model"] == "Equal Weight"
    max_sharpe = report.loc[report["model_name"].eq("Max Sharpe")].iloc[0]
    assert (
        "walk-forward Sharpe improvement" in max_sharpe["promotion_gate_failed_reasons"]
    )
