import sys
import inspect

import numpy as np
import pandas as pd
import pytest

import scripts.run_global_walk_forward_validation as walk_forward_cli
from project.research.global_walk_forward import (
    _apply_transaction_costs,
    _comparison,
    _drift_weights_through_returns,
    _summary,
    _two_way_turnover,
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
    random_weights = result["random_weights"]
    uncertainty = result["uncertainty"]
    fold_audit = result["fold_audit"]

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
    assert not random_weights.empty
    assert {
        "fold",
        "portfolio_id",
        "ticker",
        "target_weight",
        "pre_trade_weight",
        "post_test_weight",
    }.issubset(random_weights.columns)
    assert set(random_distribution["benchmark_scope"]) == {"walk_forward_oos_net"}
    assert not uncertainty.empty
    assert set(uncertainty["uncertainty_method"]) == {"paired_circular_block_bootstrap"}
    assert validation["limitation"].str.contains("not institutional PIT").all()
    assert {
        "fold_id",
        "decision_date",
        "selected_issuer_count",
        "duplicate_issuer_count",
        "model_count",
        "risk_free_coverage",
        "cost_applied",
        "leakage_status",
    }.issubset(fold_audit.columns)
    assert len(fold_audit) == 2
    assert fold_audit["duplicate_issuer_count"].eq(0).all()
    assert fold_audit["cost_applied"].all()
    assert fold_audit["leakage_status"].eq("passed").all()


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
    dates = pd.date_range("2025-01-02", periods=4, freq="B")
    validation = pd.DataFrame(
        {
            "fold": [0, 1],
            "model_name": ["Equal Weight", "Equal Weight"],
            "test_start": [dates[0], dates[2]],
            "test_end": [dates[1], dates[3]],
            "test_observations": [2, 2],
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


def test_walk_forward_comparison_rejects_shortened_or_nonfinite_oos_path():
    dates = pd.date_range("2025-01-02", periods=2, freq="B")
    validation = pd.DataFrame(
        {
            "fold": [0],
            "model_name": ["Equal Weight"],
            "test_start": [dates[0]],
            "test_end": [dates[1]],
            "test_observations": [2],
            "cagr": [0.0],
            "annualized_return": [0.0],
            "annualized_volatility": [0.0],
            "sharpe": [0.0],
            "sortino": [0.0],
            "max_drawdown": [0.0],
            "cvar_95": [0.0],
            "turnover": [1.0],
        }
    )
    shortened = pd.DataFrame(
        {
            "Date": [dates[0]],
            "fold": [0],
            "model_name": ["Equal Weight"],
            "return": [0.01],
        }
    )
    nonfinite = pd.DataFrame(
        {
            "Date": dates,
            "fold": [0, 0],
            "model_name": ["Equal Weight", "Equal Weight"],
            "return": [0.01, np.nan],
        }
    )

    with pytest.raises(ValueError, match="incomplete or inconsistent"):
        _comparison(validation, shortened, expected_dates=dates)
    with pytest.raises(ValueError, match="non-finite"):
        _comparison(validation, nonfinite, expected_dates=dates)


def test_walk_forward_comparison_rejects_model_specific_oos_dates():
    dates = pd.date_range("2025-01-02", periods=3, freq="B")
    validation = pd.DataFrame(
        [
            {
                "fold": 0,
                "model_name": model,
                "test_start": start,
                "test_end": end,
                "test_observations": 2,
                "cagr": 0.1,
                "annualized_return": 0.1,
                "annualized_volatility": 0.2,
                "sharpe": 0.4,
                "sortino": 0.5,
                "max_drawdown": -0.1,
                "cvar_95": -0.02,
                "turnover": 1.0,
            }
            for model, start, end in [
                ("Equal Weight", dates[0], dates[1]),
                ("GMV", dates[1], dates[2]),
            ]
        ]
    )
    returns_long = pd.DataFrame(
        {
            "Date": [dates[0], dates[1], dates[1], dates[2]],
            "fold": [0, 0, 0, 0],
            "model_name": ["Equal Weight", "Equal Weight", "GMV", "GMV"],
            "return": [0.01, 0.02, 0.01, 0.02],
        }
    )

    with pytest.raises(ValueError, match="identical OOS dates"):
        _comparison(validation, returns_long, expected_dates=dates)


def test_public_walk_forward_defaults_match_canonical_contract():
    parameters = inspect.signature(run_public_data_walk_forward).parameters

    assert parameters["train_window_days"].default == 504
    assert parameters["test_window_days"].default == 21
    assert parameters["step_days"].default == 21
    assert parameters["max_assets"].default == 20
    assert parameters["max_folds"].default is None


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


def test_rebalance_turnover_uses_drifted_pre_trade_weights():
    target = pd.Series({"A": 0.5, "B": 0.5})
    prior_period_returns = pd.DataFrame(
        {"A": [1.0], "B": [0.0]},
        index=pd.to_datetime(["2025-01-02"]),
    )

    pre_trade = _drift_weights_through_returns(target, prior_period_returns)
    turnover = _two_way_turnover(target, pre_trade)

    assert pre_trade["A"] == pytest.approx(2.0 / 3.0)
    assert pre_trade["B"] == pytest.approx(1.0 / 3.0)
    assert turnover == pytest.approx(1.0 / 3.0)


def test_weight_drift_rejects_missing_selected_asset_returns():
    weights = pd.Series({"A": 0.5, "B": 0.5})
    returns = pd.DataFrame(
        {"A": [0.01], "B": [np.nan]},
        index=pd.to_datetime(["2025-01-02"]),
    )

    with pytest.raises(ValueError, match="complete and finite"):
        _drift_weights_through_returns(weights, returns)


def test_walk_forward_cli_forwards_random_seed_and_walk_forward_history_gate(
    monkeypatch,
    tmp_path,
):
    processed = tmp_path / "data" / "processed"
    universe_dir = tmp_path / "data" / "universe"
    processed.mkdir(parents=True)
    universe_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "Date": pd.date_range("2025-01-01", periods=3, freq="B"),
            "A": [0.01, -0.01, 0.02],
        }
    ).to_csv(processed / "global_security_simple_returns_usd.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["A"],
            "sleeve": ["global_equity_us"],
        }
    ).to_csv(
        universe_dir / "current_global_equity_universe.csv",
        index=False,
    )
    pd.DataFrame(
        {
            "ticker": ["A"],
            "issuer_key": ["issuer-a"],
            "sector": ["Sector"],
            "industry": ["Industry"],
            "issuer_country": ["Country"],
        }
    ).to_csv(processed / "global_canonical_security_metadata.csv", index=False)
    pd.DataFrame(
        {
            "Date": pd.date_range("2025-01-01", periods=3, freq="B"),
            "annual_rate": [0.04, 0.04, 0.04],
            "daily_hurdle": [0.0001, 0.0001, 0.0001],
            "proxy": ["^IRX"] * 3,
            "alignment_policy": ["past_only_forward_fill_limit_5_rows"] * 3,
        }
    ).to_csv(processed / "global_risk_free_series.csv", index=False)
    config = tmp_path / "walk.yaml"
    config.write_text(
        "v2:\n"
        "  random_state: 937\n"
        "  minimum_standard_history_observations: 111\n"
        "  minimum_walk_forward_history_observations: 222\n",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class CapturedCall(RuntimeError):
        pass

    def capture_call(*args, **kwargs):
        captured.update(kwargs)
        raise CapturedCall

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        walk_forward_cli,
        "run_public_data_walk_forward",
        capture_call,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_global_walk_forward_validation.py", "--config", str(config)],
    )

    with pytest.raises(CapturedCall):
        walk_forward_cli.main()

    assert captured["random_state"] == 937
    assert captured["minimum_standard_observations"] == 222


def test_walk_forward_summary_does_not_label_diagnostic_model_as_best_model():
    dates = pd.date_range("2025-01-02", periods=2, freq="B")
    validation = pd.DataFrame(
        {
            "fold": [0, 0],
            "model_name": ["Equal Weight", "Black-Litterman"],
            "test_start": [dates[0], dates[0]],
            "test_end": [dates[1], dates[1]],
            "test_observations": [2, 2],
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
    returns_long = pd.DataFrame(
        {
            "Date": [dates[0], dates[1], dates[0], dates[1]],
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
