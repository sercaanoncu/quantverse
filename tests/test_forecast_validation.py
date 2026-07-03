import pandas as pd

from project.research.global_forecast_validation import build_forecast_validation


def test_forecast_validation_schema_and_random_walk_baseline_present():
    forecasts = pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "horizon": ["12M", "12M", "12M"],
            "horizon_days": [252, 252, 252],
            "rmse": [0.20, 0.30, 0.25],
            "mae": [0.20, 0.30, 0.25],
            "benchmark_random_walk_error": [0.10, 0.20, 0.15],
            "r2": [-0.1, -0.2, -0.3],
            "forecast_confidence": [0.4, 0.5, 0.6],
            "prediction_interval_low": [-0.3, -0.4, -0.2],
            "prediction_interval_high": [0.3, 0.4, 0.2],
        }
    )

    validation = build_forecast_validation(forecasts)

    assert {
        "horizon",
        "mean_mae",
        "mean_random_walk_mae",
        "forecast_validation_status",
        "allocation_signal_status",
    }.issubset(validation["by_horizon"].columns)
    assert not validation["random_walk"].empty


def test_bad_forecast_does_not_become_promoted_signal():
    forecasts = pd.DataFrame(
        {
            "ticker": ["A"],
            "horizon": ["1M"],
            "horizon_days": [21],
            "rmse": [0.50],
            "mae": [0.50],
            "benchmark_random_walk_error": [0.10],
            "r2": [-1.0],
            "forecast_confidence": [0.9],
            "prediction_interval_low": [-0.1],
            "prediction_interval_high": [0.1],
        }
    )

    validation = build_forecast_validation(forecasts)

    row = validation["by_horizon"].iloc[0]
    assert row["forecast_validation_status"] == "diagnostic_only"
    assert row["allocation_signal_status"] == "diagnostic_only"
    assert validation["warnings"]["allocation_use_allowed"].eq(False).all()
