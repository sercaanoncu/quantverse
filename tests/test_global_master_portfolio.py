import subprocess
import sys
import json

import numpy as np
import pandas as pd
import pytest

import project.research.global_master_portfolio as master_portfolio
import scripts.run_global_quant_research as global_orchestrator
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
    assert gate["Promotion_Decision"].iloc[0] == "not promoted"
    assert not result["decision_summary"]["institutional_promotion_eligible"]
    assert (
        result["decision_summary"]["point_in_time_membership_status"]
        == "unavailable_current_universe_only"
    )
    assert 5 <= result["decision_summary"]["selected_holdings"] <= 6


def test_master_promotion_gate_uses_configured_cost_and_threshold_contract():
    result = run_master_portfolio_research(
        _returns(),
        _metadata(),
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=5,
        promotion_gate_config={
            "random_percentile_threshold": 0.95,
            "volatility_relative_limit": 1.10,
            "max_drawdown_penalty": 0.02,
            "cvar_penalty": 0.01,
            "estimated_initial_turnover": 0.25,
            "transaction_cost_bps": 20.0,
            "max_turnover": 0.50,
            "max_transaction_cost_drag": 0.001,
        },
    )

    gate = result["promotion_gate"].iloc[0]

    assert gate["Turnover"] == pytest.approx(0.25)
    assert gate["Transaction_Cost_Bps"] == pytest.approx(20.0)
    assert gate["Transaction_Cost_Drag"] == pytest.approx(0.0005)
    assert gate["Random_Percentile_Threshold"] == pytest.approx(0.95)
    assert gate["Max_Turnover_Allowed"] == pytest.approx(0.50)
    assert gate["Max_Transaction_Cost_Drag_Allowed"] == pytest.approx(0.001)


def test_master_promotion_gate_rejects_invalid_configured_threshold():
    with pytest.raises(ValueError, match="random_percentile_threshold"):
        run_master_portfolio_research(
            _returns(),
            _metadata(),
            min_holdings=5,
            max_holdings=6,
            max_weight=0.40,
            n_random_portfolios=25,
            random_state=5,
            promotion_gate_config={"random_percentile_threshold": 1.01},
        )


def test_master_outputs_do_not_overwrite_canonical_risk_stress_evidence(tmp_path):
    result = run_master_portfolio_research(
        _returns(),
        _metadata(),
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=5,
    )
    canonical = tmp_path / "global_stress_test_results.csv"
    canonical.write_text("run_id,scenario\nrisk-run,equity_selloff\n", encoding="utf-8")
    canonical_projection = tmp_path / "global_monte_carlo_projection.csv"
    canonical_projection.write_text(
        "run_id,terminal_value\nprojection-run,1.1\n",
        encoding="utf-8",
    )

    master_portfolio.write_master_portfolio_outputs(result, tmp_path)

    assert canonical.read_text(encoding="utf-8") == (
        "run_id,scenario\nrisk-run,equity_selloff\n"
    )
    assert (tmp_path / "global_master_stress_test_results.csv").exists()
    assert canonical_projection.read_text(encoding="utf-8") == (
        "run_id,terminal_value\nprojection-run,1.1\n"
    )
    assert (tmp_path / "global_master_monte_carlo_projection.csv").exists()


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


def test_black_litterman_selected_subset_is_diagnostic_only():
    metadata = _metadata()
    metadata["source_url"] = "https://example.com/source"
    result = run_master_portfolio_research(
        _returns(),
        metadata,
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=5,
    )
    black_litterman = (
        result["model_comparison"]
        .loc[result["model_comparison"]["Model"].eq("Black-Litterman")]
        .iloc[0]
    )

    assert black_litterman["Status"] == "computed_diagnostic_only"
    assert (
        result["decision_summary"]["black_litterman_prerequisite_status"]
        == "selected_subset_priors_available_diagnostic_only"
    )


def test_master_excludes_unverified_crypto_and_reports_infeasible_policy_model():
    metadata = _metadata()
    returns = _returns()
    returns.loc[returns.index[10], "AST2"] = 500.0

    result = run_master_portfolio_research(
        returns,
        metadata,
        min_holdings=5,
        max_holdings=6,
        max_weight=0.40,
        n_random_portfolios=25,
        random_state=5,
    )

    selected = set(result["selected_assets"]["ticker"])
    policy = (
        result["model_comparison"]
        .loc[result["model_comparison"]["Model"].eq("Policy Constrained")]
        .iloc[0]
    )

    assert "AST2" not in selected
    assert "AST7" not in selected
    assert policy["Status"] == "infeasible_constraints"


def test_cluster_balanced_weights_respect_cap_after_redistribution(monkeypatch):
    returns = _returns(n_assets=12)
    clusters = pd.Series(
        [1] + [2] * 11,
        index=returns.columns,
        name="Cluster",
    )
    monkeypatch.setattr(
        master_portfolio,
        "cluster_assets_by_correlation",
        lambda _frame: clusters,
    )

    weights = master_portfolio._cluster_balanced_weights(returns, max_weight=0.10)

    assert weights.sum() == pytest.approx(1.0)
    assert weights.max() <= 0.10 + 1e-8


def test_orchestrator_rebuilds_feature_eligibility_before_master(tmp_path, monkeypatch):
    universe_path = tmp_path / "universe.csv"
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "sleeve": "global_equity_us",
                "include": True,
                "investable": True,
                "benchmark_only": False,
                "signal_only": False,
            }
        ]
    ).to_csv(universe_path, index=False)
    current_config = tmp_path / "current.yaml"
    returns_config = tmp_path / "returns.yaml"
    master_config = tmp_path / "master.yaml"
    projection_config = tmp_path / "projection.yaml"
    config = tmp_path / "global.yaml"
    current_config.write_text(
        f"output_universe_path: {universe_path.as_posix()}\n", encoding="utf-8"
    )
    for path in [returns_config, master_config, projection_config]:
        path.write_text("{}\n", encoding="utf-8")
    config.write_text(
        "\n".join(
            [
                f"current_universe_config: {current_config.as_posix()}",
                f"returns_matrix_config: {returns_config.as_posix()}",
                f"master_portfolio_config: {master_config.as_posix()}",
                f"projection_config: {projection_config.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    calls = []

    def record_step(script, step_config):
        calls.append((script, str(step_config)))
        return 0

    monkeypatch.setattr(global_orchestrator, "_run_step", record_step)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_global_quant_research.py", "--config", str(config)],
    )

    assert global_orchestrator.main() == 0
    scripts = [script for script, _ in calls]
    assert scripts.index("scripts/build_global_returns_matrix.py") < scripts.index(
        "scripts/build_global_stock_scores.py"
    )
    assert scripts.index("scripts/build_global_stock_scores.py") < scripts.index(
        "scripts/run_global_master_portfolio.py"
    )


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


def test_orchestrator_blocks_promotion_without_sourced_equity_universe(tmp_path):
    output_dir = tmp_path / "processed"
    current_config = tmp_path / "current_universe.yaml"
    returns_config = tmp_path / "returns.yaml"
    master_config = tmp_path / "master.yaml"
    projection_config = tmp_path / "projection.yaml"
    orchestrator_config = tmp_path / "global_quant.yaml"
    current_universe = tmp_path / "current_global_equity_universe.csv"
    current_config.write_text(
        "\n".join(
            [
                "mode: csv",
                "source_files:",
                f"  global_equity_us: {(tmp_path / 'missing.csv').as_posix()}",
                f"output_universe_path: {current_universe.as_posix()}",
                f"summary_path: {(tmp_path / 'summary.csv').as_posix()}",
                f"missing_market_caps_path: {(tmp_path / 'missing_caps.csv').as_posix()}",
                f"bias_warnings_path: {(tmp_path / 'bias.csv').as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    returns_config.write_text(
        f"output_dir: {output_dir.as_posix()}\n", encoding="utf-8"
    )
    master_config.write_text(f"output_dir: {output_dir.as_posix()}\n", encoding="utf-8")
    projection_config.write_text(
        f"output_dir: {output_dir.as_posix()}\n",
        encoding="utf-8",
    )
    orchestrator_config.write_text(
        "\n".join(
            [
                f"current_universe_config: {current_config.as_posix()}",
                f"returns_matrix_config: {returns_config.as_posix()}",
                f"master_portfolio_config: {master_config.as_posix()}",
                f"projection_config: {projection_config.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_global_quant_research.py",
            "--config",
            str(orchestrator_config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    decision = json.loads(
        (output_dir / "global_master_decision_summary.json").read_text(encoding="utf-8")
    )
    assert result.returncode == 0
    assert "sourced global equity universe is missing" in result.stdout
    assert "promoted" not in {
        line.strip().lower() for line in result.stdout.splitlines()
    }
    assert decision["status"] == "insufficient_global_equity_universe"
    assert decision["promotion_decision"] == "insufficient_inputs"


def test_master_runner_blocks_proxy_only_promotion(tmp_path):
    output_dir = tmp_path / "processed"
    returns_path = tmp_path / "returns.csv"
    proxy_universe = tmp_path / "proxy_universe.csv"
    config = tmp_path / "master.yaml"
    returns = _returns(n_assets=2).rename(columns={"AST0": "GLD", "AST1": "SHY"})
    returns.to_csv(returns_path, index_label="Date")
    proxy_metadata = _metadata(n_assets=2)
    proxy_metadata["ticker"] = ["GLD", "SHY"]
    proxy_metadata["sleeve"] = ["commodity_real_assets", "defensive_bonds_cash"]
    proxy_metadata.to_csv(proxy_universe, index=False)
    config.write_text(
        "\n".join(
            [
                f"returns_path: {returns_path.as_posix()}",
                "universe_paths:",
                f"  - {(tmp_path / 'missing_equity.csv').as_posix()}",
                f"  - {proxy_universe.as_posix()}",
                f"output_dir: {output_dir.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_global_master_portfolio.py",
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    decision = json.loads(
        (output_dir / "global_master_decision_summary.json").read_text(encoding="utf-8")
    )
    gate = pd.read_csv(output_dir / "global_master_promotion_gate.csv")
    assert result.returncode == 0
    assert "promoted" not in {
        line.strip().lower() for line in result.stdout.splitlines()
    }
    assert decision["promotion_decision"] == "insufficient_inputs"
    assert gate["Promotion_Decision"].iloc[0] == "insufficient_inputs"
