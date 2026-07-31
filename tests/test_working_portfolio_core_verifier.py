from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.qa.verify_working_portfolio_core import (
    _independent_metrics,
    _random_benchmark_check,
)


def test_independent_metric_reference_uses_nonzero_daily_rf():
    dates = pd.date_range("2025-01-02", periods=4, freq="B")
    returns = pd.Series([0.01, -0.005, 0.002, 0.004], index=dates)
    daily_rf = pd.Series(0.0002, index=dates)

    metrics = _independent_metrics(returns, daily_rf)
    expected_volatility = returns.std(ddof=1) * np.sqrt(252)
    expected_sharpe = ((returns - daily_rf).mean() * 252) / expected_volatility

    assert metrics["volatility"] == pytest.approx(expected_volatility)
    assert metrics["sharpe"] == pytest.approx(expected_sharpe)
    assert metrics["max_drawdown"] <= 0.0
    assert metrics["cvar_95"] <= metrics["var_95"]


def test_independent_random_protocol_check_rejects_wrong_cost_rows():
    identity = {
        "run_id": "run",
        "execution_id": "run",
        "data_as_of_date": "2026-07-21",
        "universe_snapshot_id": "universe",
        "data_snapshot_id": "data",
        "config_hash": "config",
        "input_fingerprint": "input",
    }
    provenance = {
        **identity,
        "benchmark_scope": "walk_forward_oos_net",
        "provenance_status": "verified_same_protocol",
        "train_window_days": 504,
        "test_window_days": 21,
        "step_days": 21,
        "max_assets": 20,
        "max_weight": 0.10,
        "transaction_cost_bps": 10.0,
        "oos_dates_match": True,
        "model_oos_dates_hash": "dates",
        "random_oos_dates_hash": "dates",
        "protocol_hash": "protocol",
        "fold_schedule_hash": "folds",
        "selected_universe_by_fold_hash": "universe-by-fold",
    }
    frame = pd.DataFrame(
        [
            {
                "benchmark_scope": "walk_forward_oos_net",
                "benchmark_provenance_status": "verified_same_protocol",
                "protocol_hash": "protocol",
                "fold_schedule_hash": "folds",
                "selected_universe_by_fold_hash": "universe-by-fold",
                "model_oos_dates_hash": "dates",
                "random_oos_dates_hash": "dates",
                "transaction_cost_bps": 25.0,
                "max_weight": 0.10,
            }
        ]
    )
    config = {
        "walk_forward_train_days": 504,
        "walk_forward_test_days": 21,
        "walk_forward_step_days": 21,
        "walk_forward_max_assets": 20,
        "max_weight": 0.10,
        "transaction_cost_bps": 10.0,
    }

    passed, details = _random_benchmark_check(frame, provenance, identity, config)

    assert passed is False
    assert details["rows_match_provenance"] is False
