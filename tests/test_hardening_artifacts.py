from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import project.pipeline as pipeline
from project.pipeline import (
    PipelineConfig,
    _benchmark_evidence_class,
    _block_bootstrap_metrics,
    _bootstrap_evidence_strength,
    _cost_sensitivity_interpretation,
    _internal_6040_proxy,
    _ml_confusion_matrix_table,
    _ml_drift_report,
    _population_stability_index,
    _stylized_stress_scenarios,
    _write_benchmark_comparison_artifacts,
    _write_statistical_robustness_artifacts,
    _write_stress_scenario_artifacts,
    _write_transaction_cost_sensitivity_artifacts,
)


def _toy_returns(rows=80):
    index = pd.date_range("2024-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "EQ1": np.linspace(0.001, 0.004, rows),
            "EQ2": np.linspace(0.002, -0.001, rows),
            "BOND": 0.0005 + 0.0001 * np.sin(np.arange(rows)),
        },
        index=index,
    )


def test_stylized_stress_scenarios_have_expected_names():
    names = {scenario["name"] for scenario in _stylized_stress_scenarios()}

    assert {
        "COVID crash stylized",
        "2022 inflation/rate shock stylized",
        "Global risk-off stylized",
        "Equity crash stylized",
        "Bond yield shock stylized",
        "USD strength shock stylized",
        "Crypto crash stylized",
    }.issubset(names)


def test_stress_scenario_output_schema_and_honest_label(tmp_path):
    weights = pd.DataFrame(
        {
            "Equal Weight": {"EQ1": 0.4, "EQ2": 0.4, "BOND": 0.2},
            "HRP": {"EQ1": 0.2, "EQ2": 0.2, "BOND": 0.6},
            "Inv Volatility": {"EQ1": 0.3, "EQ2": 0.3, "BOND": 0.4},
        }
    )
    class_map = {
        "EQ1": "us_equity_sectors",
        "EQ2": "international_equity",
        "BOND": "fixed_income",
    }

    stress = _write_stress_scenario_artifacts(tmp_path, weights, class_map)

    assert len(stress) == 7
    assert "Equal Weight_Impact_%" in stress.columns
    assert "HRP_Impact_%" in stress.columns
    assert "Inv Volatility_Impact_%" in stress.columns
    assert stress["Scenario_Type"].eq("stylized_class_shock").all()
    assert stress["Interpretation"].str.contains("not a historical replay").all()
    assert (tmp_path / "stress_scenarios.csv").exists()


def test_internal_6040_proxy_returns_none_without_bonds():
    returns = _toy_returns()[["EQ1", "EQ2"]]
    class_map = {"EQ1": "us_equity_sectors", "EQ2": "international_equity"}

    assert _internal_6040_proxy(returns, class_map, returns.index) is None


def test_internal_6040_proxy_uses_equity_and_fixed_income():
    returns = _toy_returns()
    class_map = {
        "EQ1": "us_equity_sectors",
        "EQ2": "international_equity",
        "BOND": "fixed_income",
    }

    proxy = _internal_6040_proxy(returns, class_map, returns.index)

    expected = 0.60 * returns[["EQ1", "EQ2"]].mean(axis=1) + 0.40 * returns["BOND"]
    pd.testing.assert_series_equal(proxy, expected, check_names=False)


def test_benchmark_evidence_maps_inverse_volatility_alias():
    diagnostics = pd.DataFrame(
        {"Evidence_Tier": ["Secondary research candidate"]},
        index=["Inv Volatility"],
    )

    assert (
        _benchmark_evidence_class("Inverse Vol", diagnostics)
        == "Secondary research candidate"
    )


def test_benchmark_comparison_contains_core_strategies_and_proxy(tmp_path):
    returns = _toy_returns()
    backtest_returns = pd.DataFrame(
        {
            "Equal Weight": returns.mean(axis=1),
            "HRP": 0.5 * returns["EQ1"] + 0.5 * returns["BOND"],
            "Inverse Vol": 0.4 * returns["EQ1"] + 0.6 * returns["BOND"],
            "Max Sharpe": returns["EQ2"],
        },
        index=returns.index,
    )
    backtest_summary = pd.DataFrame(
        {
            "CAGR": [0.10, 0.08, 0.06, 0.02],
            "Volatility": [0.12, 0.08, 0.07, 0.20],
            "Sharpe": [0.70, 0.60, 0.50, 0.10],
            "Max_Drawdown": [-0.10, -0.08, -0.07, -0.30],
            "Calmar": [1.0, 1.0, 0.9, 0.1],
            "Total_Turnover": [1.0, 1.2, 0.8, 3.0],
            "Total_Cost": [0.001, 0.002, 0.001, 0.004],
        },
        index=backtest_returns.columns,
    )
    diagnostics = pd.DataFrame(
        {
            "Evidence_Tier": [
                "Secondary research candidate",
                "Primary research candidate",
                "Secondary research candidate",
                "Diagnostic only",
            ]
        },
        index=["Equal Weight", "HRP", "Inv Volatility", "Max Sharpe"],
    )
    class_map = {
        "EQ1": "us_equity_sectors",
        "EQ2": "international_equity",
        "BOND": "fixed_income",
    }

    comparison = _write_benchmark_comparison_artifacts(
        tmp_path,
        returns,
        backtest_returns,
        backtest_summary,
        diagnostics,
        class_map,
        risk_free_rate=0.03,
    )

    assert {"Equal Weight", "HRP", "Inverse Vol"}.issubset(set(comparison["Name"]))
    assert (
        comparison.loc[comparison["Name"].eq("Max Sharpe"), "Evidence_Class"].iloc[0]
        == "Diagnostic only"
    )
    assert comparison["Name"].str.contains("60/40 internal").any()
    assert (tmp_path / "benchmark_comparison.csv").exists()


def test_cost_sensitivity_interpretation_marks_counterfactual():
    assert "counterfactual" in _cost_sensitivity_interpretation(0, "HRP")
    assert "High-cost" in _cost_sensitivity_interpretation(25, "HRP")


def test_transaction_cost_sensitivity_schema_with_fake_backtester(
    monkeypatch, tmp_path
):
    class FakeBacktester:
        def __init__(
            self, returns, class_map, costs, risk_free_rate, max_position_weight
        ):
            self.costs = costs

        def run_all_strategies(self, train_window, rebal_frequency):
            bps = int(round(self.costs.proportional * 10000))
            return {
                "Equal Weight": {
                    "metrics": {
                        "CAGR": 0.10 - bps / 10000,
                        "Sharpe Ratio": 0.90 - bps / 100,
                        "Max Drawdown": -0.10,
                    },
                    "total_cost": max(0, bps) / 10000,
                    "annualized_cost_drag_%": max(0, bps) / 100,
                }
            }

    monkeypatch.setattr(pipeline, "PortfolioBacktester", FakeBacktester)

    sensitivity = _write_transaction_cost_sensitivity_artifacts(
        tmp_path,
        _toy_returns(rows=30),
        {
            "EQ1": "us_equity_sectors",
            "EQ2": "international_equity",
            "BOND": "fixed_income",
        },
        PipelineConfig(train_window=10, rebal_frequency=5),
        risk_free_rate=0.03,
    )

    assert set(sensitivity["Cost_Bps"]) == {0, 5, 10, 25}
    assert (sensitivity["Total_Cost"] >= 0).all()
    assert {"CAGR", "Sharpe", "Max_Drawdown", "Annualized_Cost_Drag_%"}.issubset(
        sensitivity.columns
    )


def test_block_bootstrap_metrics_shape_and_no_divide_by_zero():
    returns = pd.Series(
        [0.01, -0.005, 0.002, 0.004, -0.001] * 5,
        index=pd.date_range("2024-01-01", periods=25, freq="B"),
    )

    result = _block_bootstrap_metrics(
        returns,
        risk_free_rate=0.02,
        samples=12,
        block_size=50,
        rng=np.random.default_rng(42),
    )

    assert result["CAGR"].shape == (12,)
    assert result["Sharpe"].shape == (12,)


def test_statistical_robustness_intervals_contain_observed_estimate(tmp_path):
    backtest_returns = pd.DataFrame(
        {"Equal Weight": [0.01, -0.005, 0.002, 0.004, -0.001] * 20},
        index=pd.date_range("2024-01-01", periods=100, freq="B"),
    )
    config = PipelineConfig(bootstrap_samples=30, bootstrap_block_size=5, random_seed=7)

    robustness = _write_statistical_robustness_artifacts(
        tmp_path, backtest_returns, config, risk_free_rate=0.02
    )
    row = robustness.iloc[0]

    assert row["CAGR_CI_5"] <= row["CAGR_CI_95"]
    assert row["Sharpe_CI_5"] <= row["Sharpe_CI_95"]
    assert row["Evidence_Strength"] in {
        "strong_positive",
        "moderate_positive",
        "negative",
        "inconclusive",
    }
    assert (tmp_path / "statistical_robustness.csv").exists()


def test_bootstrap_evidence_strength_categories():
    assert _bootstrap_evidence_strength(0.6, 1.2) == "strong_positive"
    assert _bootstrap_evidence_strength(0.1, 0.4) == "moderate_positive"
    assert _bootstrap_evidence_strength(-0.5, -0.1) == "negative"
    assert _bootstrap_evidence_strength(-0.1, 0.2) == "inconclusive"


def test_ml_confusion_matrix_output_shape_and_interpretation():
    predictions = pd.DataFrame(
        {
            "Observed": [1, 1, 0, 0],
            "Prediction": [1, 0, 1, 0],
            "Probability": [0.8, 0.4, 0.6, 0.2],
        }
    )

    confusion = _ml_confusion_matrix_table(predictions)

    assert confusion.shape == (1, 9)
    assert confusion.loc[0, "TP"] == 1
    assert confusion.loc[0, "TN"] == 1
    assert "not a trading rule" in confusion.loc[0, "Interpretation"]


def test_ml_drift_report_schema_for_sufficient_predictions():
    predictions = pd.DataFrame(
        {
            "Observed": [0, 1] * 20,
            "Prediction": [0, 1] * 20,
            "Probability": np.r_[np.linspace(0.1, 0.4, 20), np.linspace(0.5, 0.8, 20)],
        },
        index=pd.date_range("2024-01-01", periods=40, freq="B"),
    )

    drift = _ml_drift_report(predictions)

    assert {"prediction_probability_ks", "prediction_probability_psi"}.issubset(
        set(drift["Check"])
    )
    assert {"Status", "Statistic", "Interpretation"}.issubset(drift.columns)


def test_ml_drift_report_handles_too_few_predictions():
    predictions = pd.DataFrame(
        {"Observed": [0, 1], "Prediction": [0, 1], "Probability": [0.2, 0.8]}
    )

    drift = _ml_drift_report(predictions)

    assert drift.loc[0, "Status"] == "inconclusive"


def test_population_stability_index_returns_nan_for_constant_expected():
    psi = _population_stability_index(pd.Series([0.5] * 10), pd.Series([0.5] * 10))

    assert np.isnan(psi)
