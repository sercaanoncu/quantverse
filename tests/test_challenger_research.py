import json

import numpy as np
import pandas as pd
import pytest

from project.backtest.rebalancing import TransactionCosts
from project.research.challenger import (
    ALLOWED_EVIDENCE_CLASSES,
    ChallengerConfig,
    _asset_class_rotation,
    _cross_asset_momentum,
    _dual_momentum,
    _momentum_tilt,
    _nested_shrunk_max_sharpe,
    _regime_aware_allocation,
    _risk_managed_equal_weight,
    _signal_aware_hrp_lite,
    _time_series_momentum,
    _trend_following_ma,
    _vol_scaled_momentum,
    _walk_forward_strategy,
    run_champion_challenger_research,
)


def _synthetic_returns(n_days: int = 140) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    dates = pd.date_range("2021-01-01", periods=n_days, freq="B")
    base = rng.normal(0.0002, 0.008, size=(n_days, 6))
    trend = np.linspace(-0.0001, 0.0008, n_days)
    base[:, 0] += trend
    base[:, 1] -= trend / 2
    return pd.DataFrame(
        base,
        index=dates,
        columns=["EQ1", "EQ2", "BND1", "CMD1", "REIT1", "CRYPTO1"],
    )


def _class_map() -> dict[str, str]:
    return {
        "EQ1": "us_equity_sectors",
        "EQ2": "international_equity",
        "BND1": "fixed_income",
        "CMD1": "commodities",
        "REIT1": "reits",
        "CRYPTO1": "crypto",
    }


def test_challenger_walk_forward_uses_only_past_data():
    returns = _synthetic_returns(80)
    config = ChallengerConfig(train_window=20, rebal_frequency=7, max_weight=0.5)
    observed_windows = []

    def spy_optimizer(train):
        observed_windows.append(train.index.max())
        return pd.Series(1.0 / returns.shape[1], index=returns.columns)

    result = _walk_forward_strategy(
        returns,
        spy_optimizer,
        config,
        TransactionCosts(proportional=0, spread=0, fixed_per_trade=0),
        "Spy",
    )

    turnover = result["turnover"]
    assert not turnover.empty
    for train_end, traded_date in zip(
        observed_windows, pd.to_datetime(turnover["Date"])
    ):
        assert train_end < traded_date


def test_challenger_target_weights_are_long_only_capped_and_fully_invested():
    returns = _synthetic_returns(180)
    class_map = _class_map()
    config = ChallengerConfig(train_window=60, rebal_frequency=10, max_weight=0.5)
    train = returns.iloc[:100]
    strategies = [
        _momentum_tilt,
        _time_series_momentum,
        _cross_asset_momentum,
        _dual_momentum,
        _trend_following_ma,
        _vol_scaled_momentum,
        lambda frame, cfg: _risk_managed_equal_weight(frame, class_map, cfg),
        lambda frame, cfg: _regime_aware_allocation(frame, class_map, cfg),
        lambda frame, cfg: _asset_class_rotation(frame, class_map, cfg),
        lambda frame, cfg: _signal_aware_hrp_lite(frame, class_map, cfg),
        _nested_shrunk_max_sharpe,
    ]

    for strategy in strategies:
        weights = strategy(train, config)
        assert weights.sum() == pytest.approx(1.0)
        assert (weights >= -1e-10).all()
        assert (weights <= config.max_weight + 1e-10).all()


def test_champion_challenger_outputs_have_required_schema(tmp_path):
    returns = _synthetic_returns(130)
    config = ChallengerConfig(
        train_window=50,
        rebal_frequency=10,
        max_weight=0.5,
        bootstrap_samples=12,
        bootstrap_block_size=5,
    )

    run_champion_challenger_research(tmp_path, returns, _class_map(), config)

    summary = pd.read_csv(tmp_path / "challenger_backtest_summary.csv")
    required = {
        "Strategy",
        "CAGR",
        "Annual_Return",
        "Volatility",
        "Sharpe",
        "Sortino",
        "Calmar",
        "Max_Drawdown",
        "Turnover",
        "Transaction_Cost_Drag",
        "Beats_Equal_Weight_CAGR",
        "Beats_Equal_Weight_Sharpe",
        "Evidence_Class",
        "Notes",
    }
    assert required.issubset(summary.columns)
    assert "Equal Weight" in set(summary["Strategy"])
    assert set(summary["Evidence_Class"]).issubset(ALLOWED_EVIDENCE_CLASSES)

    champion = json.loads((tmp_path / "champion_selection_summary.json").read_text())
    assert champion["benchmark"] == "Equal Weight"
    assert champion["primary_metric"] == "out_of_sample_CAGR"
    assert "replace_equal_weight_champion" in champion

    for filename in [
        "challenger_returns.csv",
        "challenger_weights.csv",
        "challenger_turnover.csv",
        "challenger_vs_equal_weight.csv",
        "challenger_subperiod_analysis.csv",
        "challenger_rolling_relative_performance.csv",
        "challenger_cost_robustness.csv",
        "challenger_bootstrap_vs_equal_weight.csv",
        "equal_weight_diagnostic.csv",
        "asset_class_momentum_metric_recompute_check.csv",
        "asset_class_momentum_weight_audit.csv",
        "research_alpha_leaderboard.csv",
        "research_alpha_returns.csv",
        "research_alpha_weights.csv",
        "research_alpha_turnover.csv",
        "research_alpha_vs_equal_weight.csv",
        "model_league_summary.csv",
        "model_league_summary.json",
        "model_promotion_gate.csv",
        "model_overfit_diagnostics.csv",
    ]:
        assert (tmp_path / filename).exists()
