import json
from pathlib import Path

import numpy as np
import pandas as pd

from project.pipeline import _write_covariance_model_comparison
from project.research import (
    ALLOWED_FINAL_LABELS,
    ALLOWED_PROMOTION_DECISIONS,
    ALLOWED_RESEARCH_EVIDENCE_CLASSES,
    ChallengerConfig,
    run_champion_challenger_research,
)


def _synthetic_returns(n_days: int = 150) -> pd.DataFrame:
    rng = np.random.default_rng(321)
    dates = pd.date_range("2021-01-01", periods=n_days, freq="B")
    values = rng.normal(0.0002, 0.007, size=(n_days, 6))
    values[:, 0] += np.linspace(-0.0001, 0.0007, n_days)
    values[:, 3] += 0.00015
    return pd.DataFrame(
        values,
        index=dates,
        columns=["EQ1", "EQ2", "BND1", "CMD1", "REIT1", "BTC1"],
    )


def _class_map() -> dict[str, str]:
    return {
        "EQ1": "us_equity_sectors",
        "EQ2": "international_equity",
        "BND1": "fixed_income",
        "CMD1": "commodities",
        "REIT1": "reits",
        "BTC1": "crypto",
    }


def test_research_alpha_leaderboard_schema_and_allowed_labels(tmp_path):
    config = ChallengerConfig(
        train_window=50,
        rebal_frequency=10,
        max_weight=0.5,
        bootstrap_samples=10,
        bootstrap_block_size=5,
    )
    run_champion_challenger_research(
        tmp_path,
        _synthetic_returns(),
        _class_map(),
        config,
    )

    leaderboard = pd.read_csv(tmp_path / "research_alpha_leaderboard.csv")
    required = {
        "Strategy",
        "Model_Family",
        "League",
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
        "Beats_Equal_Weight_Calmar",
        "Beats_Equal_Weight_After_25bps",
        "Beats_Equal_Weight_After_50bps",
        "Subperiod_Win_Rate",
        "Bootstrap_CAGR_Diff_Lower",
        "Bootstrap_CAGR_Diff_Upper",
        "Bootstrap_Sharpe_Diff_Lower",
        "Bootstrap_Sharpe_Diff_Upper",
        "PBO_or_Overfit_Flag",
        "Evidence_Class",
        "Final_Label",
        "Notes",
    }

    assert required.issubset(leaderboard.columns)
    assert "Equal Weight" in set(leaderboard["Strategy"])
    assert set(leaderboard["Evidence_Class"]).issubset(
        ALLOWED_RESEARCH_EVIDENCE_CLASSES
    )
    assert set(leaderboard["Final_Label"]).issubset(ALLOWED_FINAL_LABELS)


def test_model_league_and_promotion_gate_schema(tmp_path):
    config = ChallengerConfig(
        train_window=50,
        rebal_frequency=10,
        max_weight=0.5,
        bootstrap_samples=10,
        bootstrap_block_size=5,
    )
    run_champion_challenger_research(
        tmp_path,
        _synthetic_returns(),
        _class_map(),
        config,
    )

    league = pd.read_csv(tmp_path / "model_league_summary.csv")
    assert {
        "League",
        "Strategy",
        "Primary_Metric",
        "CAGR",
        "Sharpe",
        "Max_Drawdown",
        "Evidence_Class",
        "Final_Label",
        "Decision_Rule",
        "Reason",
    }.issubset(league.columns)
    assert "Broad Default Champion" in set(league["League"])

    league_json = json.loads((tmp_path / "model_league_summary.json").read_text())
    assert isinstance(league_json, list)
    assert any(row["League"] == "Annual Return Challenger" for row in league_json)

    promotion = pd.read_csv(tmp_path / "model_promotion_gate.csv")
    assert {
        "Strategy",
        "Beats_EW_CAGR",
        "Beats_EW_Sharpe",
        "Beats_EW_Calmar",
        "Survives_25bps",
        "Survives_50bps",
        "Subperiod_Win_Rate",
        "Bootstrap_CAGR_Significant",
        "Bootstrap_Sharpe_Significant",
        "Max_Drawdown_Penalty",
        "Turnover_Level",
        "Overfit_Flag",
        "Promotion_Decision",
        "Reason",
    }.issubset(promotion.columns)
    assert set(promotion["Promotion_Decision"]).issubset(ALLOWED_PROMOTION_DECISIONS)


def test_asset_class_momentum_forensic_output_schemas(tmp_path):
    config = ChallengerConfig(
        train_window=50,
        rebal_frequency=10,
        max_weight=0.5,
        bootstrap_samples=10,
        bootstrap_block_size=5,
    )
    run_champion_challenger_research(
        tmp_path,
        _synthetic_returns(),
        _class_map(),
        config,
    )

    recompute = pd.read_csv(
        tmp_path / "asset_class_momentum_metric_recompute_check.csv"
    )
    assert {
        "Strategy",
        "Metric",
        "Summary_Value",
        "Recomputed_Value",
        "Absolute_Diff",
        "Matches",
        "Tolerance",
        "Source",
        "Conclusion",
    }.issubset(recompute.columns)
    assert not recompute.empty
    assert recompute["Matches"].all()

    weight_audit = pd.read_csv(tmp_path / "asset_class_momentum_weight_audit.csv")
    assert {
        "Date",
        "Strategy",
        "Is_Rebalance_Date",
        "Asset_Count",
        "Nonzero_Weight_Count",
        "Weight_Sum",
        "Min_Weight",
        "Max_Weight",
        "Long_Only",
        "Sum_To_One",
        "Cap_Check_Applies",
        "Max_Weight_Cap",
        "Cap_Respected_On_Rebalance",
        "Top_Ticker",
        "Top_Asset_Class",
        "Top_Weight",
    }.issubset(weight_audit.columns)
    assert not weight_audit.empty
    assert weight_audit["Long_Only"].all()
    assert weight_audit["Sum_To_One"].all()


def test_covariance_model_comparison_schema(tmp_path):
    tickers = ["A", "B", "C"]
    cov_results = {
        "Ledoit-Wolf": {
            "covariance": pd.DataFrame(
                [[0.01, 0.002, 0.001], [0.002, 0.02, 0.003], [0.001, 0.003, 0.03]],
                index=tickers,
                columns=tickers,
            ),
            "correlation": pd.DataFrame(
                [[1.0, 0.14, 0.06], [0.14, 1.0, 0.12], [0.06, 0.12, 1.0]],
                index=tickers,
                columns=tickers,
            ),
            "shrinkage": 0.2,
        },
        "EWMA (hl=63)": {
            "covariance": pd.DataFrame(
                np.eye(3) * 0.02, index=tickers, columns=tickers
            ),
            "correlation": pd.DataFrame(np.eye(3), index=tickers, columns=tickers),
        },
    }

    comparison = _write_covariance_model_comparison(tmp_path, cov_results)

    assert (tmp_path / "covariance_model_comparison.csv").exists()
    assert {
        "Method",
        "Annualized_Average_Variance",
        "Mean_Correlation",
        "Condition_Number",
        "Shrinkage",
        "Included_In_Current_Risk_Engine",
        "Current_Use",
        "Notes",
    }.issubset(comparison.columns)
    assert "EWMA (hl=63)" in set(comparison["Method"])


def test_research_docs_and_readme_do_not_overclaim():
    required_docs = [
        "docs/research/research_grounded_quantverse_architecture.md",
        "docs/research/literature_to_quantverse_implementation_matrix.md",
        "docs/research/model_league_system.md",
        "docs/research/risk_covariance_upgrade_plan.md",
        "docs/research/ml_ai_quantverse_strategy.md",
        "docs/research/validation_hardening_plan.md",
        "docs/research/asset_class_momentum_forensic_audit.md",
    ]
    for filename in required_docs:
        assert Path(filename).exists()

    ml_doc = Path("docs/research/ml_ai_quantverse_strategy.md").read_text(
        encoding="utf-8"
    )
    assert "not production allocation engines" in ml_doc
    assert "not autonomous portfolio managers" in ml_doc

    readme = Path("README.md").read_text(encoding="utf-8").lower()
    banned = [
        "guarantees superior return",
        "ai predicts the market",
        "lstm beats the market",
        "llm beats the market",
        "production trading system",
    ]
    assert all(phrase not in readme for phrase in banned)
