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


def test_invalid_calendar_raises():
    prices = pd.DataFrame(
        {"SPY": [100.0, 101.0]}, index=pd.date_range("2024-01-01", periods=2)
    )
    processor = DataProcessor(prices)

    with pytest.raises(ValueError, match="calendar"):
        processor.clean(calendar="exchange")
