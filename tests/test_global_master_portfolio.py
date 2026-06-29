import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from project.data_pipeline.security_universe import REQUIRED_UNIVERSE_COLUMNS
from project.research.global_master_portfolio import run_master_portfolio_research


def _returns(n_assets: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(21)
    return pd.DataFrame(
        rng.normal(0.0005, 0.01, size=(160, n_assets)),
        index=pd.date_range("2024-01-01", periods=160, freq="B"),
        columns=[f"AST{i}" for i in range(n_assets)],
    )


def _metadata(n_assets: int = 8) -> pd.DataFrame:
    sleeves = [
        "global_equity_us",
        "global_equity_europe",
        "crypto",
        "commodity_real_assets",
        "defensive_bonds_cash",
    ]
    rows = []
    for idx in range(n_assets):
        rows.append(
            {
                "ticker": f"AST{idx}",
                "name": f"Asset {idx}",
                "sleeve": sleeves[idx % len(sleeves)],
                "region": "global",
                "country": "Test",
                "exchange": "TEST",
                "currency": "USD",
                "asset_type": "equity",
                "sector": "",
                "industry": "",
                "market_cap_usd": 1000 - idx,
                "market_cap_rank": idx + 1,
                "as_of_date": "2026-01-31",
                "source": "unit",
                "data_provider": "unit",
                "investable": True,
                "benchmark_only": False,
                "signal_only": False,
                "include": True,
                "proxy_type": "direct_listing",
                "notes": "unit",
            }
        )
    return pd.DataFrame(rows, columns=REQUIRED_UNIVERSE_COLUMNS)


def test_master_allocator_outputs_weights_comparison_and_promotion_gate():
    result = run_master_portfolio_research(
        _returns(),
        _metadata(),
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=5,
    )
    weights = result["candidate_weights"]
    comparison = result["model_comparison"]
    gate = result["promotion_gate"]

    assert np.allclose(weights.groupby("Model")["Weight"].sum().to_numpy(), 1.0)
    assert weights["Weight"].max() <= 0.40 + 1e-8
    assert {"Equal Weight", "Black-Litterman"}.issubset(set(comparison["Model"]))
    assert gate["Promotion_Decision"].iloc[0] in {"promoted", "not promoted"}
    assert 5 <= result["decision_summary"]["selected_holdings"] <= 6


def test_master_random_benchmark_is_reproducible():
    first = run_master_portfolio_research(
        _returns(),
        _metadata(),
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=8,
    )["random_portfolio_benchmark"]
    second = run_master_portfolio_research(
        _returns(),
        _metadata(),
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=8,
    )["random_portfolio_benchmark"]

    pd.testing.assert_frame_equal(first, second)


def test_orchestrator_exits_zero_when_inputs_are_missing(tmp_path):
    config = tmp_path / "global_quant.yaml"
    missing_step = tmp_path / "missing.yaml"
    config.write_text(
        "\n".join(
            [
                f"current_universe_config: {missing_step.as_posix()}",
                f"returns_matrix_config: {missing_step.as_posix()}",
                f"master_portfolio_config: {missing_step.as_posix()}",
                f"projection_config: {missing_step.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_global_quant_research.py",
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
