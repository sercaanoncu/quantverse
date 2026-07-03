import numpy as np
import pandas as pd

from project.research.global_return_forecasting import (
    FORECAST_COLUMNS,
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
