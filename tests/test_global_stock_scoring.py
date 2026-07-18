import numpy as np
import pandas as pd

from project.research.global_stock_scoring import (
    SCORE_COLUMNS,
    build_global_stock_scores,
)


def _returns() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=300, freq="B")
    frame = pd.DataFrame(
        {
            "STRONG": np.full(300, 0.0015),
            "WEAK": np.full(300, -0.0008),
            "VOL": np.tile([0.055, -0.050], 150),
            "LOW": np.r_[np.full(230, np.nan), np.full(70, 0.001)],
            "DIVERS": np.tile([0.002, -0.001], 150),
        },
        index=index,
    )
    return frame


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["STRONG", "WEAK", "VOL", "LOW", "DIVERS"],
            "name": ["Strong", "Weak", "Volatile", "Low Coverage", "Diversifier"],
            "sleeve": ["global_equity_us"] * 5,
            "region": ["North America"] * 5,
            "country": ["United States"] * 5,
            "currency": ["USD"] * 5,
            "data_provider": ["unit"] * 5,
            "source": ["unit"] * 5,
            "source_method": ["public_provider_current"] * 5,
            "proxy_type": ["direct_listing"] * 5,
            "market_cap_usd": [500, 400, 300, 200, 100],
        }
    )


def test_stock_scoring_schema_rankings_and_penalties_are_deterministic():
    first = build_global_stock_scores(_returns(), _universe(), max_selected=3)
    second = build_global_stock_scores(_returns(), _universe(), max_selected=3)

    assert list(first.columns) == SCORE_COLUMNS
    pd.testing.assert_frame_equal(first, second)
    assert (
        first.loc[first["ticker"].eq("STRONG"), "rank_global"].iloc[0]
        < first.loc[first["ticker"].eq("WEAK"), "rank_global"].iloc[0]
    )
    assert (
        "low_coverage" in first.loc[first["ticker"].eq("LOW"), "warning_flags"].iloc[0]
    )
    assert (
        "high_volatility"
        in first.loc[first["ticker"].eq("VOL"), "warning_flags"].iloc[0]
    )
    low = first.loc[first["ticker"].eq("LOW")].iloc[0]
    assert low["eligibility_status"] == "diagnostic_short_history"
    assert bool(low["selection_flag"]) is False
    assert pd.isna(low["momentum_12m"])
    assert pd.isna(low["volatility_12m"])
    assert int(first["selection_flag"].sum()) == 3


def test_stock_scoring_respects_as_of_date_and_does_not_use_future_returns():
    base = _returns()
    as_of = base.index[-1]
    baseline = build_global_stock_scores(base, _universe(), as_of_date=as_of)
    future = pd.concat(
        [
            base,
            pd.DataFrame(
                {
                    "STRONG": -0.20,
                    "WEAK": 0.50,
                    "VOL": 0.50,
                    "LOW": 0.50,
                    "DIVERS": 0.50,
                },
                index=pd.date_range(as_of + pd.offsets.BDay(), periods=5, freq="B"),
            ),
        ]
    )
    after_future_appended = build_global_stock_scores(
        future, _universe(), as_of_date=as_of
    )

    pd.testing.assert_series_equal(
        baseline.set_index("ticker")["composite_quant_score"].sort_index(),
        after_future_appended.set_index("ticker")["composite_quant_score"].sort_index(),
    )
