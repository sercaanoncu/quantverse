import numpy as np
import pandas as pd

from project.research.global_walk_forward import (
    _apply_transaction_costs,
    run_public_data_walk_forward,
)


def _universe() -> pd.DataFrame:
    tickers = ["GOOD", "FUTURE_WINNER", "BAD"]
    return pd.DataFrame(
        {
            "ticker": tickers,
            "name": tickers,
            "sleeve": ["global_equity_us"] * 3,
            "region": ["North America"] * 3,
            "country": ["United States"] * 3,
            "currency": ["USD"] * 3,
            "data_provider": ["unit"] * 3,
            "source": ["unit"] * 3,
            "source_method": ["public_provider_current"] * 3,
            "market_cap_usd": [3, 2, 1],
        }
    )


def test_walk_forward_recomputes_scores_inside_train_window_without_future_winner():
    index = pd.date_range("2024-01-01", periods=282, freq="B")
    train = pd.DataFrame(
        {
            "GOOD": [0.002] * 252,
            "FUTURE_WINNER": [-0.002] * 252,
            "BAD": [-0.004] * 252,
        },
        index=index[:252],
    )
    test = pd.DataFrame(
        {
            "GOOD": [0.0] * 30,
            "FUTURE_WINNER": [0.20] * 30,
            "BAD": [0.0] * 30,
        },
        index=index[252:],
    )
    returns = pd.concat([train, test])

    result = run_public_data_walk_forward(
        returns,
        _universe(),
        train_window_days=252,
        test_window_days=20,
        step_days=20,
        max_assets=1,
        max_weight=1.00,
        max_folds=1,
        random_benchmark_portfolios=5,
    )

    assert result["summary"]["leakage_audit_passed"] is True
    assert result["summary"]["leakage_audit_status"] == (
        "passed_with_current_universe_survivorship_limitation"
    )
    assert result["summary"]["institutional_point_in_time_supported"] is False
    assert result["leakage_audit"]["passed"].all()
    assert set(result["leakage_audit"]["evidence_scope"]) == {
        "current_universe_not_point_in_time"
    }
    assert (
        not result["leakage_audit"]["institutional_point_in_time_supported"]
        .astype(bool)
        .any()
    )
    selected = result["window_summary"]["selected_tickers"].iloc[0]
    assert selected == "GOOD"


def test_transaction_cost_reduces_first_net_return_when_turnover_positive():
    gross = pd.Series([0.01, 0.02])
    weights = pd.Series([0.6, 0.4], index=["A", "B"])
    previous = pd.Series([0.5, 0.5], index=["A", "B"])
    net = _apply_transaction_costs(
        gross,
        weights,
        previous,
        transaction_cost_bps=10.0,
    )

    assert net.iloc[0] < gross.iloc[0]
    assert net.iloc[1] == gross.iloc[1]
