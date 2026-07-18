import numpy as np
import pandas as pd

from project.data_pipeline.security_identity import (
    build_feature_history_eligibility,
    filter_standard_history_eligible_inputs,
)
from project.research.global_stock_scoring import build_global_stock_scores


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["IPO", "SEASONED"],
            "name": ["New IPO", "Seasoned Stock"],
            "sleeve": ["global_equity_us", "global_equity_us"],
            "region": ["North America", "North America"],
            "country": ["United States", "United States"],
            "currency": ["USD", "USD"],
            "investable": [True, True],
            "include": [True, True],
            "benchmark_only": [False, False],
            "signal_only": [False, False],
            "data_provider": ["unit", "unit"],
            "source": ["unit", "unit"],
            "source_method": ["direct_listing", "direct_listing"],
            "market_cap_usd": [1_000_000, 2_000_000],
        }
    )


def _returns() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=260, freq="B")
    return pd.DataFrame(
        {
            "IPO": np.r_[np.full(240, np.nan), np.full(20, 0.002)],
            "SEASONED": np.full(260, 0.001),
        },
        index=dates,
    )


def test_new_ipo_cannot_claim_twelve_month_features():
    eligibility = build_feature_history_eligibility(_returns()).set_index("ticker")
    ipo = eligibility.loc["IPO"]

    assert int(ipo["observations"]) == 20
    assert bool(ipo["1m_eligible"]) is False
    assert bool(ipo["12m_eligible"]) is False
    assert bool(ipo["volatility_12m_eligible"]) is False
    assert bool(ipo["standard_composite_score_eligible"]) is False
    assert ipo["eligibility_status"] == "diagnostic_short_history"


def test_new_ipo_remains_visible_but_cannot_enter_standard_ranking():
    scores = build_global_stock_scores(_returns(), _universe(), max_selected=2)
    ipo = scores.loc[scores["ticker"].eq("IPO")].iloc[0]
    seasoned = scores.loc[scores["ticker"].eq("SEASONED")].iloc[0]

    assert pd.isna(ipo["momentum_12m"])
    assert pd.isna(ipo["volatility_12m"])
    assert ipo["eligibility_status"] == "diagnostic_short_history"
    assert bool(ipo["selection_flag"]) is False
    assert bool(seasoned["standard_composite_score_eligible"]) is True
    assert bool(seasoned["selection_flag"]) is True


def test_long_history_security_is_standard_eligible():
    eligibility = build_feature_history_eligibility(_returns()).set_index("ticker")
    seasoned = eligibility.loc["SEASONED"]

    assert int(seasoned["observations"]) == 260
    assert bool(seasoned["12m_eligible"]) is True
    assert bool(seasoned["volatility_12m_eligible"]) is True
    assert bool(seasoned["standard_composite_score_eligible"]) is True
    assert seasoned["eligibility_status"] == "eligible"


def test_standard_history_gate_excludes_short_history_from_portfolio_inputs():
    returns = _returns()
    universe = _universe()
    eligibility = build_feature_history_eligibility(returns)

    filtered_returns, filtered_universe, excluded = (
        filter_standard_history_eligible_inputs(returns, universe, eligibility)
    )

    assert list(filtered_returns.columns) == ["SEASONED"]
    assert filtered_universe["ticker"].tolist() == ["SEASONED"]
    assert excluded == ["IPO"]
