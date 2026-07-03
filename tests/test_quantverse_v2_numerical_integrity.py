import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.research.global_numerical_integrity import (
    portfolio_return_series,
    validate_v2_numerical_integrity,
)


def _write_base_fixture(root: Path, *, broken: bool = False) -> Path:
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    dates = pd.date_range("2024-01-01", periods=80, freq="B")
    returns = pd.DataFrame(
        {
            "Date": dates,
            "A": np.r_[np.full(20, np.nan), np.full(60, 0.001)],
            "B": np.r_[np.full(20, np.nan), np.tile([0.002, -0.001], 30)],
        }
    )
    returns.to_csv(processed / "global_security_simple_returns_usd.csv", index=False)
    (processed / "quantverse_v2_demo_summary.json").write_text(
        json.dumps(
            {
                "run_status": "completed",
                "final_selected_model": "Equal Weight",
                "final_selected_holdings": 2,
                "expected_portfolio_volatility": 0.0 if broken else 0.02,
                "weight_sum": 1.0,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "actual_status": ["benchmark_only"],
            "cagr": [0.0 if broken else 0.20],
            "annualized_return": [0.0 if broken else 0.18],
            "volatility": [0.0 if broken else 0.02],
            "sharpe": [0.0 if broken else 1.2],
            "sortino": [0.0 if broken else 1.4],
            "max_drawdown": [0.0 if broken else -0.01],
            "var_95": [0.0 if broken else -0.001],
            "cvar_95": [0.0 if broken else -0.0015],
        }
    ).to_csv(processed / "global_portfolio_league.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "weight": [0.5, 0.5],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "cagr": [0.0 if broken else 0.20],
            "annualized_return": [0.0 if broken else 0.18],
            "annualized_volatility": [0.0 if broken else 0.02],
            "sharpe": [0.0 if broken else 1.2],
            "sortino": [0.0 if broken else 1.4],
            "max_drawdown": [0.0 if broken else -0.01],
            "var_95": [0.0 if broken else -0.001],
            "cvar_95": [0.0 if broken else -0.0015],
            "total_return": [0.0 if broken else 0.05],
        }
    ).to_csv(processed / "global_portfolio_risk_report.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "avg_cagr": [0.0 if broken else 0.10],
            "avg_annualized_return": [0.0 if broken else 0.09],
            "avg_volatility": [0.0 if broken else 0.03],
            "avg_sharpe": [0.0 if broken else 1.0],
            "avg_sortino": [0.0 if broken else 1.1],
            "avg_max_drawdown": [0.0 if broken else -0.01],
            "avg_cvar_95": [0.0 if broken else -0.001],
        }
    ).to_csv(processed / "global_walk_forward_model_comparison.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Policy Constrained"],
            "return_percentile": [1.0, 1.0 if broken else 0.6],
            "volatility_percentile": [1.0, 1.0 if broken else 0.5],
            "sharpe_percentile": [1.0, 1.0 if broken else 0.7],
            "max_drawdown_percentile": [1.0, 1.0 if broken else 0.4],
            "cvar_percentile": [1.0, 1.0 if broken else 0.5],
        }
    ).to_csv(processed / "global_random_portfolio_percentile_report.csv", index=False)
    pd.DataFrame(
        {
            "horizon": ["12M"],
            "mean_mae": [305.0 if broken else 0.12],
            "mean_rmse": [400.0 if broken else 0.16],
            "mean_random_walk_mae": [0.6 if broken else 0.14],
            "allocation_signal_status": ["diagnostic_only"],
        }
    ).to_csv(processed / "global_forecast_validation_by_horizon.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["A", "B"],
            "risk_contribution_pct": [0.5, 0.5],
        }
    ).to_csv(processed / "global_risk_contribution_report.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "selection_flag": [True, True],
        }
    ).to_csv(processed / "global_stock_scores.csv", index=False)
    return processed


def test_portfolio_return_series_handles_staggered_listing_history():
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    returns = pd.DataFrame(
        {"A": [0.01, 0.02, 0.01, 0.0, -0.01], "B": [np.nan, np.nan, 0.02, 0.01, 0.0]},
        index=dates,
    )
    series = portfolio_return_series(
        returns,
        pd.Series({"A": 0.5, "B": 0.5}),
        min_available_weight=0.5,
    )

    assert not series.empty
    assert series.iloc[0] == 0.01
    assert series.std() > 0


def test_numerical_integrity_passes_on_valid_synthetic_fixture(tmp_path):
    _write_base_fixture(tmp_path, broken=False)

    result = validate_v2_numerical_integrity(tmp_path)

    assert result["overall_status"] == "passed"
    assert result["failed_check_count"] == 0


def test_numerical_integrity_fails_on_zero_metrics_and_bad_forecast_scale(tmp_path):
    _write_base_fixture(tmp_path, broken=True)

    result = validate_v2_numerical_integrity(tmp_path)

    assert result["overall_status"] == "failed"
    failed = {check["check"] for check in result["checks"] if not check["passed"]}
    assert "risk_metrics_not_all_zero_for_executable_models" in failed
    assert "walk_forward_metrics_not_all_zero" in failed
    assert "random_percentiles_not_identical_one" in failed
    assert "forecast_error_scale_sane" in failed
