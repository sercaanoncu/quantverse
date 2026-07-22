import json
from types import SimpleNamespace

import pandas as pd

import scripts.run_quantverse_v2_demo as demo


def test_final_model_is_not_fabricated_when_league_is_empty_or_ineligible():
    assert demo._final_model(pd.DataFrame()) == "not_available"
    blocked = pd.DataFrame(
        {
            "model_name": ["Policy Constrained"],
            "constraints_pass": [False],
            "actual_status": ["blocked_by_implementation"],
            "sharpe": [0.0],
            "cagr": [0.0],
        }
    )
    assert demo._final_model(blocked) == "not_available"


def test_v2_demo_summary_schema_and_random_percentile(tmp_path, monkeypatch):
    processed = tmp_path / "data" / "processed"
    universe_dir = tmp_path / "data" / "universe"
    processed.mkdir(parents=True)
    universe_dir.mkdir(parents=True)
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "PROCESSED", processed)
    monkeypatch.setattr(
        demo, "SUMMARY_PATH", processed / "quantverse_v2_demo_summary.json"
    )

    pd.DataFrame({"ticker": ["AAA", "BBB"]}).to_csv(
        universe_dir / "current_global_equity_universe.csv", index=False
    )
    pd.DataFrame({"Date": ["2024-01-01"], "AAA": [0.01], "BBB": [0.02]}).to_csv(
        processed / "global_security_simple_returns_usd.csv", index=False
    )
    pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "selection_flag": [True, False],
        }
    ).to_csv(processed / "global_stock_scores.csv", index=False)
    pd.DataFrame({"ticker": ["AAA"], "horizon": ["12M"]}).to_csv(
        processed / "global_stock_return_forecasts.csv", index=False
    )
    pd.DataFrame(
        {
            "model_name": ["Random Portfolios", "Equal Weight"],
            "actual_status": ["benchmark_only", "benchmark_only"],
            "constraints_pass": [True, True],
            "sharpe": [0.5, 0.8],
            "cagr": [0.05, 0.08],
        }
    ).to_csv(processed / "global_portfolio_league.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight", "Equal Weight"],
            "ticker": ["AAA", "BBB"],
            "weight": [0.5, 0.5],
        }
    ).to_csv(processed / "global_portfolio_league_weights.csv", index=False)
    pd.DataFrame(
        {
            "model_name": ["Equal Weight"],
            "annualized_return": [0.10],
            "annualized_volatility": [0.20],
            "cvar_95": [-0.03],
        }
    ).to_csv(processed / "global_portfolio_risk_report.csv", index=False)
    pd.DataFrame({"Sharpe": [0.1, 0.7, 0.9, 1.2]}).to_csv(
        processed / "global_master_random_portfolio_benchmark.csv", index=False
    )
    (processed / "global_walk_forward_summary.json").write_text(
        json.dumps(
            {
                "walk_forward_status": "completed_public_data_current_universe",
                "best_model": "Equal Weight",
                "equal_weight_comparison": {
                    "beats_equal_weight_avg_sharpe": False,
                    "beats_equal_weight_avg_cagr": False,
                },
            }
        ),
        encoding="utf-8",
    )
    (processed / "global_master_decision_summary.json").write_text(
        json.dumps({"promotion_decision": "not promoted", "reason": "unit"}),
        encoding="utf-8",
    )

    summary = demo.build_demo_summary()

    assert summary["run_status"] == "completed"
    assert summary["universe_rows"] == 2
    assert summary["assets_with_returns"] == 2
    assert summary["stocks_selected"] == 1
    assert summary["final_selected_model"] == "Equal Weight"
    assert summary["promotion_decision"] == "not promoted"
    assert summary["random_portfolio_percentile"] == 0.5


def test_v2_pipeline_builds_robustness_evidence_before_model_selection():
    steps = demo._pipeline_steps("unit.yaml")
    scripts = [step[0] for step in steps]

    assert scripts.index("scripts/build_global_returns_matrix.py") < scripts.index(
        "scripts/run_global_statistical_diagnostics.py"
    )
    assert scripts.index("scripts/run_global_statistical_diagnostics.py") < (
        scripts.index("scripts/build_global_stock_scores.py")
    )
    assert scripts.index("scripts/run_global_walk_forward_validation.py") < (
        scripts.index("scripts/run_global_robustness_analysis.py")
    )
    assert scripts.index("scripts/run_global_robustness_analysis.py") < (
        scripts.index("scripts/build_global_model_selection_report.py")
    )
    returns_step = next(
        step for step in steps if step[0] == "scripts/build_global_returns_matrix.py"
    )
    master_step = next(
        step for step in steps if step[0] == "scripts/run_global_master_portfolio.py"
    )
    assert (
        returns_step[returns_step.index("--master-config") + 1]
        == master_step[master_step.index("--config") + 1]
    )


def test_v2_demo_rewrites_completed_summary_when_report_step_fails(
    monkeypatch, tmp_path
):
    written = []
    calls = iter(
        [
            SimpleNamespace(returncode=0),
            SimpleNamespace(returncode=7),
        ]
    )
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "_pipeline_steps", lambda _config: [])
    monkeypatch.setattr(
        demo,
        "build_demo_summary",
        lambda: {"run_status": "completed", "run_id": "unit-run"},
    )
    monkeypatch.setattr(demo, "_write_summary", lambda payload: written.append(payload))
    monkeypatch.setattr(demo.subprocess, "run", lambda *args, **kwargs: next(calls))
    monkeypatch.setattr(
        demo.sys,
        "argv",
        ["run_quantverse_v2_demo.py", "--config", "unit.yaml"],
    )

    assert demo.main() == 7
    assert written[0]["run_status"] == "completed"
    assert written[-1]["run_status"] == "failed"
    assert (
        written[-1]["failed_step"]
        == "scripts/build_quantverse_portfolio_analysis.py --config unit.yaml"
    )
