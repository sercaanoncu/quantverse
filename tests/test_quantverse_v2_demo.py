import json

import pandas as pd

import scripts.run_quantverse_v2_demo as demo


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
