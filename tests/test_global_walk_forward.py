import numpy as np
import pandas as pd
import pytest

from project.research.global_walk_forward import (
    _apply_transaction_costs,
    _comparison,
    _summary,
    run_public_data_walk_forward,
)


def _returns(n_assets: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(19)
    return pd.DataFrame(
        rng.normal(0.0005, 0.011, size=(330, n_assets)),
        index=pd.date_range("2024-01-01", periods=330, freq="B"),
        columns=[f"AST{i}" for i in range(n_assets)],
    )


def _universe(n_assets: int = 7) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [f"AST{i}" for i in range(n_assets)],
            "name": [f"Asset {i}" for i in range(n_assets)],
            "sleeve": ["global_equity_us"] * n_assets,
            "region": ["North America"] * n_assets,
            "country": ["United States"] * n_assets,
            "currency": ["USD"] * n_assets,
            "data_provider": ["unit"] * n_assets,
            "source": ["unit"] * n_assets,
            "source_method": ["public_provider_current"] * n_assets,
            "market_cap_usd": np.arange(n_assets, 0, -1) * 1_000_000,
        }
    )


def test_walk_forward_uses_chronological_windows_and_writes_core_tables():
    result = run_public_data_walk_forward(
        _returns(),
        _universe(),
        train_window_days=252,
        test_window_days=21,
        step_days=21,
        max_assets=6,
        max_weight=0.25,
        max_folds=2,
        random_benchmark_portfolios=10,
        uncertainty_bootstrap_samples=50,
        uncertainty_block_length=5,
    )

    validation = result["validation"]
    summary = result["summary"]
    comparison = result["model_comparison"]
    weights = result["weights"]
    turnover = result["turnover"]
    random_distribution = result["random_distribution"]
    uncertainty = result["uncertainty"]

    assert summary["walk_forward_status"] == "completed_public_data_current_universe"
    assert not validation.empty
    assert (
        pd.to_datetime(validation["train_end"])
        .lt(pd.to_datetime(validation["test_start"]))
        .all()
    )
    assert "Equal Weight" in set(comparison["model_name"])
    assert not weights.empty
    assert not turnover.empty
    assert len(random_distribution) == 10
    assert set(random_distribution["benchmark_scope"]) == {"walk_forward_oos_net"}
    assert not uncertainty.empty
    assert set(uncertainty["uncertainty_method"]) == {"paired_circular_block_bootstrap"}
    assert validation["limitation"].str.contains("not institutional PIT").all()


def test_equity_walk_forward_uses_equity_calendar_not_crypto_weekends():
    index = pd.date_range("2024-01-01", periods=430, freq="D")
    rng = np.random.default_rng(20)
    returns = pd.DataFrame(index=index)
    business = index.dayofweek < 5
    for ticker in ["EQ0", "EQ1", "EQ2"]:
        returns[ticker] = np.where(
            business,
            rng.normal(0.0004, 0.01, size=len(index)),
            np.nan,
        )
    returns["BTC-USD"] = rng.normal(0.0005, 0.02, size=len(index))
    universe = pd.concat(
        [
            _universe(3).assign(ticker=["EQ0", "EQ1", "EQ2"]),
            pd.DataFrame(
                {
                    "ticker": ["BTC-USD"],
                    "name": ["Bitcoin"],
                    "sleeve": ["crypto"],
                    "region": ["Global"],
                    "country": ["Global"],
                    "currency": ["USD"],
                    "data_provider": ["unit"],
                    "source": ["unit"],
                    "source_method": ["public_provider_current"],
                    "market_cap_usd": [1_000_000],
                }
            ),
        ],
        ignore_index=True,
    )

    result = run_public_data_walk_forward(
        returns,
        universe,
        train_window_days=252,
        test_window_days=21,
        step_days=21,
        max_assets=3,
        max_weight=0.50,
        max_folds=1,
        default_scope="equity_only",
        include_crypto=False,
        random_benchmark_portfolios=10,
        uncertainty_bootstrap_samples=20,
        uncertainty_block_length=5,
    )

    assert result["summary"]["walk_forward_status"] == (
        "completed_public_data_current_universe"
    )
    assert int(result["window_summary"]["selected_count"].iloc[0]) == 3


def test_walk_forward_comparison_recalculates_metrics_from_concatenated_oos_returns():
    validation = pd.DataFrame(
        {
            "fold": [0, 1],
            "model_name": ["Equal Weight", "Equal Weight"],
            "cagr": [2.0, -0.5],
            "annualized_return": [1.0, -0.5],
            "annualized_volatility": [0.2, 0.2],
            "sharpe": [5.0, -2.5],
            "sortino": [6.0, -3.0],
            "max_drawdown": [-0.01, -0.20],
            "cvar_95": [-0.01, -0.10],
            "turnover": [0.4, 0.6],
        }
    )
    dates = pd.date_range("2025-01-02", periods=4, freq="B")
    returns_long = pd.DataFrame(
        {
            "Date": dates,
            "fold": [0, 0, 1, 1],
            "model_name": ["Equal Weight"] * 4,
            "return": [0.10, 0.10, -0.10, -0.10],
        }
    )

    comparison = _comparison(validation, returns_long)
    row = comparison.iloc[0]
    expected_annual_return = np.mean([0.10, 0.10, -0.10, -0.10]) * 252

    assert row["metric_aggregation"] == (
        "concatenated_non_overlapping_net_oos_daily_returns"
    )
    assert row["oos_annualized_return"] == expected_annual_return
    assert row["avg_annualized_return"] == row["oos_annualized_return"]
    assert row["oos_sharpe"] != validation["sharpe"].mean()


def test_transaction_cost_turnover_includes_exited_positions():
    returns = pd.Series([0.01], index=pd.to_datetime(["2025-01-02"]))
    current = pd.Series({"B": 1.0})
    previous = pd.Series({"A": 1.0})

    adjusted = _apply_transaction_costs(
        returns,
        current,
        previous,
        transaction_cost_bps=10.0,
    )

    assert adjusted.iloc[0] == pytest.approx(0.01 - 0.002)


def test_walk_forward_summary_does_not_label_diagnostic_model_as_best_model():
    validation = pd.DataFrame(
        {
            "fold": [0, 0],
            "model_name": ["Equal Weight", "Black-Litterman"],
            "model_status": ["benchmark_only", "diagnostic_only"],
            "cagr": [0.10, 0.50],
            "annualized_return": [0.10, 0.50],
            "annualized_volatility": [0.20, 0.20],
            "sharpe": [0.50, 2.50],
            "sortino": [0.60, 3.00],
            "max_drawdown": [-0.10, -0.08],
            "cvar_95": [-0.02, -0.02],
            "turnover": [0.20, 0.20],
        }
    )
    dates = pd.date_range("2025-01-02", periods=4, freq="B")
    returns_long = pd.DataFrame(
        {
            "Date": [dates[0], dates[1], dates[2], dates[3]],
            "fold": [0, 0, 0, 0],
            "model_name": [
                "Equal Weight",
                "Equal Weight",
                "Black-Litterman",
                "Black-Litterman",
            ],
            "return": [0.001, 0.001, 0.01, 0.01],
        }
    )

    comparison = _comparison(validation, returns_long)
    summary = _summary(
        comparison,
        validation,
        pd.DataFrame({"passed": [True]}),
    )

    assert summary["best_metric_model"] == "Black-Litterman"
    assert summary["best_metric_model_status"] == "diagnostic_only"
    assert summary["best_model"] == "Equal Weight"
