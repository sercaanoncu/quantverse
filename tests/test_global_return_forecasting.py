import numpy as np
import pandas as pd

from project.research.global_return_forecasting import (
    FORECAST_COLUMNS,
    _ridge_forecast_and_errors,
    build_return_forecasts,
)


def _returns() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=280, freq="B")
    return pd.DataFrame(
        {
            "LONG": np.full(280, 0.001),
            "SHORT": np.r_[np.full(220, np.nan), np.full(60, 0.001)],
        },
        index=index,
    )


def test_return_forecast_schema_baseline_intervals_and_confidence():
    forecasts = build_return_forecasts(_returns(), horizons={"1M": 21})

    assert list(forecasts.columns) == FORECAST_COLUMNS
    assert set(forecasts["ticker"]) == {"LONG", "SHORT"}
    assert (forecasts["naive_random_walk_expected_return"] == 0.0).all()
    assert (
        forecasts["prediction_interval_low"] <= forecasts["ensemble_expected_return"]
    ).all()
    assert (
        forecasts["ensemble_expected_return"] <= forecasts["prediction_interval_high"]
    ).all()
    long_confidence = forecasts.loc[
        forecasts["ticker"].eq("LONG"), "forecast_confidence"
    ].iloc[0]
    short_confidence = forecasts.loc[
        forecasts["ticker"].eq("SHORT"), "forecast_confidence"
    ].iloc[0]
    assert long_confidence > short_confidence


def test_return_forecast_as_of_date_excludes_future_data():
    base = _returns()
    as_of = base.index[-1]
    baseline = build_return_forecasts(base, as_of_date=as_of, horizons={"1M": 21})
    future = pd.concat(
        [
            base,
            pd.DataFrame(
                {"LONG": -0.25, "SHORT": 0.50},
                index=pd.date_range(as_of + pd.offsets.BDay(), periods=5, freq="B"),
            ),
        ]
    )
    after_future_appended = build_return_forecasts(
        future, as_of_date=as_of, horizons={"1M": 21}
    )

    pd.testing.assert_series_equal(
        baseline.set_index("ticker")["ensemble_expected_return"].sort_index(),
        after_future_appended.set_index("ticker")[
            "ensemble_expected_return"
        ].sort_index(),
    )


def test_short_history_does_not_masquerade_as_twelve_month_momentum():
    forecasts = build_return_forecasts(_returns()[["SHORT"]], horizons={"12M": 252})
    row = forecasts.iloc[0]

    assert pd.isna(row["momentum_expected_return"])
    assert row["model_status"] == "low_data_diagnostic"


def test_one_month_mean_reversion_is_not_relabelled_as_long_horizon_forecast():
    forecasts = build_return_forecasts(_returns()[["LONG"]], horizons={"12M": 252})
    row = forecasts.iloc[0]

    assert pd.isna(row["mean_reversion_expected_return"])
    assert (
        "mean_reversion_component_not_applicable_beyond_1m" in row["diagnostic_warning"]
    )


def test_insufficient_variance_history_does_not_create_false_narrow_interval():
    returns = pd.DataFrame(
        {"NEW": [0.01]},
        index=pd.to_datetime(["2026-01-02"]),
    )

    row = build_return_forecasts(returns, horizons={"1M": 21}).iloc[0]

    assert pd.isna(row["prediction_interval_low"])
    assert pd.isna(row["prediction_interval_high"])
    assert row["model_status"] == "low_data_diagnostic"


def test_ridge_validation_purges_overlapping_training_labels_and_predicts_latest():
    rng = np.random.default_rng(41)
    index = pd.date_range("2020-01-01", periods=700, freq="B")
    series = pd.Series(rng.normal(0.0003, 0.01, len(index)), index=index)

    prediction, diagnostics = _ridge_forecast_and_errors(series, 63)

    assert np.isfinite(prediction)
    assert diagnostics["purge_observations"] == 63
    assert diagnostics["prediction_as_of"] == index[-1].date().isoformat()
