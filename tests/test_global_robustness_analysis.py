import numpy as np
import pandas as pd

from project.research.global_robustness import (
    _bounded_scenario_grid,
    run_robustness_sensitivity,
)
from project.research.global_stock_scoring import build_global_stock_scores


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(12)
    values = rng.normal(0.0004, 0.01, size=(320, 5))
    return pd.DataFrame(
        values,
        index=pd.date_range("2024-01-01", periods=320, freq="B"),
        columns=[f"A{i}" for i in range(5)],
    )


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"A{i}" for i in range(5)],
            "name": [f"Asset {i}" for i in range(5)],
            "sleeve": ["global_equity_us"] * 5,
            "region": ["North America"] * 5,
            "country": ["United States"] * 5,
            "currency": ["USD"] * 5,
            "data_provider": ["unit"] * 5,
            "source": ["unit"] * 5,
            "source_method": ["public_provider_current"] * 5,
            "market_cap_usd": [5, 4, 3, 2, 1],
        }
    )


def test_sensitivity_output_schema_and_reproducibility():
    returns = _returns()
    scores = build_global_stock_scores(returns, _universe(), max_selected=5)
    result = run_robustness_sensitivity(
        returns,
        scores,
        metadata=_universe(),
        max_assets_values=[5],
        max_weight_values=[0.40],
        train_window_days_values=[252],
        test_window_days_values=[21],
        transaction_cost_bps_values=[0.0],
        random_seeds=[1],
        random_portfolios=5,
        max_scenarios=1,
    )
    repeat = run_robustness_sensitivity(
        returns,
        scores,
        metadata=_universe(),
        max_assets_values=[5],
        max_weight_values=[0.40],
        train_window_days_values=[252],
        test_window_days_values=[21],
        transaction_cost_bps_values=[0.0],
        random_seeds=[1],
        random_portfolios=5,
        max_scenarios=1,
    )

    assert {
        "scenario_id",
        "final_model",
        "net_annualized_return",
        "selected_holdings_overlap_with_base",
        "random_sharpe_percentile",
        "test_window_applied",
        "evidence_scope",
    }.issubset(result["sensitivity"].columns)
    assert not result["sensitivity"]["test_window_applied"].any()
    assert set(result["sensitivity"]["evidence_scope"]) == {
        "current_sample_configuration_diagnostic"
    }
    pd.testing.assert_frame_equal(result["sensitivity"], repeat["sensitivity"])
    assert result["summary"]["robustness_status"] == (
        "diagnostic_configuration_stability_only"
    )
    assert result["summary"]["promotion_eligible"] is False


def test_changing_transaction_cost_reduces_net_return():
    returns = _returns()
    scores = build_global_stock_scores(returns, _universe(), max_selected=5)
    result = run_robustness_sensitivity(
        returns,
        scores,
        metadata=_universe(),
        max_assets_values=[5],
        max_weight_values=[0.40],
        train_window_days_values=[252],
        test_window_days_values=[21],
        transaction_cost_bps_values=[0.0, 50.0],
        random_seeds=[1],
        random_portfolios=5,
        max_scenarios=2,
    )
    sensitivity = result["sensitivity"].sort_values("transaction_cost_bps")

    assert (
        sensitivity["net_annualized_return"].iloc[1]
        <= sensitivity["net_annualized_return"].iloc[0]
    )


def test_bounded_grid_samples_across_all_configured_dimensions():
    grid, feasible_count = _bounded_scenario_grid(
        pd.DataFrame(index=range(320), columns=range(8)),
        max_assets_grid=[5, 8],
        max_weight_grid=[0.20, 0.40],
        train_grid=[126, 252],
        test_grid=[21, 63],
        cost_grid=[0.0, 25.0],
        seed_grid=[1, 2],
        max_scenarios=12,
    )

    assert feasible_count == 64
    assert len(grid) == 12
    assert {row["max_assets"] for row in grid} == {5, 8}
    assert {row["max_weight"] for row in grid} == {0.20, 0.40}
    assert {row["train_window_days"] for row in grid} == {126, 252}
    assert {row["test_window_days"] for row in grid} == {21, 63}
    assert {row["transaction_cost_bps"] for row in grid} == {0.0, 25.0}
    assert {row["random_seed"] for row in grid} == {1, 2}
