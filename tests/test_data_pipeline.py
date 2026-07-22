import numpy as np
import pandas as pd
import pytest

from project.data_pipeline.fetcher import DataFetcher
from project.data_pipeline.processor import DataProcessor


def test_fetch_prices_defaults_to_investable_tickers():
    fetcher = DataFetcher(start_date="2024-01-01", end_date="2024-01-31")

    assert "^VIX" not in fetcher.universe.investable_tickers
    assert "^VIX" in fetcher.universe.signal_tickers
    assert "^IRX" not in fetcher.universe.investable_tickers
    assert "^IRX" in fetcher.universe.signal_tickers


def test_business_calendar_drops_weekends_before_return_calculation():
    prices = pd.DataFrame(
        {
            "SPY": [100.0, 100.0, 100.0, 101.0],
            "BTC-USD": [100.0, 110.0, 120.0, 132.0],
        },
        index=pd.to_datetime(["2024-01-05", "2024-01-06", "2024-01-07", "2024-01-08"]),
    )

    processor = DataProcessor(prices)
    cleaned = processor.clean(calendar="business")
    returns = processor.compute_returns()

    assert list(cleaned.index) == [
        pd.Timestamp("2024-01-05"),
        pd.Timestamp("2024-01-08"),
    ]
    assert list(returns.index) == [pd.Timestamp("2024-01-08")]
    assert returns.loc["2024-01-08", "SPY"] == pytest.approx(0.01)
    assert returns.loc["2024-01-08", "BTC-USD"] == pytest.approx(0.32)


def test_business_calendar_mask_is_recomputed_after_sorting():
    prices = pd.DataFrame(
        {"SPY": [106.0, 100.0, 102.0]},
        index=pd.to_datetime(["2024-01-06", "2024-01-05", "2024-01-08"]),
    )

    cleaned = DataProcessor(prices).clean(calendar="business")

    assert list(cleaned.index) == [
        pd.Timestamp("2024-01-05"),
        pd.Timestamp("2024-01-08"),
    ]
    assert cleaned["SPY"].tolist() == [100.0, 102.0]


def test_time_interpolation_is_rejected_as_future_looking():
    prices = pd.DataFrame(
        {"AAA": [100.0, np.nan, 102.0]},
        index=pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
    )

    with pytest.raises(ValueError, match="future endpoint"):
        DataProcessor(prices).clean(
            min_history_pct=0.5,
            max_gap_days=2,
            fill_method="interpolate",
        )


@pytest.mark.parametrize("invalid_limit", [None, 0, -1, True, 1.5])
def test_price_cleaning_requires_positive_integer_forward_fill_limit(invalid_limit):
    prices = pd.DataFrame(
        {"AAA": [100.0, np.nan, 102.0]},
        index=pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
    )

    with pytest.raises(ValueError, match="positive integer"):
        DataProcessor(prices).clean(
            min_history_pct=0.5,
            max_gap_days=invalid_limit,
            fill_method="ffill",
        )


def test_invalid_calendar_raises():
    prices = pd.DataFrame(
        {"SPY": [100.0, 101.0]}, index=pd.date_range("2024-01-01", periods=2)
    )
    processor = DataProcessor(prices)

    with pytest.raises(ValueError, match="calendar"):
        processor.clean(calendar="exchange")


def test_long_internal_gap_is_not_silently_forward_or_backward_filled():
    index = pd.date_range("2024-01-01", periods=120, freq="B")
    prices = pd.DataFrame(
        {
            "COMPLETE": np.linspace(100.0, 120.0, len(index)),
            "LONG_GAP": np.linspace(80.0, 95.0, len(index)),
        },
        index=index,
    )
    prices.loc[index[40:48], "LONG_GAP"] = np.nan

    cleaned = DataProcessor(prices).clean(
        min_history_pct=0.80,
        max_gap_days=3,
        fill_method="ffill",
    )

    assert list(cleaned.columns) == ["COMPLETE"]
    assert not cleaned.isna().any().any()


def test_simple_returns_do_not_implicitly_fill_missing_prices():
    index = pd.date_range("2024-01-01", periods=4, freq="B")
    processor = DataProcessor(
        pd.DataFrame({"A": [100.0, 101.0, np.nan, 103.0]}, index=index)
    )
    processor.prices = processor.raw_prices.copy()

    result = processor.compute_returns(method="simple")

    assert list(result.index) == [index[1]]


def test_annualize_return_uses_arithmetic_mean_contract():
    returns = pd.Series([0.01, -0.005, 0.002])

    actual = DataProcessor.annualize_return(returns, trading_days=252)

    assert actual == pytest.approx(returns.mean() * 252)
