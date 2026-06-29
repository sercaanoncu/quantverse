import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from project.data_pipeline.security_universe import (
    REQUIRED_UNIVERSE_COLUMNS,
    detect_missing_market_caps,
    detect_stablecoin_like_assets,
    detect_survivorship_bias_risk,
    filter_included_investable_assets,
    load_security_universe,
    split_universe_by_sleeve,
    validate_security_universe_schema,
)
from project.research.global_stock_selection import (
    build_equal_weight_portfolio,
    build_inverse_volatility_portfolio,
    build_min_cvar_portfolio,
    build_shrinkage_max_sharpe_portfolio,
    build_stock_selection_promotion_gate,
    cluster_assets_by_correlation,
    compare_candidate_to_equal_weight_and_random,
    evaluate_portfolio_return_series,
    select_assets_by_cluster,
    simulate_random_portfolios,
)


def _valid_universe() -> pd.DataFrame:
    rows = []
    sleeves = ["global_equity_us", "global_equity_europe", "global_equity_japan"]
    for idx in range(9):
        rows.append(
            {
                "ticker": f"STK{idx}",
                "name": f"Stock {idx}",
                "sleeve": sleeves[idx % len(sleeves)],
                "region": "global",
                "country": "Testland",
                "exchange": "TEST",
                "currency": "USD",
                "asset_type": "equity",
                "sector": "Sector",
                "industry": "Industry",
                "market_cap_usd": 100_000_000_000 - idx,
                "market_cap_rank": idx + 1,
                "as_of_date": "2026-01-31",
                "source": "unit test sourced file",
                "data_provider": "unit_test",
                "investable": True,
                "benchmark_only": False,
                "signal_only": False,
                "include": True,
                "proxy_type": "direct_listing",
                "notes": "point-in-time test row",
            }
        )
    return pd.DataFrame(rows, columns=REQUIRED_UNIVERSE_COLUMNS)


def _returns(n_days: int = 120, n_assets: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.date_range("2021-01-01", periods=n_days, freq="B")
    factors = rng.normal(0.0003, 0.008, size=(n_days, 3))
    values = []
    for idx in range(n_assets):
        factor = factors[:, idx % 3]
        noise = rng.normal(0.0001 + idx * 0.00001, 0.003, size=n_days)
        values.append(factor + noise)
    return pd.DataFrame(
        np.column_stack(values),
        index=dates,
        columns=[f"STK{idx}" for idx in range(n_assets)],
    )


def test_universe_schema_validation_accepts_valid_data():
    validate_security_universe_schema(_valid_universe())


def test_universe_schema_validation_rejects_missing_required_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        validate_security_universe_schema(_valid_universe().drop(columns=["ticker"]))


def test_investable_filtering_and_sleeve_splitting_work():
    universe = _valid_universe()
    universe.loc[0, "benchmark_only"] = True
    filtered = filter_included_investable_assets(universe)
    split = split_universe_by_sleeve(universe)

    assert "STK0" not in set(filtered["ticker"])
    assert "global_equity_us" in split
    assert len(split["global_equity_us"]) == 3


def test_missing_market_cap_and_survivorship_warnings_trigger():
    universe = _valid_universe()
    universe["market_cap_usd"] = universe["market_cap_usd"].astype(object)
    universe.loc[0, "market_cap_usd"] = ""
    universe.loc[1, "source"] = "current constituents manual template"

    missing = detect_missing_market_caps(universe)
    survivorship = detect_survivorship_bias_risk(universe)

    assert set(missing["ticker"]) == {"STK0"}
    assert "STK1" in set(survivorship["ticker"])


def test_stablecoin_like_detection_works():
    universe = _valid_universe()
    stable = universe.iloc[[0]].copy()
    stable.loc[:, "ticker"] = "USDT-USD"
    stable.loc[:, "name"] = "Tether USD"
    stable.loc[:, "sleeve"] = "crypto"
    stable.loc[:, "asset_type"] = "crypto"
    universe = pd.concat([universe, stable], ignore_index=True)

    flagged = detect_stablecoin_like_assets(universe)

    assert set(flagged["ticker"]) == {"USDT-USD"}


def test_asset_selection_count_and_cluster_diversification():
    returns = _returns()
    selected = select_assets_by_cluster(returns, min_holdings=6, max_holdings=6)
    clusters = cluster_assets_by_correlation(returns)

    assert 6 == len(selected)
    assert clusters.loc[selected].nunique() >= 2


def test_portfolio_builders_return_long_only_weights_that_sum_to_one():
    returns = _returns(n_assets=8)
    tickers = list(returns.columns[:5])
    builders = [
        build_equal_weight_portfolio,
        build_inverse_volatility_portfolio,
        build_shrinkage_max_sharpe_portfolio,
        build_min_cvar_portfolio,
    ]

    for builder in builders:
        weights = (
            builder(returns, tickers, max_weight=0.40)
            if builder != build_equal_weight_portfolio
            else builder(returns, tickers)
        )
        assert weights.sum() == pytest.approx(1.0)
        assert (weights >= -1e-10).all()
        assert weights.max() <= 0.40 + 1e-8


def test_random_portfolio_simulation_is_reproducible_and_weights_sum_to_one():
    returns = _returns(n_assets=6)
    first = simulate_random_portfolios(
        returns, n_portfolios=25, max_weight=0.40, random_state=123
    )
    second = simulate_random_portfolios(
        returns, n_portfolios=25, max_weight=0.40, random_state=123
    )
    weight_cols = [column for column in first if column.startswith("weight_")]

    pd.testing.assert_frame_equal(first, second)
    assert np.allclose(first[weight_cols].sum(axis=1), 1.0)


def test_promotion_gate_can_return_promoted_and_not_promoted():
    promoted_metrics = {
        "Beats_Equal_Weight_CAGR": True,
        "Beats_Equal_Weight_Sharpe": True,
        "Volatility_Ratio_vs_Equal_Weight": 1.0,
        "Max_Drawdown_Diff_vs_Equal_Weight": 0.0,
        "CVaR_Diff_vs_Equal_Weight": 0.0,
        "Random_Sharpe_Percentile": 0.95,
        "CAGR_Diff_vs_Equal_Weight": 0.05,
        "Turnover": 0.40,
        "Transaction_Cost_Drag": 0.001,
    }
    rejected_metrics = {**promoted_metrics, "Random_Sharpe_Percentile": 0.20}
    high_cost_metrics = {**promoted_metrics, "Transaction_Cost_Drag": 0.01}

    assert build_stock_selection_promotion_gate(promoted_metrics)["Promoted"] is True
    assert (
        build_stock_selection_promotion_gate(rejected_metrics)["Promotion_Decision"]
        == "not promoted"
    )
    high_cost_gate = build_stock_selection_promotion_gate(high_cost_metrics)
    assert high_cost_gate["Promotion_Decision"] == "not promoted"
    assert "transaction-cost gate" in high_cost_gate["Failed_Gates"]


def test_candidate_comparison_adds_equal_weight_and_random_benchmark_fields():
    returns = _returns(n_assets=6)
    candidate = evaluate_portfolio_return_series(returns.iloc[:, :3].mean(axis=1))
    equal_weight = evaluate_portfolio_return_series(returns.mean(axis=1))
    randoms = simulate_random_portfolios(returns, n_portfolios=30, max_weight=0.40)
    comparison = compare_candidate_to_equal_weight_and_random(
        candidate, equal_weight, randoms
    )

    assert "Beats_Equal_Weight_CAGR" in comparison
    assert "Random_Sharpe_Percentile" in comparison


def test_cli_exits_zero_when_only_template_universe_exists(tmp_path):
    config_path = tmp_path / "config.yaml"
    output_dir = tmp_path / "processed"
    config_path.write_text(
        "\n".join(
            [
                "universe_path: data/universe/global_equity_top100_template.csv",
                f"output_dir: {output_dir.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_global_stock_selection.py",
            "--config",
            str(config_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "No populated investable universe found" in result.stdout


def test_cli_outputs_stable_schema_with_synthetic_returns(tmp_path):
    universe = _valid_universe()
    returns = _returns(n_assets=9)
    universe_path = tmp_path / "universe.csv"
    returns_path = tmp_path / "returns.csv"
    config_path = tmp_path / "config.yaml"
    output_dir = tmp_path / "processed"
    universe.to_csv(universe_path, index=False)
    returns.to_csv(returns_path, index_label="Date")
    config_path.write_text(
        "\n".join(
            [
                f"universe_path: {universe_path.as_posix()}",
                f"returns_path: {returns_path.as_posix()}",
                f"output_dir: {output_dir.as_posix()}",
                "selection:",
                "  min_holdings: 4",
                "  max_holdings: 6",
                "  max_weight: 0.30",
                "  random_state: 42",
                "random_portfolios:",
                "  n_portfolios: 20",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_global_stock_selection.py",
            "--config",
            str(config_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    gate = pd.read_csv(output_dir / "global_stock_selection_promotion_gate.csv")
    selected = pd.read_csv(output_dir / "global_stock_selection_selected_assets.csv")
    weights = pd.read_csv(output_dir / "global_stock_selection_candidate_weights.csv")
    assert {
        "Promotion_Decision",
        "Reason",
        "Random_Sharpe_Percentile",
        "Turnover",
        "Transaction_Cost_Drag",
        "Max_Transaction_Cost_Drag_Allowed",
    }.issubset(gate.columns)
    assert {"Ticker", "Selection_Score", "Sharpe"}.issubset(selected.columns)
    assert {"Ticker", "Weight"}.issubset(weights.columns)
